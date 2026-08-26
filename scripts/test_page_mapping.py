from pathlib import Path
import hashlib

from PIL import Image
from playwright.sync_api import sync_playwright

from jump_pdf.browser.viewer import (
    get_visible_canvases,
    goto_internal_page,
)


AUTH_FILE = Path("auth.json")

MAGAZINE_URL = (
    "https://shonenjumpplus.com/magazine/"
    "9253191255209039994"
)

VIEWPORT_WIDTH = 1720
VIEWPORT_HEIGHT = 1000

OUTPUT_DIR = Path("data/pages/mapping")

TEST_PAGES = [
    69,
    70,
    71,
]


def sha256(path: Path) -> str:
    return hashlib.sha256(
        path.read_bytes()
    ).hexdigest()[:16]


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
            device_scale_factor=2.56,
        )

        page = context.new_page()

        print("雑誌を開きます")

        page.goto(
            MAGAZINE_URL,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(2500)

        for internal_page in TEST_PAGES:
            print()
            print("=" * 70)
            print(
                f"mainPage-{internal_page}"
            )
            print("=" * 70)

            goto_internal_page(
                page,
                internal_page,
            )

            visible = get_visible_canvases(
                page,
                VIEWPORT_WIDTH,
                VIEWPORT_HEIGHT,
            )

            print(
                "visible canvases:",
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
                        f"internal_{internal_page:03d}"
                        f"_position_{order}.png"
                    )
                )

                canvas.screenshot(
                    path=str(output_file),
                    scale="device",
                )

                with Image.open(
                    output_file
                ) as image:
                    size = (
                        image.width,
                        image.height,
                    )

                print(
                    f"position={order} "
                    f"canvas={item['index']} "
                    f"alignment={item['alignment']} "
                    f"x={box['x']:.0f} "
                    f"png={size[0]}x{size[1]} "
                    f"hash={sha256(output_file)}"
                )

        print()
        print("保存先:")
        print(OUTPUT_DIR.resolve())

        input("\nEnterで終了 > ")

        browser.close()


if __name__ == "__main__":
    main()