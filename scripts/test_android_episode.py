from pathlib import Path
import time

from jump_pdf.android.capture import (
    capture_screen,
    crop_screen,
)
from jump_pdf.android.device import (
    list_devices,
)
from jump_pdf.android.navigator import (
    tap,
)
from jump_pdf.android.ui import (
    find_clickable_parent_by_text,
    get_page_position,
)


OUTPUT_DIR = Path(
    "data/pages/android_episode"
)


# ============================================================
# 待機時間
# ============================================================

# ページ送り後
PAGE_WAIT_SECONDS = 2.0

# オーバーレイ表示/非表示
OVERLAY_WAIT_SECONDS = 1.0

# 次話への遷移
NEXT_EPISODE_WAIT_SECONDS = 4.0


# ============================================================
# タップ位置
# ============================================================

# 1080 x 2340 縦画面

# オーバーレイ表示 / 非表示
OVERLAY_TAP_X = 300
OVERLAY_TAP_Y = 1170

# 次ページ
NEXT_PAGE_X = 100
NEXT_PAGE_Y = 1170

# ============================================================
# Crop
# ============================================================

CROP_LEFT = 0
CROP_TOP = 330
CROP_RIGHT = 0
CROP_BOTTOM = 330


def get_episode_page_info(
) -> tuple[int, int]:
    """
    オーバーレイを表示して、

        current / total

    をUIから取得する。

    取得後はオーバーレイを閉じる。
    """

    print()
    print(
        "オーバーレイを表示します"
    )

    tap(
        OVERLAY_TAP_X,
        OVERLAY_TAP_Y,
    )

    time.sleep(
        OVERLAY_WAIT_SECONDS
    )

    position = (
        get_page_position()
    )

    if position is None:
        raise RuntimeError(
            "ページ数を取得できませんでした。"
        )

    current_page, total_pages = (
        position
    )

    print(
        "viewer page: "
        f"{current_page}/"
        f"{total_pages}"
    )

    print(
        "オーバーレイを閉じます"
    )

    tap(
        OVERLAY_TAP_X,
        OVERLAY_TAP_Y,
    )

    time.sleep(
        OVERLAY_WAIT_SECONDS
    )

    return (
        current_page,
        total_pages,
    )


def capture_episode(
    current_page: int,
    total_pages: int,
) -> int:
    """
    現在表示中のページから
    最終ページまで全部保存する。

    ページの除外判断はここでは行わない。
    """

    remaining_pages = (
        total_pages
        - current_page
        + 1
    )

    print()
    print("=" * 70)
    print("画像取得開始")
    print("=" * 70)

    print(
        "viewer: "
        f"{current_page}/"
        f"{total_pages}"
    )

    print(
        "capture pages: "
        f"{remaining_pages}"
    )

    saved_count = 0

    for viewer_page in range(
        current_page,
        total_pages + 1,
    ):
        saved_count += 1

        raw_file = (
            OUTPUT_DIR
            / "_current_raw.png"
        )

        # ------------------------------------------
        # 現在画面を取得
        # ------------------------------------------

        capture_screen(
            raw_file
        )

        # ------------------------------------------
        # Cropして保存
        # ------------------------------------------

        output_file = (
            OUTPUT_DIR
            / f"{saved_count:03d}.png"
        )

        crop_screen(
            source_file=raw_file,
            output_file=output_file,
            left=CROP_LEFT,
            top=CROP_TOP,
            right=CROP_RIGHT,
            bottom=CROP_BOTTOM,
        )

        print(
            f"[{saved_count:03d}/"
            f"{remaining_pages:03d}] "
            f"viewer={viewer_page}/"
            f"{total_pages} "
            f"saved={output_file.name}"
        )

        # ------------------------------------------
        # 最終ページなら終了
        # ------------------------------------------

        if (
            viewer_page
            >= total_pages
        ):
            break

        # ------------------------------------------
        # 次ページ
        # ------------------------------------------

        tap(
            NEXT_PAGE_X,
            NEXT_PAGE_Y,
        )

        time.sleep(
            PAGE_WAIT_SECONDS
        )

    raw_file = (
        OUTPUT_DIR
        / "_current_raw.png"
    )

    raw_file.unlink(
        missing_ok=True
    )

    return saved_count


def goto_next_episode() -> None:
    """
    オーバーレイを表示し、

    UIツリーから
    「次の話」

    を探して実際のクリック領域を押す。
    """

    print()
    print(
        "オーバーレイを表示します"
    )

    tap(
        OVERLAY_TAP_X,
        OVERLAY_TAP_Y,
    )

    time.sleep(
        OVERLAY_WAIT_SECONDS
    )

    next_episode = (
        find_clickable_parent_by_text(
            "次の話"
        )
    )

    if next_episode is None:
        raise RuntimeError(
            "「次の話」ボタンが"
            "見つかりませんでした。"
        )

    if not next_episode.enabled:
        raise RuntimeError(
            "「次の話」ボタンが"
            "無効です。"
        )

    x, y = (
        next_episode.center
    )

    print(
        "次の話ボタンを検出:"
    )

    print(
        f"  bounds="
        f"{next_episode.bounds}"
    )

    print(
        f"  tap=({x}, {y})"
    )

    tap(
        x,
        y,
    )

    time.sleep(
        NEXT_EPISODE_WAIT_SECONDS
    )

    print(
        "次の話へ移動しました。"
    )


def main():
    devices = (
        list_devices()
    )

    if not devices:
        raise RuntimeError(
            "Android端末が"
            "見つかりません。"
        )

    print()
    print("=" * 70)
    print("Android漫画取得")
    print("=" * 70)

    print(
        f"device: {devices[0]}"
    )

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print(
        "ジャンプ＋で対象話の"
        "取得開始ページを"
        "表示してください。"
    )

    print()
    print(
        "オーバーレイは"
        "閉じておいてください。"
    )

    print()

    input(
        "準備できたら Enter > "
    )

    # ========================================================
    # ページ情報取得
    # ========================================================

    current_page, total_pages = (
        get_episode_page_info()
    )

    # ========================================================
    # 全ページ取得
    # ========================================================

    saved_count = (
        capture_episode(
            current_page,
            total_pages,
        )
    )

    print()
    print("=" * 70)
    print("画像取得完了")
    print("=" * 70)

    print(
        f"saved: {saved_count}"
    )

    print(
        f"output: "
        f"{OUTPUT_DIR.resolve()}"
    )

    # ========================================================
    # 次話へ
    # ========================================================

    goto_next_episode()


if __name__ == "__main__":
    main()