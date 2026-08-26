import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from jump_pdf.browser.viewer import (
    get_table_of_contents,
)


AUTH_FILE = Path("auth.json")

MAGAZINES_FILE = Path(
    "data/catalog/magazines.json"
)

OUTPUT_DIR = Path(
    "data/analysis/toc"
)

# まずは直近20号で調査
LIMIT = 20


def build_issue_key(
    magazine: dict,
) -> str:
    """
    magazines.json の year / issue から
    ファイル名用のキーを作る。

    例:
        2026 / 37_38
            -> 2026-37_38
    """

    year = magazine.get("year")
    issue = magazine.get("issue")

    if year is not None and issue:
        return f"{year}-{issue}"

    # 万一解析できなかった場合は
    # magazine_id を使う
    return magazine["magazine_id"]


def collect_toc(
    page,
    magazine: dict,
) -> dict:
    """
    1号分の目次を取得する。
    """

    print()
    print("=" * 80)
    print(magazine["title"])
    print(magazine["url"])
    print("=" * 80)

    page.goto(
        magazine["url"],
        wait_until="domcontentloaded",
    )

    # ビューア・目次の初期化待ち
    page.wait_for_timeout(2000)

    entries = get_table_of_contents(page)

    print(
        f"目次項目数: {len(entries)}"
    )

    result_entries = []

    for index, entry in enumerate(entries):
        next_start_page = None
        end_page = None
        page_count = None

        if index + 1 < len(entries):
            next_entry = entries[index + 1]

            next_start_page = (
                next_entry.start_page
            )

            end_page = (
                next_start_page - 1
            )

            page_count = (
                next_start_page
                - entry.start_page
            )

        item = {
            "order": index + 1,
            "title": entry.title,
            "start_internal_page": (
                entry.start_page
            ),
            "end_internal_page": end_page,
            "page_count": page_count,
        }

        result_entries.append(item)

        end_text = (
            str(end_page)
            if end_page is not None
            else "?"
        )

        count_text = (
            str(page_count)
            if page_count is not None
            else "?"
        )

        print(
            f"{index + 1:02d}. "
            f"{entry.start_page:>4}"
            f" - {end_text:>4} "
            f"({count_text:>3}p) "
            f"{entry.title}"
        )

    return {
        "magazine_id": magazine["magazine_id"],
        "title": magazine["title"],
        "url": magazine["url"],
        "year": magazine.get("year"),
        "issue": magazine.get("issue"),
        "published_at": magazine.get(
            "published_at"
        ),
        "entry_count": len(result_entries),
        "entries": result_entries,
    }


def main():
    if not MAGAZINES_FILE.exists():
        raise RuntimeError(
            f"{MAGAZINES_FILE} がありません。\n"
            "先に collect_bookshelf.py を"
            "実行してください。"
        )

    magazines = json.loads(
        MAGAZINES_FILE.read_text(
            encoding="utf-8"
        )
    )

    if not magazines:
        raise RuntimeError(
            "magazines.json が空です。"
        )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    targets = magazines[:LIMIT]

    print(
        f"対象: {len(targets)}号"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
        )

        context = browser.new_context(
            storage_state=str(AUTH_FILE),
            viewport={
                "width": 1720,
                "height": 1000,
            },
        )

        page = context.new_page()

        success_count = 0
        error_count = 0

        for number, magazine in enumerate(
            targets,
            start=1,
        ):
            issue_key = build_issue_key(
                magazine
            )

            output_file = (
                OUTPUT_DIR
                / f"{issue_key}.json"
            )

            print()
            print(
                f"[{number}/{len(targets)}]"
            )

            # 再実行時は取得済みをスキップ
            if output_file.exists():
                print(
                    f"SKIP: {output_file}"
                )

                success_count += 1
                continue

            try:
                result = collect_toc(
                    page,
                    magazine,
                )

                output_file.write_text(
                    json.dumps(
                        result,
                        ensure_ascii=False,
                        indent=2,
                    ),
                    encoding="utf-8",
                )

                print(
                    f"saved: {output_file}"
                )

                success_count += 1

            except Exception as exc:
                error_count += 1

                print()
                print(
                    f"ERROR: {magazine['title']}"
                )
                print(
                    f"{type(exc).__name__}: "
                    f"{exc}"
                )

                # 1号失敗しても残りを続行する
                continue

        print()
        print("=" * 80)
        print("目次収集完了")
        print(
            f"成功: {success_count}"
        )
        print(
            f"失敗: {error_count}"
        )
        print(
            f"保存先: {OUTPUT_DIR.resolve()}"
        )
        print("=" * 80)

        browser.close()


if __name__ == "__main__":
    main()