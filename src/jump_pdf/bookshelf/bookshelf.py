import re
from dataclasses import asdict, dataclass
from urllib.parse import urljoin

from playwright.sync_api import Page


BOOKSHELF_URL = (
    "https://shonenjumpplus.com/my/bookshelf/magazine/"
    "13933686331636289886"
)


@dataclass
class Magazine:
    title: str
    url: str
    magazine_id: str
    year: int | None
    issue: str | None
    published_at: str | None


def parse_magazine_title(
    title: str,
) -> tuple[int | None, str | None]:
    """
    例:
      週刊少年ジャンプ 2026年36号
          -> (2026, "36")

      週刊少年ジャンプ 2026年37・38合併号
          -> (2026, "37_38")

      週刊少年ジャンプ 2025年36･37合併号
          -> (2025, "36_37")
    """

    match = re.search(
        r"(\d{4})年"
        r"(\d+)"
        r"[・･]"
        r"(\d+)"
        r"合併号",
        title,
    )

    if match:
        year = int(match.group(1))
        issue = (
            f"{match.group(2)}_"
            f"{match.group(3)}"
        )

        return year, issue

    match = re.search(
        r"(\d{4})年(\d+)号",
        title,
    )

    if match:
        return (
            int(match.group(1)),
            match.group(2),
        )

    return None, None


def extract_magazines(
    page: Page,
) -> list[Magazine]:
    """
    現在表示されている本棚ページから
    週刊少年ジャンプを取得する。
    """

    links = page.locator(
        'a[href*="/magazine/"]'
    )

    magazines: list[Magazine] = []
    seen_urls: set[str] = set()

    for i in range(links.count()):
        link = links.nth(i)

        href = link.get_attribute("href")

        if not href:
            continue

        # 本棚のページ送りURL等は除外
        if "/my/bookshelf/" in href:
            continue

        text = link.inner_text().strip()

        if (
            "週刊少年ジャンプ"
            not in text
        ):
            continue

        url = urljoin(
            page.url,
            href,
        )

        if url in seen_urls:
            continue

        match = re.search(
            r"/magazine/(\d+)",
            url,
        )

        if not match:
            continue

        magazine_id = match.group(1)

        # タイトルと日付を分離
        lines = [
            line.strip()
            for line in text.splitlines()
            if line.strip()
        ]

        if not lines:
            continue

        title = lines[0]

        published_at = None

        for line in lines[1:]:
            if re.fullmatch(
                r"\d{4}/\d{2}/\d{2}",
                line,
            ):
                published_at = (
                    line.replace("/", "-")
                )
                break

        year, issue = (
            parse_magazine_title(title)
        )

        magazines.append(
            Magazine(
                title=title,
                url=url,
                magazine_id=magazine_id,
                year=year,
                issue=issue,
                published_at=published_at,
            )
        )

        seen_urls.add(url)

    return magazines


def find_next_page_url(
    page: Page,
) -> str | None:
    """
    本棚の「次へ」URLを取得する。
    """

    links = page.locator("a")

    for i in range(links.count()):
        link = links.nth(i)

        text = link.inner_text().strip()

        if text != "次へ":
            continue

        href = link.get_attribute("href")

        if not href:
            continue

        return urljoin(
            page.url,
            href,
        )

    return None


def collect_magazines(
    page: Page,
    max_pages: int | None = None,
) -> list[Magazine]:
    """
    本棚をページネーションしながら、
    購入済みジャンプをすべて取得する。

    max_pages=None:
        最後まで取得

    max_pages=2:
        本棚2ページだけ取得
    """

    magazines: list[Magazine] = []
    seen_magazines: set[str] = set()
    seen_pages: set[str] = set()

    current_url = BOOKSHELF_URL
    page_number = 1

    while current_url:
        if current_url in seen_pages:
            print(
                "同じ本棚URLを検出したため終了します。"
            )
            break

        seen_pages.add(current_url)

        print()
        print("=" * 70)
        print(
            f"本棚ページ {page_number}"
        )
        print(current_url)
        print("=" * 70)

        page.goto(
            current_url,
            wait_until="domcontentloaded",
        )

        page.wait_for_timeout(1500)

        found = extract_magazines(page)

        print(
            f"検出: {len(found)}冊"
        )

        for magazine in found:
            if (
                magazine.magazine_id
                in seen_magazines
            ):
                continue

            magazines.append(magazine)

            seen_magazines.add(
                magazine.magazine_id
            )

            print(
                f"  {magazine.title}"
                f"  {magazine.published_at or ''}"
            )

        if (
            max_pages is not None
            and page_number >= max_pages
        ):
            break

        next_url = find_next_page_url(
            page
        )

        if not next_url:
            print()
            print("最終ページです。")
            break

        current_url = next_url
        page_number += 1

    return magazines


def magazine_to_dict(
    magazine: Magazine,
) -> dict:
    return asdict(magazine)