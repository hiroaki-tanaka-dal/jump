from pathlib import Path

from jump_pdf.android.capture import capture_screen
from jump_pdf.android.device import list_devices


OUTPUT_FILE = Path(
    "data/pages/android_test.png"
)


def main():
    devices = list_devices()

    print(
        f"devices: {devices}"
    )

    if not devices:
        raise RuntimeError(
            "Android端末が見つかりません。"
        )

    output_file = capture_screen(
        OUTPUT_FILE
    )

    print(
        f"saved: {output_file.resolve()}"
    )


if __name__ == "__main__":
    main()
