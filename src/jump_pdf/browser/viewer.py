import base64
from pathlib import Path

from playwright.sync_api import Page

import re
from dataclasses import dataclass


def goto_internal_page(
    page: Page,
    internal_page: int,
) -> None:
    """
    目次リンク #mainPage-N を使って、
    ビューア内部ページへ移動する。

    目次リンクは非表示状態の場合があるため、
    Playwrightの物理クリックではなく
    DOM上でclick()を発火させる。
    """

    selector = f'a[href="#mainPage-{internal_page}"]'

    link = page.locator(selector)

    if link.count() == 0:
        raise RuntimeError(
            f"内部ページ mainPage-{internal_page} "
            "への目次リンクが見つかりません。"
        )

    print(
        f"目次リンク発見: mainPage-{internal_page}"
    )

    link.first.evaluate(
        """
        element => {
            element.click();
        }
        """
    )

    # ビューアの横移動・Canvas再描画を待つ
    page.wait_for_timeout(1500)


def get_visible_canvases(
    page: Page,
    viewport_width: int,
    viewport_height: int,
):
    """
    現在画面内に存在するCanvasを取得する。
    """

    canvases = page.locator("canvas")
    result = []

    for i in range(canvases.count()):
        canvas = canvases.nth(i)
        box = canvas.bounding_box()

        if box is None:
            continue

        visible = (
            box["x"] + box["width"] > 0
            and box["x"] < viewport_width
            and box["y"] + box["height"] > 0
            and box["y"] < viewport_height
        )

        if not visible:
            continue

        alignment = canvas.evaluate(
            """
            canvas => {
                const parent = canvas.closest(".js-page-area");

                if (!parent) {
                    return null;
                }

                if (parent.classList.contains("align-right")) {
                    return "right";
                }

                if (parent.classList.contains("align-left")) {
                    return "left";
                }

                return null;
            }
            """
        )

        result.append(
            {
                "index": i,
                "canvas": canvas,
                "box": box,
                "alignment": alignment,
            }
        )

    # 実際の画面位置で左→右に並べる
    result.sort(
        key=lambda item: item["box"]["x"]
    )

    return result


def save_canvas_native_resolution(
    canvas,
    output_path: Path,
) -> tuple[int, int]:
    """
    CSS表示サイズではなくCanvas内部サイズでPNG保存。
    """

    result = canvas.evaluate(
        """
        canvas => ({
            width: canvas.width,
            height: canvas.height,
            data: canvas.toDataURL("image/png")
        })
        """
    )

    prefix = "data:image/png;base64,"
    data_url = result["data"]

    if not data_url.startswith(prefix):
        raise RuntimeError(
            "CanvasをPNGとして取得できませんでした。"
        )

    png = base64.b64decode(
        data_url[len(prefix):]
    )

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_path.write_bytes(png)

    return (
        result["width"],
        result["height"],
    )


@dataclass
class TocEntry:
    title: str
    start_page: int


def get_table_of_contents(
    page: Page,
) -> list[TocEntry]:
    """
    ビューア内の目次リンクから、

        ONE PIECE -> #mainPage-69

    のような情報を取得する。
    """

    links = page.locator(
        'a[href^="#mainPage-"]'
    )

    entries: list[TocEntry] = []

    seen_pages: set[int] = set()

    for i in range(links.count()):
        link = links.nth(i)

        href = link.get_attribute("href")

        if not href:
            continue

        match = re.fullmatch(
            r"#mainPage-(\d+)",
            href,
        )

        if not match:
            continue

        start_page = int(
            match.group(1)
        )

        # 同じページへのリンクが複数ある場合は除外
        if start_page in seen_pages:
            continue

        title = link.inner_text().strip()

        if not title:
            continue

        entries.append(
            TocEntry(
                title=title,
                start_page=start_page,
            )
        )

        seen_pages.add(
            start_page
        )

    # DOM上の順番に依存せず、
    # 内部ページ番号順に並べる
    entries.sort(
        key=lambda entry: entry.start_page
    )

    return entries