from pathlib import Path

from playwright.sync_api import sync_playwright

from jump_pdf.downloader.pages import (
    download_entry_pages,
)


AUTH_FILE = Path("auth.json")

MAGAZINE_URL = (
    "https://shonenjumpplus.com/magazine/"
    "9253191255209039994"
)

OUTPUT_DIR = Path(
    "data/pages"
)

VIEWPORT_WIDTH = 1720
VIEWPORT_HEIGHT = 1000


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
        )

        context = browser.new_context(
            storage_state=str(
                AUTH_FILE
            ),
            viewport={
                "width": VIEWPORT_WIDTH,
                "height": VIEWPORT_HEIGHT,
            },
            device_scale_factor=2.56,
        )

        page = context.new_page()

        print("雑誌を開きます")

        page.goto(
            MAGAZINE_URL,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(
            2500
        )

        files = (
            download_entry_pages(
                page=page,
                title="ONE PIECE",
                start_internal_page=69,
                next_internal_page=87,
                output_dir=OUTPUT_DIR,
            )
        )

        print()
        print(
            f"保存完了: "
            f"{len(files)}ページ"
        )

        for file in files:
            print(
                file
            )

        input(
            "\nEnterで終了 > "
        )

        browser.close()


if __name__ == "__main__":
    main()