from pathlib import Path

from playwright.sync_api import sync_playwright

from jump_pdf.sync import sync_magazines


AUTH_FILE = Path("auth.json")

VIEWPORT_WIDTH = 1720
VIEWPORT_HEIGHT = 1000


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
        )

        context = browser.new_context(
            storage_state=str(AUTH_FILE),
            viewport={
                "width": VIEWPORT_WIDTH,
                "height": VIEWPORT_HEIGHT,
            },
            device_scale_factor=2.56,
        )

        page = context.new_page()

        sync_magazines(
            page,
            # 最初は1号だけ
            limit=None,
            dry_run=False,
            newest_first=True,
        )

        browser.close()


if __name__ == "__main__":
    main()