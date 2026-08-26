from pathlib import Path

from playwright.sync_api import sync_playwright


AUTH_FILE = Path("auth.json")

MAGAZINE_URL = (
    "https://shonenjumpplus.com/magazine/"
    "9253191255209039994"
)

TARGET_PAGE = 70

OUTPUT_DIR = Path("data/pages/test")
OUTPUT_FILE = OUTPUT_DIR / f"page_{TARGET_PAGE:03d}.png"


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

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

        target_url = f"{MAGAZINE_URL}#mainPage-{TARGET_PAGE}"

        print("OPEN:", target_url)

        page.goto(
            target_url,
            wait_until="domcontentloaded",
        )

        # ビューア描画待ち
        page.wait_for_timeout(3000)

        canvases = page.locator("canvas")

        print("CANVAS COUNT:", canvases.count())

        for i in range(canvases.count()):
            canvas = canvases.nth(i)
            box = canvas.bounding_box()

            print(
                f"[{i}] "
                f"width={canvas.get_attribute('width')} "
                f"height={canvas.get_attribute('height')} "
                f"box={box}"
            )

        if canvases.count() == 0:
            raise RuntimeError("canvas が見つかりませんでした。")

        # 表示されている canvas のみを抽出
        visible_canvases = []

        for i in range(canvases.count()):
            canvas = canvases.nth(i)
            box = canvas.bounding_box()

            if box is None:
                continue

            is_visible = (
                box["x"] + box["width"] > 0
                and box["x"] < 1720
                and box["y"] + box["height"] > 0
                and box["y"] < 1000
            )

            if not is_visible:
                continue

            visible_canvases.append((i, canvas, box))


        print()
        print("VISIBLE CANVASES:", len(visible_canvases))

        for order, (index, canvas, box) in enumerate(
            visible_canvases,
            start=1,
        ):
            output_file = (
                OUTPUT_DIR
                / f"page_{TARGET_PAGE:03d}_canvas_{index}.png"
            )

            canvas.screenshot(
                path=str(output_file),
            )

            print(
                f"Canvas {index}: "
                f"x={box['x']} "
                f"→ {output_file}"
            )

        print()
        print("保存しました:")
        print(OUTPUT_FILE.resolve())

        input("\nEnterで終了 > ")

        browser.close()


if __name__ == "__main__":
    main()