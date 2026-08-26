from pathlib import Path

from PIL import Image
from playwright.sync_api import Page

from jump_pdf.browser.viewer import (
    get_visible_canvases,
    goto_internal_page,
)
import random
import time

VIEWPORT_WIDTH = 1720
VIEWPORT_HEIGHT = 1000

def wait_after_page_turn() -> None:
    """
    ページ送り後の待機。
    連続操作になりすぎないよう少し余裕を持たせる。
    """
    wait_seconds = random.uniform(
        1.5,
        2.5,
    )

    print(
        f"  wait: {wait_seconds:.1f}s"
    )

    time.sleep(wait_seconds)

def save_canvas(
    canvas,
    output_file: Path,
) -> tuple[int, int]:
    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    canvas.screenshot(
        path=str(output_file),
        scale="device",
    )

    with Image.open(output_file) as image:
        return image.width, image.height


def download_entry_pages(
    page: Page,
    title: str,
    start_internal_page: int,
    next_internal_page: int,
    output_dir: Path,
    include_initial_spread: bool = False,
) -> list[Path]:
    """
    1つの目次項目ぶんのページを保存する。

    例:
        start_internal_page = 69
        next_internal_page = 87

    → 69〜86相当の18ページを保存する。
    """

    page_count = (
        next_internal_page
        - start_internal_page
    )

    if page_count <= 0:
        raise ValueError(
            "内部ページ範囲が不正です: "
            f"{start_internal_page} -> "
            f"{next_internal_page}"
        )

    entry_dir = (
        output_dir
        / title
    )

    entry_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 70)
    print(title)
    print(
        f"internal: "
        f"{start_internal_page}"
        f" - "
        f"{next_internal_page - 1}"
    )
    print(
        f"page count: {page_count}"
    )
    print("=" * 70)

    # 作品開始位置へ移動
    goto_internal_page(
        page,
        start_internal_page,
    )

    saved_files: list[Path] = []

    current_page_number = 1

    # --------------------------------------------------
    # 最初の見開き
    # --------------------------------------------------

    visible = get_visible_canvases(
        page,
        VIEWPORT_WIDTH,
        VIEWPORT_HEIGHT,
    )

    if len(visible) < 1:
        raise RuntimeError(
            "開始ページのCanvasを取得できませんでした。"
        )

    # x座標順
    # visible[0] = 画面左
    # visible[1] = 画面右
    visible.sort(
        key=lambda item: item["box"]["x"]
    )

    if include_initial_spread:
        # ----------------------------------------------
        # 巻頭カラー
        #
        # 最初の見開きは両ページとも対象。
        # 読む順番は右開きなので
        #
        #   画面右 → 画面左
        #
        # の順で保存する。
        # ----------------------------------------------

        initial_items = sorted(
            visible,
            key=lambda item: item["box"]["x"],
            reverse=True,
        )

    else:
        # ----------------------------------------------
        # 通常ページ
        #
        # 開始アンカーの左ページだけ保存。
        # 右ページは前の作品などの可能性がある。
        # ----------------------------------------------

        initial_items = [
            visible[0]
        ]

    for item in initial_items:
        if current_page_number > page_count:
            break

        output_file = (
            entry_dir
            / f"{current_page_number:03d}.png"
        )

        width, height = save_canvas(
            item["canvas"],
            output_file,
        )

        print(
            f"{current_page_number:03d}"
            f"/{page_count:03d} "
            f"START "
            f"canvas={item['index']} "
            f"alignment={item['alignment']} "
            f"x={item['box']['x']:.0f} "
            f"{width}x{height}"
        )

        saved_files.append(
            output_file
        )

        current_page_number += 1

    if current_page_number > page_count:
        return saved_files

    # 次の見開きへ
    page.keyboard.press(
        "ArrowLeft"
    )

    wait_after_page_turn()

    # --------------------------------------------------
    # 以降は
    #
    # 画面右 → 画面左
    #
    # の順で保存。
    # --------------------------------------------------

    while (
        current_page_number
        <= page_count
    ):
        visible = get_visible_canvases(
            page,
            VIEWPORT_WIDTH,
            VIEWPORT_HEIGHT,
        )

        if len(visible) < 2:
            raise RuntimeError(
                "見開きCanvasを2枚取得できませんでした。"
            )

        # xが大きい方 = 画面右
        #
        # 右開きなので
        # 右 → 左
        # の順で読む。
        visible.sort(
            key=lambda item: item["box"]["x"],
            reverse=True,
        )

        for item in visible:
            if (
                current_page_number
                > page_count
            ):
                break

            output_file = (
                entry_dir
                / (
                    f"{current_page_number:03d}"
                    ".png"
                )
            )

            width, height = save_canvas(
                item["canvas"],
                output_file,
            )

            print(
                f"{current_page_number:03d}"
                f"/{page_count:03d} "
                f"canvas={item['index']} "
                f"alignment={item['alignment']} "
                f"x={item['box']['x']:.0f} "
                f"{width}x{height}"
            )

            saved_files.append(
                output_file
            )

            current_page_number += 1

        if (
            current_page_number
            <= page_count
        ):
            page.keyboard.press(
                "ArrowLeft"
            )

            wait_after_page_turn()

            page.wait_for_timeout(
                700
            )

    return saved_files