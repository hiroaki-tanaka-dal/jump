import subprocess


def adb(
    *args: str,
    capture_output: bool = True,
) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["adb", *args],
        check=True,
        capture_output=capture_output,
    )


def list_devices() -> list[str]:
    result = adb(
        "devices"
    )

    text = result.stdout.decode(
        "utf-8",
        errors="ignore",
    )

    devices: list[str] = []

    for line in text.splitlines()[1:]:
        line = line.strip()

        if not line:
            continue

        parts = line.split()

        if (
            len(parts) >= 2
            and parts[1] == "device"
        ):
            devices.append(
                parts[0]
            )

    return devices