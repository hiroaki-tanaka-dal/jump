from pathlib import Path
import time

from jump_pdf.android.capture import (
    capture_manga_page,
)
from jump_pdf.android.device import (
    get_screen_size,
    list_devices,
)
from jump_pdf.android.navigator import (
    tap,
)


OUTPUT_DIR = Path(
    "data/pages/android_test"
)

# 最初は3ページで確認。
PAGE_COUNT = 3

# ページ送り後の待機
PAGE_WAIT_SECONDS = 2.0


# ============================================================
# タップ位置
# ============================================================
#
# 縦画面の左中央をタップ。
#
# 1080x2340なら、
#
# x ≈ 86
# y = 1170
#
# になる。
#

NEXT_PAGE_X_RATIO = 0.08
NEXT_PAGE_Y_RATIO = 0.50


# ============================================================
# Crop設定
# ============================================================
#
# まずは0で実行して、
# android_test/001_raw.png を確認しながら調整する。
#
# 例:
#
# CROP_TOP = 80
# CROP_BOTTOM = 100
#
# など。
#


CROP_LEFT = 0
CROP_TOP = 330
CROP_RIGHT = 0
CROP_BOTTOM = 330


# 最初の調整時だけTrue推奨。
# raw画像とcrop後画像を両方残す。
KEEP_RAW = True


def main():
    devices = list_devices()

    if not devices:
        raise RuntimeError(
            "Android端末が見つかりません。"
        )

    print(
        f"device: {devices[0]}"
    )

    width, height = (
        get_screen_size()
    )

    print(
        f"screen: {width} x {height}"
    )

    # 縦画面であることを確認
    if width >= height:
        raise RuntimeError(
            "端末が横画面になっています。\n"
            "ジャンプ＋を縦画面にしてから"
            "再実行してください。"
        )

    next_x = int(
        width
        * NEXT_PAGE_X_RATIO
    )

    next_y = int(
        height
        * NEXT_PAGE_Y_RATIO
    )

    print(
        "next page tap: "
        f"x={next_x}, "
        f"y={next_y}"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 70)
    print("Android漫画ページ取得")
    print("=" * 70)
    print()
    print(
        "1. Androidを縦画面にしてください。"
    )
    print(
        "2. ジャンプ＋で対象作品の"
        "先頭ページを表示してください。"
    )
    print(
        "3. 漫画ビューアのメニューを"
        "閉じた状態にしてください。"
    )
    print()

    input(
        "準備できたら Enter > "
    )

    for page_number in range(
        1,
        PAGE_COUNT + 1,
    ):
        output_file = (
            OUTPUT_DIR
            / f"{page_number:03d}.png"
        )

        capture_manga_page(
            output_file,
            left=CROP_LEFT,
            top=CROP_TOP,
            right=CROP_RIGHT,
            bottom=CROP_BOTTOM,
            keep_raw=KEEP_RAW,
        )

        print(
            f"[{page_number:03d}/"
            f"{PAGE_COUNT:03d}] "
            f"saved: {output_file}"
        )

        if (
            page_number
            >= PAGE_COUNT
        ):
            break

        # --------------------------------------------
        # 左中央をタップして次ページ
        # --------------------------------------------

        tap(
            next_x,
            next_y,
        )

        print(
            "  next-page tap: "
            f"{next_x}, {next_y}"
        )

        time.sleep(
            PAGE_WAIT_SECONDS
        )

    print()
    print("=" * 70)
    print("取得完了")
    print(
        f"保存先: "
        f"{OUTPUT_DIR.resolve()}"
    )
    print("=" * 70)


if __name__ == "__main__":
    main()