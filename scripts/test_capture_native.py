from pathlib import Path

from playwright.sync_api import sync_playwright

from jump_pdf.browser.viewer import (
    get_visible_canvases,
    goto_internal_page,
    # save_canvas_native_resolution,
)
from PIL import Image


AUTH_FILE = Path("auth.json")

MAGAZINE_URL = (
    "https://shonenjumpplus.com/magazine/"
    "9253191255209039994"
)

INTERNAL_PAGE = 69

VIEWPORT_WIDTH = 1720
VIEWPORT_HEIGHT = 1000

OUTPUT_DIR = Path("data/pages/test")


def main():
    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

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
            device_scale_factor=2.5,
        )

        page = context.new_page()

        print("雑誌を開きます")

        page.goto(
            MAGAZINE_URL,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(2500)

        print(
            f"mainPage-{INTERNAL_PAGE} "
            "へ移動します"
        )

        goto_internal_page(
            page,
            INTERNAL_PAGE,
        )

        visible = get_visible_canvases(
            page,
            VIEWPORT_WIDTH,
            VIEWPORT_HEIGHT,
        )

        print()
        print(
            "VISIBLE CANVAS COUNT:",
            len(visible),
        )

        for order, item in enumerate(
            visible,
            start=1,
        ):
            canvas = item["canvas"]
            box = item["box"]

            output_file = (
                OUTPUT_DIR
                / (
                    f"internal_{INTERNAL_PAGE:03d}"
                    f"_visible_{order}.png"
                )
            )

            canvas.screenshot(
                path=str(output_file),
                scale="device",
            )

            with Image.open(output_file) as image:
                png_width = image.width
                png_height = image.height

            print()
            print(f"Canvas index: {item['index']}")
            print(f"alignment: {item['alignment']}")
            print(f"x: {box['x']:.1f}")
            print(
                f"CSS size: "
                f"{box['width']:.0f} x "
                f"{box['height']:.0f}"
            )
            print(
                f"PNG size: "
                f"{png_width} x "
                f"{png_height}"
            )
            print(f"saved: {output_file}")

        input("\nEnterで終了 > ")

        browser.close()


if __name__ == "__main__":
    main()