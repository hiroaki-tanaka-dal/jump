from jump_pdf.android.device import adb


def tap(
    x: int,
    y: int,
) -> None:
    adb(
        "shell",
        "input",
        "tap",
        str(x),
        str(y),
    )