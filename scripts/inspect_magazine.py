
from pathlib import Path

from playwright.sync_api import sync_playwright


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
        )

        page = context.new_page()

        page.goto(
            MAGAZINE_URL,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(3000)

        print()
        print("TITLE:", page.title())
        print("URL:", page.url)
        print()

        # -------------------------
        # img
        # -------------------------

        images = page.locator("img")

        print("=" * 80)
        print("IMG COUNT:", images.count())
        print("=" * 80)

        for i in range(images.count()):
            img = images.nth(i)

            try:
                src = img.get_attribute("src")
                alt = img.get_attribute("alt")

                box = img.bounding_box()

                print(
                    f"[IMG {i}] "
                    f"alt={alt!r} "
                    f"src={src!r} "
                    f"box={box}"
                )

            except Exception as e:
                print(f"[IMG {i}] ERROR:", e)

        # -------------------------
        # canvas
        # -------------------------

        canvases = page.locator("canvas")

        print()
        print("=" * 80)
        print("CANVAS COUNT:", canvases.count())
        print("=" * 80)

        for i in range(canvases.count()):
            canvas = canvases.nth(i)

            try:
                box = canvas.bounding_box()

                width = canvas.get_attribute("width")
                height = canvas.get_attribute("height")

                print(
                    f"[CANVAS {i}] "
                    f"width={width} "
                    f"height={height} "
                    f"box={box}"
                )

            except Exception as e:
                print(f"[CANVAS {i}] ERROR:", e)

        # -------------------------
        # Links
        # -------------------------

        links = page.locator("a")

        print()
        print("=" * 80)
        print("INTERESTING LINKS")
        print("=" * 80)

        for i in range(links.count()):
            link = links.nth(i)

            try:
                text = link.inner_text().strip()
                href = link.get_attribute("href")

                if text:
                    print(
                        f"[{i}] "
                        f"text={text!r} "
                        f"href={href!r}"
                    )

            except Exception:
                pass

        input("\nEnterで終了 > ")

        browser.close()


if __name__ == "__main__":
    main()