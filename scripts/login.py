from pathlib import Path

from playwright.sync_api import sync_playwright


AUTH_FILE = Path("auth.json")


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
        )

        context = browser.new_context(
            viewport={
                "width": 1440,
                "height": 1000,
            }
        )

        page = context.new_page()
        page.goto("https://shonenjumpplus.com/")

        print("")
        print("ブラウザでログインしてください。")
        print("ログインが完了したら、このターミナルに戻ってEnterを押してください。")
        print("")

        input("ログイン完了後 Enter > ")

        context.storage_state(path=str(AUTH_FILE))

        print(f"ログイン状態を保存しました: {AUTH_FILE.resolve()}")

        browser.close()


if __name__ == "__main__":
    main()