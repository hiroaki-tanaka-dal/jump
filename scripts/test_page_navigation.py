import hashlib
from pathlib import Path

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

START_INTERNAL_PAGE = 69

VIEWPORT_WIDTH = 1720
VIEWPORT_HEIGHT = 1000


def get_canvas_state(page):
    """
    現在画面内に表示されているCanvasを
    スクリーンショットのハッシュで識別する。
    """

    visible = get_visible_canvases(
        page,
        VIEWPORT_WIDTH,
        VIEWPORT_HEIGHT,
    )

    state = []

    for item in visible:
        canvas = item["canvas"]

        image_bytes = canvas.screenshot(
            scale="device",
        )

        digest = hashlib.sha256(
            image_bytes
        ).hexdigest()[:16]

        state.append(
            {
                "index": item["index"],
                "alignment": item["alignment"],
                "x": item["box"]["x"],
                "hash": digest,
            }
        )

    return state


def print_state(label, state):
    print()
    print(label)

    for position, item in enumerate(
        state,
        start=1,
    ):
        print(
            f"  position={position} "
            f"canvas={item['index']} "
            f"alignment={item['alignment']} "
            f"x={item['x']:.0f} "
            f"hash={item['hash']}"
        )


def reset_to_start(page):
    """
    ONE PIECEの目次位置へ戻す。
    """

    goto_internal_page(
        page,
        START_INTERNAL_PAGE,
    )

    page.wait_for_timeout(1000)


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

        page.goto(
            MAGAZINE_URL,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(2500)

        # --------------------------------
        # 基準状態
        # --------------------------------

        reset_to_start(page)

        initial = get_canvas_state(page)

        print_state(
            "=== mainPage-69 初期状態 ===",
            initial,
        )

        # --------------------------------
        # ArrowLeft
        # --------------------------------

        print()
        print("ArrowLeft を1回押します")

        page.keyboard.press("ArrowLeft")
        page.wait_for_timeout(1000)

        after_left = get_canvas_state(page)

        print_state(
            "=== ArrowLeft 後 ===",
            after_left,
        )

        # --------------------------------
        # 69へ戻す
        # --------------------------------

        reset_to_start(page)

        reset_state = get_canvas_state(page)

        print_state(
            "=== 69へ戻した状態 ===",
            reset_state,
        )

        # --------------------------------
        # ArrowRight
        # --------------------------------

        print()
        print("ArrowRight を1回押します")

        page.keyboard.press("ArrowRight")
        page.wait_for_timeout(1000)

        after_right = get_canvas_state(page)

        print_state(
            "=== ArrowRight 後 ===",
            after_right,
        )

        input("\nEnterで終了 > ")

        browser.close()


if __name__ == "__main__":
    main()