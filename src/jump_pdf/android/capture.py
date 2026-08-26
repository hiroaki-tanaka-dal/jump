from pathlib import Path

from PIL import Image

from jump_pdf.android.device import adb


def capture_screen(
    output_file: Path,
) -> Path:
    """
    Android画面全体をPNGとして取得する。
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    result = adb(
        "exec-out",
        "screencap",
        "-p",
    )

    output_file.write_bytes(
        result.stdout
    )

    return output_file


def crop_screen(
    source_file: Path,
    output_file: Path,
    *,
    left: int = 0,
    top: int = 0,
    right: int = 0,
    bottom: int = 0,
) -> Path:
    """
    スクリーンショットの四辺を
    指定pxだけ切り落として保存する。
    """

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with Image.open(
        source_file
    ) as image:
        width, height = image.size

        crop_left = left
        crop_top = top
        crop_right = (
            width - right
        )
        crop_bottom = (
            height - bottom
        )

        if (
            crop_left >= crop_right
            or crop_top >= crop_bottom
        ):
            raise ValueError(
                "crop範囲が不正です: "
                f"{width}x{height}"
            )

        cropped = image.crop(
            (
                crop_left,
                crop_top,
                crop_right,
                crop_bottom,
            )
        )

        cropped.save(
            output_file,
            "PNG",
        )

    return output_file