import json
import statistics
from collections import defaultdict
from pathlib import Path


TOC_DIR = Path("data/analysis/toc")
OUTPUT_FILE = Path("data/analysis/toc_report.json")


def load_toc_files() -> list[dict]:
    files = sorted(
        TOC_DIR.glob("*.json"),
        reverse=True,
    )

    if not files:
        raise RuntimeError(
            f"{TOC_DIR} にJSONがありません。"
        )

    magazines = []

    for file in files:
        try:
            data = json.loads(
                file.read_text(
                    encoding="utf-8"
                )
            )

            magazines.append(data)

        except Exception as exc:
            print(
                f"WARNING: {file} "
                f"を読み込めませんでした: {exc}"
            )

    return magazines


def build_statistics(
    magazines: list[dict],
) -> dict:
    stats = defaultdict(
        lambda: {
            "appearances": 0,
            "page_counts": [],
            "issues": [],
            "entries": [],
        }
    )

    for magazine in magazines:
        issue = magazine.get("issue")
        year = magazine.get("year")
        magazine_title = magazine.get("title")

        if year and issue:
            issue_key = f"{year}-{issue}"
        else:
            issue_key = magazine_title

        for entry in magazine.get(
            "entries",
            []
        ):
            title = entry["title"]

            record = stats[title]

            record["appearances"] += 1

            page_count = entry.get(
                "page_count"
            )

            if page_count is not None:
                record[
                    "page_counts"
                ].append(page_count)

            record["issues"].append(
                issue_key
            )

            record["entries"].append(
                {
                    "issue": issue_key,
                    "magazine": magazine_title,
                    "order": entry.get("order"),
                    "start_internal_page": (
                        entry.get(
                            "start_internal_page"
                        )
                    ),
                    "end_internal_page": (
                        entry.get(
                            "end_internal_page"
                        )
                    ),
                    "page_count": page_count,
                }
            )

    result = {}

    for title, record in stats.items():
        counts = record["page_counts"]

        if counts:
            min_pages = min(counts)
            max_pages = max(counts)
            average_pages = round(
                statistics.mean(counts),
                2,
            )
            median_pages = round(
                statistics.median(counts),
                2,
            )
        else:
            min_pages = None
            max_pages = None
            average_pages = None
            median_pages = None

        result[title] = {
            "appearances": (
                record["appearances"]
            ),
            "min_pages": min_pages,
            "max_pages": max_pages,
            "average_pages": average_pages,
            "median_pages": median_pages,
            "page_counts": counts,
            "issues": record["issues"],
            "entries": record["entries"],
        }

    return result


def print_report(
    magazines: list[dict],
    stats: dict,
) -> None:
    print()
    print("=" * 100)
    print("目次統計レポート")
    print("=" * 100)

    print(
        f"解析号数: {len(magazines)}"
    )

    print(
        f"ユニークタイトル数: "
        f"{len(stats)}"
    )

    print()
    print(
        f"{'回数':>4} "
        f"{'最小':>4} "
        f"{'最大':>4} "
        f"{'平均':>6} "
        f"{'中央値':>6} "
        f"タイトル"
    )

    print("-" * 100)

    ordered = sorted(
        stats.items(),
        key=lambda item: (
            -item[1]["appearances"],
            item[0],
        ),
    )

    for title, record in ordered:
        appearances = record[
            "appearances"
        ]

        min_pages = (
            str(record["min_pages"])
            if record["min_pages"]
            is not None
            else "-"
        )

        max_pages = (
            str(record["max_pages"])
            if record["max_pages"]
            is not None
            else "-"
        )

        average = (
            f"{record['average_pages']:.1f}"
            if record["average_pages"]
            is not None
            else "-"
        )

        median = (
            f"{record['median_pages']:.1f}"
            if record["median_pages"]
            is not None
            else "-"
        )

        print(
            f"{appearances:>4} "
            f"{min_pages:>4} "
            f"{max_pages:>4} "
            f"{average:>6} "
            f"{median:>6} "
            f"{title}"
        )


def print_suspicious_entries(
    stats: dict,
) -> None:
    """
    分類ルール作成時に参考になりそうな
    特徴的な項目を表示する。
    """

    print()
    print("=" * 100)
    print("要確認候補")
    print("=" * 100)

    ordered = sorted(
        stats.items(),
        key=lambda item: (
            item[1]["appearances"],
            item[0],
        ),
    )

    for title, record in ordered:
        appearances = record[
            "appearances"
        ]

        average = record[
            "average_pages"
        ]

        reasons = []

        # 1〜2回しか出ない
        if appearances <= 2:
            reasons.append(
                "出現回数が少ない"
            )

        # 平均5ページ以下
        if (
            average is not None
            and average <= 5
        ):
            reasons.append(
                "ページ数が少ない"
            )

        keywords = [
            "企画",
            "付録",
            "応募",
            "サービス",
            "予告",
            "ポスター",
            "プレゼント",
        ]

        if any(
            keyword in title
            for keyword in keywords
        ):
            reasons.append(
                "特殊項目キーワード"
            )

        if not reasons:
            continue

        reason_text = " / ".join(
            reasons
        )

        print(
            f"{title}"
        )

        print(
            f"  出現: "
            f"{appearances}回"
        )

        print(
            f"  pages: "
            f"{record['page_counts']}"
        )

        print(
            f"  理由: "
            f"{reason_text}"
        )

        print()


def main():
    magazines = load_toc_files()

    stats = build_statistics(
        magazines
    )

    print_report(
        magazines,
        stats,
    )

    print_suspicious_entries(
        stats
    )

    report = {
        "magazine_count": len(
            magazines
        ),
        "unique_title_count": len(
            stats
        ),
        "titles": stats,
    }

    OUTPUT_FILE.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    OUTPUT_FILE.write_text(
        json.dumps(
            report,
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print()
    print("=" * 100)
    print(
        f"詳細JSON: {OUTPUT_FILE}"
    )
    print("=" * 100)


if __name__ == "__main__":
    main()