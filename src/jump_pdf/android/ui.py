import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass

from jump_pdf.android.device import adb


@dataclass
class UIElement:
    text: str

    bounds: tuple[
        int,
        int,
        int,
        int,
    ]

    clickable: bool
    enabled: bool

    @property
    def center(
        self,
    ) -> tuple[int, int]:
        left, top, right, bottom = (
            self.bounds
        )

        return (
            (left + right) // 2,
            (top + bottom) // 2,
        )


def dump_ui() -> ET.Element:
    """
    現在のAndroid UI階層を取得する。
    """

    result = adb(
        "exec-out",
        "uiautomator",
        "dump",
        "/dev/tty",
    )

    text = result.stdout.decode(
        "utf-8",
        errors="ignore",
    )

    # XML開始位置
    start = text.find(
        "<?xml"
    )

    if start == -1:
        raise RuntimeError(
            "UI XMLの開始位置を取得できませんでした。\n"
            f"output: {text[:500]}"
        )

    # XML終了位置
    end_marker = "</hierarchy>"

    end = text.find(
        end_marker,
        start,
    )

    if end == -1:
        raise RuntimeError(
            "UI XMLの終了位置を取得できませんでした。\n"
            f"output: {text[-500:]}"
        )

    end += len(
        end_marker
    )

    # XML部分だけ抽出
    xml_text = text[
        start:end
    ]

    try:
        return ET.fromstring(
            xml_text
        )

    except ET.ParseError as exc:
        raise RuntimeError(
            "UI XMLの解析に失敗しました。\n"
            f"{exc}\n"
            f"XML先頭: {xml_text[:300]}"
        ) from exc


def parse_bounds(
    value: str,
) -> tuple[
    int,
    int,
    int,
    int,
]:
    """
    [40,2167][152,2280]

    ↓

    (40, 2167, 152, 2280)
    """

    match = re.fullmatch(
        r"\[(\d+),(\d+)\]"
        r"\[(\d+),(\d+)\]",
        value,
    )

    if not match:
        raise ValueError(
            f"不正なbounds: {value}"
        )

    values = tuple(
        int(item)
        for item in match.groups()
    )

    return values


def node_to_element(
    node: ET.Element,
) -> UIElement:
    return UIElement(
        text=node.attrib.get(
            "text",
            "",
        ),
        bounds=parse_bounds(
            node.attrib["bounds"]
        ),
        clickable=(
            node.attrib.get(
                "clickable"
            )
            == "true"
        ),
        enabled=(
            node.attrib.get(
                "enabled"
            )
            == "true"
        ),
    )


def get_page_position(
) -> tuple[int, int] | None:
    """
    UI上の

        1/61
        20/61

    のようなページ表示を探す。

    Returns:
        (current_page, total_pages)
    """

    root = dump_ui()

    for node in root.iter(
        "node"
    ):
        text = node.attrib.get(
            "text",
            "",
        )

        match = re.fullmatch(
            r"(\d+)/(\d+)",
            text,
        )

        if not match:
            continue

        return (
            int(match.group(1)),
            int(match.group(2)),
        )

    return None


def find_clickable_parent_by_text(
    text: str,
) -> UIElement | None:
    """
    指定文字列を持つ要素から、
    clickable=true の親要素を探す。

    「次の話」のTextViewそのものではなく、
    実際に押せる親Viewを取得するために使う。
    """

    root = dump_ui()

    def search(
        node: ET.Element,
    ) -> UIElement | None:

        children = list(node)

        for child in children:

            if (
                child.attrib.get(
                    "text"
                )
                == text
            ):
                if (
                    node.attrib.get(
                        "clickable"
                    )
                    == "true"
                ):
                    return (
                        node_to_element(
                            node
                        )
                    )

            result = search(
                child
            )

            if (
                result is not None
            ):
                return result

        return None

    return search(root)