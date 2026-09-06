#!/usr/bin/env python3
"""Capture and inspect a Jump+ manga viewer screenshot over ADB.

This is intentionally a probe, not the final episode downloader.  It captures
exactly what Android renders and reports enough geometry to decide how the
landscape viewer should be split into individual manga pages.

No OCR is used.
"""

from __future__ import annotations

import argparse
import io
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from PIL import Image, ImageChops


@dataclass(frozen=True)
class Box:
    left: int
    top: int
    right: int
    bottom: int

    @property
    def width(self) -> int:
        return self.right - self.left

    @property
    def height(self) -> int:
        return self.bottom - self.top


def adb(*args: str, capture: bool = True) -> subprocess.CompletedProcess[bytes]:
    return subprocess.run(
        ["adb", *args],
        check=True,
        stdout=subprocess.PIPE if capture else None,
        stderr=subprocess.PIPE if capture else None,
    )


def ensure_device() -> str:
    result = adb("get-state")
    state = result.stdout.decode().strip()
    if state != "device":
        raise RuntimeError(f"ADB device is not ready: {state!r}")
    serial = adb("get-serialno").stdout.decode().strip()
    return serial


def capture_screen() -> Image.Image:
    raw = adb("exec-out", "screencap", "-p").stdout
    return Image.open(io.BytesIO(raw)).convert("RGB")


def edge_activity_bbox(image: Image.Image, tolerance: int = 12) -> Box | None:
    """Estimate the non-background rectangle without interpreting manga text.

    The four corner pixels are used as an estimate of the viewer background.
    This is only diagnostic: the returned rectangle is NOT yet assumed to be a
    reliable page crop.
    """
    w, h = image.size
    corners = [
        image.getpixel((0, 0)),
        image.getpixel((w - 1, 0)),
        image.getpixel((0, h - 1)),
        image.getpixel((w - 1, h - 1)),
    ]
    bg = tuple(sum(pixel[channel] for pixel in corners) // 4 for channel in range(3))
    background = Image.new("RGB", image.size, bg)
    diff = ImageChops.difference(image, background).convert("L")
    mask = diff.point(lambda value: 255 if value > tolerance else 0)
    bbox = mask.getbbox()
    if bbox is None:
        return None
    return Box(*bbox)


def save_halves(image: Image.Image, out_dir: Path) -> tuple[Path, Path]:
    """Save literal screen halves for comparison only.

    These are deliberately named screen_left/right rather than page_left/right:
    until the viewer geometry is confirmed we must not assume that half-screen
    equals one manga page.
    """
    w, h = image.size
    mid = w // 2
    left_path = out_dir / "screen_left.png"
    right_path = out_dir / "screen_right.png"
    image.crop((0, 0, mid, h)).save(left_path)
    image.crop((mid, 0, w, h)).save(right_path)
    return left_path, right_path


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture one landscape Jump+ viewer frame and inspect its geometry."
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("data/android_debug/landscape_probe"),
        help="output directory",
    )
    parser.add_argument(
        "--wait",
        type=float,
        default=1.0,
        help="seconds to wait before capture",
    )
    args = parser.parse_args()

    serial = ensure_device()
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"ADB device: {serial}")
    print("Keep Jump+ in landscape with viewer controls hidden.")
    if args.wait:
        time.sleep(args.wait)

    image = capture_screen()
    screenshot_path = args.out / "viewer_landscape.png"
    image.save(screenshot_path)

    left_path, right_path = save_halves(image, args.out)
    bbox = edge_activity_bbox(image)

    print()
    print("=== CAPTURE ===")
    print(f"screenshot : {screenshot_path}")
    print(f"screen size: {image.width} x {image.height}")
    print(f"center x   : {image.width // 2}")
    print(f"left half  : {left_path}")
    print(f"right half : {right_path}")

    print()
    print("=== DIAGNOSTIC REGION ===")
    if bbox is None:
        print("non-background bbox: not detected")
    else:
        print(
            "non-background bbox: "
            f"x={bbox.left}..{bbox.right}, y={bbox.top}..{bbox.bottom} "
            f"({bbox.width} x {bbox.height})"
        )

    print()
    print("NOTE:")
    print("  screen_left/right.png are diagnostic screen halves only.")
    print("  They are not yet treated as final manga-page crops.")
    print("  Once we confirm the actual viewer page rectangle, this script can")
    print("  crop left/right pages at that rectangle and feed them to the PDF pipeline.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
