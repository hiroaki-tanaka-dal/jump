import json
from pathlib import Path

from playwright.sync_api import (
    sync_playwright,
)

from jump_pdf.bookshelf.bookshelf import (
    collect_magazines,
    magazine_to_dict,
)


AUTH_FILE = Path("auth.json")

OUTPUT_FILE = Path(
    "data/catalog/magazines.json"
)


def main():
    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
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

        magazines = collect_magazines(
            page,

            # 最初は安全のため2ページ。
            # 動作確認後 None に変更する。
            max_pages=None,
        )

        data = [
            magazine_to_dict(magazine)
            for magazine in magazines
        ]

        OUTPUT_FILE.write_text(
            json.dumps(
                data,
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        print()
        print("=" * 70)
        print(
            f"取得完了: {len(magazines)}冊"
        )
        print(
            f"保存先: {OUTPUT_FILE}"
        )
        print("=" * 70)

        browser.close()


if __name__ == "__main__":
    main()