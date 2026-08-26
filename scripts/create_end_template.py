from pathlib import Path

from PIL import Image


SOURCE = Path(
    "data/pages/android_test/003_raw.png"
)

OUTPUT = Path(
    "data/templates/jump_plus_episode_end.png"
)

LEFT = 250
TOP = 220
RIGHT = 830
BOTTOM = 700


def main():
    if not SOURCE.exists():
        raise RuntimeError(
            f"元画像がありません: {SOURCE}"
        )

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    with Image.open(SOURCE) as image:
        print(
            f"source size: "
            f"{image.width} x {image.height}"
        )

        cropped = image.crop(
            (
                LEFT,
                TOP,
                RIGHT,
                BOTTOM,
            )
        )

        cropped.save(
            OUTPUT,
            "PNG",
        )

        print(
            f"template size: "
            f"{cropped.width} x "
            f"{cropped.height}"
        )

    print(
        f"saved: {OUTPUT.resolve()}"
    )


if __name__ == "__main__":
    main()
