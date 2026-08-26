from pathlib import Path

from playwright.sync_api import sync_playwright

from jump_pdf.browser.viewer import (
    get_table_of_contents,
)


AUTH_FILE = Path("auth.json")

MAGAZINE_URL = (
    "https://shonenjumpplus.com/magazine/"
    "9253191255209039994"
)


def main():
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
            device_scale_factor=2.56,
        )

        page = context.new_page()

        page.goto(
            MAGAZINE_URL,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(2500)

        entries = get_table_of_contents(
            page
        )

        print()
        print(
            f"目次項目数: {len(entries)}"
        )
        print("=" * 70)

        for index, entry in enumerate(
            entries,
            start=1,
        ):
            print(
                f"{index:02d}. "
                f"mainPage-{entry.start_page:<4} "
                f"{entry.title}"
            )

        input("\nEnterで終了 > ")

        browser.close()


if __name__ == "__main__":
    main()