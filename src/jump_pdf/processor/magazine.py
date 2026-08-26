import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

from playwright.sync_api import Page

from jump_pdf.browser.viewer import get_table_of_contents
from jump_pdf.classifier.entry import (
    EntryType,
    classify_title,
)

from jump_pdf.downloader.pages import download_entry_pages
from datetime import datetime

COLOR_PAGE_COUNT = 4


@dataclass
class ProcessEntry:
    original_title: str
    work_title: str
    entry_type: str
    start_internal_page: int
    end_internal_page: int | None
    capture_start_page: int | None
    capture_end_page: int | None
    output_dir: str | None
    skip: bool
    skip_reason: str | None


def safe_name(value: str) -> str:
    """
    ファイル・ディレクトリ名として問題のある文字を置換する。
    """

    value = value.strip()

    value = re.sub(
        r'[\\/:*?"<>|]',
        "_",
        value,
    )

    value = re.sub(
        r"\s+",
        " ",
        value,
    )

    return value


def issue_key_from_magazine(
    magazine: dict,
) -> str:
    year = magazine.get("year")
    issue = magazine.get("issue")

    if year is not None and issue:
        return f"{year}-{issue}"

    return magazine["magazine_id"]


def build_process_plan(
    entries,
    issue_key: str,
    output_root: Path,
) -> list[ProcessEntry]:
    """
    目次から、この号をどう取得するかの計画を作る。

    ここではまだ画像取得はしない。
    """

    result: list[ProcessEntry] = []

    for index, entry in enumerate(entries):
        classified = classify_title(
            entry.title
        )

        # 次の目次項目までを、この項目の範囲とする
        end_internal_page = None

        if index + 1 < len(entries):
            end_internal_page = (
                entries[index + 1].start_page - 1
            )

        # -----------------------------
        # 除外
        # -----------------------------

        if (
            classified.entry_type
            == EntryType.EXCLUDE
        ):
            result.append(
                ProcessEntry(
                    original_title=entry.title,
                    work_title=classified.work_title,
                    entry_type=classified.entry_type.value,
                    start_internal_page=entry.start_page,
                    end_internal_page=end_internal_page,
                    capture_start_page=None,
                    capture_end_page=None,
                    output_dir=None,
                    skip=True,
                    skip_reason="exclude rule",
                )
            )

            continue

        work_name = safe_name(
            classified.work_title
        )

        work_dir = (
            output_root
            / work_name
            / issue_key
        )

        # -----------------------------
        # 巻頭カラー
        # -----------------------------

        if (
            classified.entry_type
            == EntryType.COLOR
        ):
            capture_start = (
                entry.start_page
            )

            capture_end = (
                entry.start_page
                + COLOR_PAGE_COUNT
                - 1
            )

            # 万一、次の目次項目を越える場合
            if (
                end_internal_page
                is not None
            ):
                capture_end = min(
                    capture_end,
                    end_internal_page,
                )

            output_dir = (
                work_dir / "color"
            )

        # -----------------------------
        # モノクロ本編
        # -----------------------------

        elif (
            classified.entry_type
            == EntryType.MONO
        ):
            capture_start = (
                entry.start_page
            )

            capture_end = (
                end_internal_page
            )

            output_dir = (
                work_dir / "main"
            )

        # -----------------------------
        # 通常掲載
        # -----------------------------

        else:
            capture_start = (
                entry.start_page
            )

            capture_end = (
                end_internal_page
            )

            output_dir = (
                work_dir / "main"
            )

        result.append(
            ProcessEntry(
                original_title=entry.title,
                work_title=classified.work_title,
                entry_type=classified.entry_type.value,
                start_internal_page=entry.start_page,
                end_internal_page=end_internal_page,
                capture_start_page=capture_start,
                capture_end_page=capture_end,
                output_dir=str(output_dir),
                skip=False,
                skip_reason=None,
            )
        )

    return result


def print_process_plan(
    plan: list[ProcessEntry],
) -> None:
    print()
    print("=" * 100)
    print("取得計画")
    print("=" * 100)

    for index, entry in enumerate(
        plan,
        start=1,
    ):
        if entry.skip:
            print(
                f"{index:02d}. "
                f"[SKIP] "
                f"{entry.original_title}"
            )

            continue

        page_range = (
            f"{entry.capture_start_page}"
            f"-"
            f"{entry.capture_end_page}"
        )

        print(
            f"{index:02d}. "
            f"[{entry.entry_type.upper():6}] "
            f"{page_range:>9}  "
            f"{entry.work_title}"
        )

        if (
            entry.original_title
            != entry.work_title
        ):
            print(
                f"      original: "
                f"{entry.original_title}"
            )


def save_process_plan(
    plan: list[ProcessEntry],
    magazine: dict,
    issue_key: str,
    output_root: Path,
) -> Path:
    """
    号単位の取得計画をJSONへ保存する。
    """

    metadata_dir = (
        output_root
        / "_magazines"
        / issue_key
    )

    metadata_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        metadata_dir
        / "process_plan.json"
    )

    data = {
        "magazine": magazine,
        "issue_key": issue_key,
        "entries": [
            asdict(entry)
            for entry in plan
        ],
    }

    output_file.write_text(
        json.dumps(
            data,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    return output_file


def process_magazine(
    page: Page,
    magazine: dict,
    output_root: Path,
    dry_run: bool = True,
) -> list[ProcessEntry]:
    """
    1号分を処理する。

    現段階では dry_run=True を使用し、
    取得計画の作成まで行う。
    """

    issue_key = issue_key_from_magazine(
        magazine
    )

    print()
    print("=" * 100)
    print(magazine["title"])
    print(f"issue: {issue_key}")
    print("=" * 100)

    page.goto(
        magazine["url"],
        wait_until="domcontentloaded",
    )

    page.wait_for_timeout(2000)

    entries = get_table_of_contents(
        page
    )

    if not entries:
        raise RuntimeError(
            "目次を取得できませんでした。"
        )

    print(
        f"目次項目数: {len(entries)}"
    )

    plan = build_process_plan(
        entries=entries,
        issue_key=issue_key,
        output_root=output_root,
    )

    # debug: 取得計画の最初の5件だけにする
    # plan = plan[:5]
    
    print_process_plan(
        plan
    )

    plan_file = save_process_plan(
        plan=plan,
        magazine=magazine,
        issue_key=issue_key,
        output_root=output_root,
    )

    print()
    print(
        f"取得計画保存: {plan_file}"
    )

    if dry_run:
        print()
        print(
            "DRY RUN: "
            "画像取得は実行していません。"
        )
        return plan


    print()
    print("=" * 100)
    print("画像取得開始")
    print("=" * 100)

    for index, item in enumerate(
        plan,
        start=1,
    ):
        if item.skip:
            print(
                f"[{index}/{len(plan)}] "
                f"SKIP: {item.original_title}"
            )
            continue

        if (
            item.capture_start_page is None
            or item.capture_end_page is None
            or item.output_dir is None
        ):
            print(
                f"[{index}/{len(plan)}] "
                f"SKIP: {item.original_title} "
                "(取得範囲不明)"
            )
            continue

        output_dir = Path(
            item.output_dir
        )

        # download_entry_pages() は
        # output_dir / title に保存する設計なので、
        # ここでは親ディレクトリ + 最終フォルダ名へ分解する
        parent_dir = output_dir.parent
        leaf_dir = output_dir.name

        metadata_file = (
            output_dir
            / "metadata.json"
        )

        # 取得済みならスキップ
        if metadata_file.exists():
            print(
                f"[{index}/{len(plan)}] "
                f"SKIP: {item.work_title} "
                "(取得済み)"
            )
            continue

        print()
        print(
            f"[{index}/{len(plan)}] "
            f"{item.work_title}"
        )
        print(
            f"type: {item.entry_type}"
        )
        print(
            f"range: "
            f"{item.capture_start_page}"
            f"-"
            f"{item.capture_end_page}"
        )

        # download_entry_pages() は
        # next_internal_page を受け取るので +1
        next_internal_page = (
            item.capture_end_page + 1
        )

        files = download_entry_pages(
            page=page,
            title=leaf_dir,
            start_internal_page=(
                item.capture_start_page
            ),
            next_internal_page=(
                next_internal_page
            ),
            output_dir=parent_dir,
            include_initial_spread=(
                item.entry_type == "color"
            ),
        )

        metadata = {
            "original_title": (
                item.original_title
            ),
            "work_title": (
                item.work_title
            ),
            "entry_type": (
                item.entry_type
            ),
            "magazine": (
                magazine["title"]
            ),
            "issue": issue_key,
            "magazine_id": (
                magazine["magazine_id"]
            ),
            "magazine_url": (
                magazine["url"]
            ),
            "published_at": (
                magazine.get(
                    "published_at"
                )
            ),
            "capture_start_page": (
                item.capture_start_page
            ),
            "capture_end_page": (
                item.capture_end_page
            ),
            "page_count": (
                len(files)
            ),
            "files": [
                file.name
                for file in files
            ],
        }

        metadata_file.write_text(
            json.dumps(
                metadata,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print(
            f"完了: {output_dir}"
        )


    print()
    print("=" * 100)
    print("画像取得完了")
    print("=" * 100)

    status_file = (
        output_root
        / "_magazines"
        / issue_key
        / "status.json"
    )

    status_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    status = {
        "status": "completed",
        "processed_at": datetime.now().isoformat(),
        "magazine_id": magazine["magazine_id"],
        "title": magazine["title"],
        "issue": issue_key,
    }

    status_file.write_text(
        json.dumps(
            status,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return plan

    # 実取得は次段階でここへ接続する
    raise NotImplementedError(
        "画像取得処理はまだ接続していません。"
    )