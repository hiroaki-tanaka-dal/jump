import json
from pathlib import Path

from playwright.sync_api import sync_playwright

from jump_pdf.processor.magazine import (
    process_magazine,
)


AUTH_FILE = Path("auth.json")

MAGAZINES_FILE = Path(
    "data/catalog/magazines.json"
)

OUTPUT_ROOT = Path(
    "data/works"
)


def main():
    magazines = json.loads(
        MAGAZINES_FILE.read_text(
            encoding="utf-8"
        )
    )

    if not magazines:
        raise RuntimeError(
            "magazines.json が空です。"
        )

    # 最新号
    magazine = magazines[0]
    # 任意の号の確認
    # magazine = magazines[-1]  # 2024年6月号

    print(
        f"対象: {magazine['title']}"
    )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
        )

        context = browser.new_context(
            storage_state=str(
                AUTH_FILE
            ),
            viewport={
                "width": 1720,
                "height": 1000,
            },
        )

        page = context.new_page()

        process_magazine(
            page=page,
            magazine=magazine,
            output_root=OUTPUT_ROOT,
            dry_run=False,
        )

        browser.close()


if __name__ == "__main__":
    main()