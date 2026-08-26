from dataclasses import dataclass
from enum import Enum


COLOR_SUFFIX = "(巻頭カラー)"
MONO_SUFFIX = "(モノクロ冒頭ページ)"


EXCLUDE_KEYWORDS = [
    "付録",
    "特別付録",
    "応募者全員サービス",
    "本誌版次号予告",
    "本誌版目次・作者コメント",
    "ジャンプ探検隊",
    "企画",
    "クロニクルシール",
    "EMPEROURシール",
    "応募者全員大サービス",
    "ホログラムステッカー",
    "潜入ルポ漫画",
    "6大ニュース",
    "人気投票",
    "全員サービス応募",
    "プレゼント応募",
    "ジャンプと僕",
    "特大プレゼント",
    "おしらせ",
    "ジャンプフェスタ",
    "記念",
    "JF20",
    "ジャンプビクトリー",
    
]


class EntryType(str, Enum):
    NORMAL = "normal"
    COLOR = "color"
    MONO = "mono"
    EXCLUDE = "exclude"


@dataclass
class ClassifiedEntry:
    original_title: str
    work_title: str
    entry_type: EntryType


def classify_title(title: str) -> ClassifiedEntry:
    if title.endswith(COLOR_SUFFIX):
        return ClassifiedEntry(
            original_title=title,
            work_title=title.removesuffix(COLOR_SUFFIX),
            entry_type=EntryType.COLOR,
        )

    if title.endswith(MONO_SUFFIX):
        return ClassifiedEntry(
            original_title=title,
            work_title=title.removesuffix(MONO_SUFFIX),
            entry_type=EntryType.MONO,
        )

    if any(
        keyword in title
        for keyword in EXCLUDE_KEYWORDS
    ):
        return ClassifiedEntry(
            original_title=title,
            work_title=title,
            entry_type=EntryType.EXCLUDE,
        )

    return ClassifiedEntry(
        original_title=title,
        work_title=title,
        entry_type=EntryType.NORMAL,
    )