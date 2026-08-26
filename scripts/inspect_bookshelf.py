from playwright.sync_api import sync_playwright
from pathlib import Path

AUTH_FILE = Path("auth.json")

BOOKSHELF_URL = (
    "https://shonenjumpplus.com/my/bookshelf/magazine/"
    "13933686331636289886"
)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)

        context = browser.new_context(
            storage_state=str(AUTH_FILE),
            viewport={
                "width": 1440,
                "height": 1000,
            },
        )

        page = context.new_page()

        page.goto(
            BOOKSHELF_URL,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(2000)

        print("TITLE:", page.title())
        print("URL:", page.url)
        print()

        links = page.locator("a")

        print("リンク数:", links.count())
        print("=" * 80)

        for i in range(links.count()):
            link = links.nth(i)

            try:
                text = link.inner_text().strip()
            except Exception:
                text = ""

            href = link.get_attribute("href")

            if not href:
                continue

            if "magazine" in href:
                print(f"[{i}]")
                print("text:", repr(text))
                print("href:", href)
                print("-" * 80)

        input("Enterで終了 > ")

        browser.close()


if __name__ == "__main__":
    main()