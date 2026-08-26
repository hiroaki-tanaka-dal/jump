from pathlib import Path

from playwright.sync_api import sync_playwright


AUTH_FILE = Path("auth.json")

MAGAZINE_URL = (
    "https://shonenjumpplus.com/magazine/"
    "9253191255209039994"
)

INTERNAL_PAGE = 69


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

        target_url = (
            f"{MAGAZINE_URL}"
            f"#mainPage-{INTERNAL_PAGE}"
        )

        print("OPEN:", target_url)

        page.goto(
            target_url,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(3000)

        print("ACTUAL URL:", page.url)
        print()

        canvases = page.locator("canvas")

        print("CANVAS COUNT:", canvases.count())
        print("=" * 100)

        for i in range(canvases.count()):
            canvas = canvases.nth(i)

            result = canvas.evaluate(
                """
                (canvas) => {
                    const parents = [];

                    let el = canvas;

                    for (let depth = 0; depth < 8 && el; depth++) {
                        parents.push({
                            tag: el.tagName,
                            id: el.id || null,
                            className:
                                typeof el.className === "string"
                                    ? el.className
                                    : null,
                            dataPage: el.getAttribute("data-page"),
                            dataIndex: el.getAttribute("data-index"),
                            dataPageIndex:
                                el.getAttribute("data-page-index"),
                            style: el.getAttribute("style")
                        });

                        el = el.parentElement;
                    }

                    return {
                        canvasWidth: canvas.width,
                        canvasHeight: canvas.height,
                        parents: parents
                    };
                }
                """
            )

            box = canvas.bounding_box()

            print()
            print(f"CANVAS [{i}]")
            print("box:", box)
            print(
                "internal size:",
                result["canvasWidth"],
                "x",
                result["canvasHeight"],
            )

            for depth, parent in enumerate(
                result["parents"]
            ):
                print(
                    f"  [{depth}] "
                    f"<{parent['tag']}> "
                    f"id={parent['id']!r} "
                    f"class={parent['className']!r} "
                    f"data-page={parent['dataPage']!r} "
                    f"data-index={parent['dataIndex']!r} "
                    f"data-page-index={parent['dataPageIndex']!r}"
                )

            print("-" * 100)

        input("\nEnterで終了 > ")

        browser.close()


if __name__ == "__main__":
    main()