from dataclasses import dataclass
from pathlib import Path
from tempfile import NamedTemporaryFile

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject


@dataclass
class IssuePages:
    issue_dir: Path
    color: list[Path]
    main: list[Path]

def prepend_blank_cover(
    images: list[Image.Image],
) -> None:
    """
    Panels対策として、
    PDF全体の先頭に空白ページを1枚追加する。

    Panelsが1ページ目を表紙として単独扱いしても、
    2ページ目以降の見開き配置を維持するため。
    """

    if not images:
        return

    width, height = images[0].size

    blank = Image.new(
        "RGB",
        (width, height),
        "white",
    )

    images.insert(
        0,
        blank,
    )

def collect_issue_pages(
    issue_dir: Path,
) -> IssuePages:
    color_dir = issue_dir / "color"
    main_dir = issue_dir / "main"

    color = (
        sorted(color_dir.glob("*.png"))
        if color_dir.exists()
        else []
    )

    main = (
        sorted(main_dir.glob("*.png"))
        if main_dir.exists()
        else []
    )

    return IssuePages(
        issue_dir=issue_dir,
        color=color,
        main=main,
    )


def create_blank_image(
    reference_image: Path,
) -> Image.Image:
    with Image.open(reference_image) as image:
        size = image.size

    return Image.new(
        "RGB",
        size,
        "white",
    )


def open_rgb(
    path: Path,
) -> Image.Image:
    image = Image.open(path)

    if image.mode != "RGB":
        converted = image.convert("RGB")
        image.close()
        return converted

    return image


def append_issue_to_pdf_images(
    result: list[Image.Image],
    issue: IssuePages,
) -> None:
    """
    1話を独立したレイアウトブロックとして追加する。

    NORMAL:
        blank
        main...

    COLOR:
        color...
        blank
        main...

    最後にページ数を偶数へ揃え、
    次の話を結合しても見開き位置が変わらないようにする。
    """

    # この話を追加する前のページ数
    block_start = len(result)

    # --------------------------------------------------
    # カラー回
    # --------------------------------------------------
    if issue.color:
        print("  layout: COLOR")

        # カラーは先頭ページを独立させない。
        # そのまま見開きとして開始する。
        for path in issue.color:
            result.append(
                open_rgb(path)
            )

        # モノクロ本編が存在する場合、
        # MAIN 001を独立させるための空白を入れる。
        if issue.main:
            result.append(
                create_blank_image(
                    issue.main[0]
                )
            )

            for path in issue.main:
                result.append(
                    open_rgb(path)
                )

    # --------------------------------------------------
    # 通常回
    # --------------------------------------------------
    elif issue.main:
        print("  layout: NORMAL")

        # 各話の先頭に必ず空白ページを入れる。
        result.append(
            create_blank_image(
                issue.main[0]
            )
        )

        for path in issue.main:
            result.append(
                open_rgb(path)
            )

    else:
        return

    # --------------------------------------------------
    # 話末尾の調整
    # --------------------------------------------------
    #
    # この話だけのページ数を取得。
    #
    # 各話のブロックを偶数ページにしておけば、
    # 次の話を結合しても開始位置の偶奇が変わらない。
    # --------------------------------------------------

    block_page_count = (
        len(result) - block_start
    )

    if block_page_count % 2 != 0:
        reference = None

        if issue.main:
            reference = issue.main[-1]

        elif issue.color:
            reference = issue.color[-1]

        if reference is not None:
            result.append(
                create_blank_image(
                    reference
                )
            )

            block_page_count += 1

            print(
                "  trailing blank added"
            )

    print(
        f"  block pages: {block_page_count}"
    )

def set_right_to_left(
    pdf_file: Path,
) -> None:
    reader = PdfReader(
        str(pdf_file)
    )

    writer = PdfWriter()

    for page in reader.pages:
        writer.add_page(page)

    viewer_preferences = DictionaryObject()

    viewer_preferences.update(
        {
            NameObject("/Direction"):
                NameObject("/R2L"),
        }
    )

    writer._root_object.update(
        {
            NameObject("/PageLayout"):
                NameObject("/TwoPageRight"),
            NameObject("/ViewerPreferences"):
                viewer_preferences,
        }
    )

    temp_file = (
        pdf_file.with_suffix(
            ".tmp.pdf"
        )
    )

    with temp_file.open(
        "wb"
    ) as file:
        writer.write(file)

    temp_file.replace(
        pdf_file
    )


def build_pdf(
    images: list[Image.Image],
    output_file: Path,
) -> None:
    if not images:
        raise ValueError(
            "PDF化する画像がありません。"
        )

    output_file.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    first = images[0]
    rest = images[1:]

    try:
        first.save(
            output_file,
            "PDF",
            save_all=True,
            append_images=rest,
            resolution=150.0,
        )
    finally:
        for image in images:
            image.close()

    set_right_to_left(
        output_file
    )


def build_work_pdfs(
    work_dir: Path,
    output_root: Path,
    issues_per_pdf: int = 10,
) -> list[Path]:
    issue_dirs = [
        path
        for path in work_dir.iterdir()
        if path.is_dir()
        and not path.name.startswith("_")
    ]

    if not issue_dirs:
        return []

    issue_dirs.sort(
        key=lambda path: path.name
    )

    work_title = work_dir.name

    output_dir = (
        output_root
        / work_title
    )

    created: list[Path] = []

    for start in range(
        0,
        len(issue_dirs),
        issues_per_pdf,
    ):
        group = issue_dirs[
            start:start + issues_per_pdf
        ]

        pdf_images: list[Image.Image] = []

        for issue_dir in group:
            issue = collect_issue_pages(
                issue_dir
            )

            print()
            print(
                f"{work_title} / "
                f"{issue_dir.name}"
            )
            print(
                f"  color: "
                f"{len(issue.color)}"
            )
            print(
                f"  main: "
                f"{len(issue.main)}"
            )

            append_issue_to_pdf_images(
                pdf_images,
                issue,
            )

        if not pdf_images:
            continue

        first_number = start + 1
        last_number = (
            start + len(group)
        )

        output_file = (
            output_dir
            / (
                f"{work_title}_"
                f"{first_number:03d}-"
                f"{last_number:03d}.pdf"
            )
        )

        # PanelsではPDFの1ページ目が表紙として単独表示されるため、
        # 全話のレイアウト完成後に空白表紙を1枚だけ追加する。
        prepend_blank_cover(
            pdf_images
        )

        print()
        print(
            f"PDF作成: "
            f"{output_file}"
        )
        print(
            f"PDFページ数: "
            f"{len(pdf_images)}"
        )

        build_pdf(
            pdf_images,
            output_file,
        )
    return created