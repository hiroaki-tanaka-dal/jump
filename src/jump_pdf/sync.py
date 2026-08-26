import json
from pathlib import Path

from playwright.sync_api import Page

from jump_pdf.bookshelf.bookshelf import (
    collect_magazines,
    magazine_to_dict,
)
from jump_pdf.processor.magazine import process_magazine


MAGAZINES_FILE = Path("data/catalog/magazines.json")
WORKS_ROOT = Path("data/works")


def issue_key(magazine: dict) -> str:
    year = magazine.get("year")
    issue = magazine.get("issue")

    if year is not None and issue:
        return f"{year}-{issue}"

    return magazine["magazine_id"]


def is_magazine_processed(
    magazine: dict,
    output_root: Path = WORKS_ROOT,
) -> bool:
    key = issue_key(magazine)

    status_file = (
        output_root
        / "_magazines"
        / key
        / "status.json"
    )

    if not status_file.exists():
        return False

    try:
        status = json.loads(
            status_file.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        return False

    return status.get("status") == "completed"

def update_magazine_catalog(
    page: Page,
) -> list[dict]:
    """
    本棚を最後のページまで取得して
    magazines.json を最新状態に更新する。
    """

    print()
    print("=" * 80)
    print("本棚カタログ更新")
    print("=" * 80)

    magazines = collect_magazines(
        page,
        max_pages=None,
    )

    magazine_dicts = [
        magazine_to_dict(magazine)
        for magazine in magazines
    ]

    MAGAZINES_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    MAGAZINES_FILE.write_text(
        json.dumps(
            magazine_dicts,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print(
        f"本棚カタログ更新完了: "
        f"{len(magazine_dicts)}冊"
    )
    print(
        f"保存先: {MAGAZINES_FILE}"
    )

    return magazine_dicts

def load_magazines() -> list[dict]:
    if not MAGAZINES_FILE.exists():
        raise RuntimeError(
            "magazines.json がありません。"
        )

    return json.loads(
        MAGAZINES_FILE.read_text(
            encoding="utf-8"
        )
    )


def sync_magazines(
    page: Page,
    *,
    limit: int | None = None,
    dry_run: bool = False,
    newest_first: bool = False,
) -> None:
    """
    未処理号だけ process_magazine() へ流す。
    """

    magazines = update_magazine_catalog(
        page
    )

    # 初回同期では古い号から処理する方が
    # data/works の並びを確認しやすい。
    if not newest_first:
        magazines = list(
            reversed(magazines)
        )

    pending = [
        magazine
        for magazine in magazines
        if not is_magazine_processed(
            magazine
        )
    ]

    if limit is not None:
        pending = pending[:limit]

    print()
    print("=" * 80)
    print("SYNC")
    print("=" * 80)
    print(
        f"catalog: {len(magazines)}"
    )
    print(
        f"pending: {len(pending)}"
    )
    print(
        f"dry_run: {dry_run}"
    )

    if not pending:
        print("未処理号はありません。")
        return

    for index, magazine in enumerate(
        pending,
        start=1,
    ):
        print()
        print("#" * 80)
        print(
            f"[{index}/{len(pending)}] "
            f"{magazine['title']}"
        )
        print("#" * 80)

        process_magazine(
            page=page,
            magazine=magazine,
            output_root=WORKS_ROOT,
            dry_run=dry_run,
        )

    print()
    print("=" * 80)
    print("SYNC完了")
    print("=" * 80)