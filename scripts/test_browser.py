from pathlib import Path

from playwright.sync_api import sync_playwright


AUTH_FILE = Path("auth.json")


def main():
    if not AUTH_FILE.exists():
        raise FileNotFoundError(
            "auth.json がありません。先に python scripts/login.py を実行してください。"
        )

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
        )

        context = browser.new_context(
            storage_state=str(AUTH_FILE),
            viewport={
                "width": 1440,
                "height": 1000,
            },
        )

        page = context.new_page()

        page.goto("https://shonenjumpplus.com/")

        print("title:", page.title())
        print("url:", page.url)

        input("Enterを押すと終了します...")

        browser.close()


if __name__ == "__main__":
    main()