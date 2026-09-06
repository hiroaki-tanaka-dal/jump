import shutil
from dataclasses import dataclass
from pathlib import Path

from PIL import Image
from pypdf import PdfReader, PdfWriter
from pypdf.generic import DictionaryObject, NameObject

from jump_pdf.pdf.history import update_work_history


ONESHOT_CATEGORY = "読み切り"
SERIAL_CATEGORY = "連載作品"
LEGACY_ONGOING_CATEGORY = "連載中"


@dataclass
class IssuePages:
    issue_dir: Path
    color: list[Path]
    main: list[Path]


def classify_work_category(
    issue_count: int,
    *,
    serial_confirmed: bool = False,
) -> str:
    """
    累計2話以上、または履歴上連載確定済みなら連載作品。
    それ以外の累計1話は読み切りとして扱う。
    """
    if issue_count <= 0:
        raise ValueError("issue_count は1以上である必要があります。")

    if serial_confirmed or issue_count >= 2:
        return SERIAL_CATEGORY

    return ONESHOT_CATEGORY


def cleanup_previous_category(
    output_root: Path,
    work_title: str,
    current_category: str,
) -> None:
    categories = (
        ONESHOT_CATEGORY,
        SERIAL_CATEGORY,
        LEGACY_ONGOING_CATEGORY,
    )

    for category in categories:
        if category == current_category:
            continue

        old_dir = output_root / category / work_title

        if old_dir.exists():
            print(f"旧カテゴリ削除: {old_dir}")
            shutil.rmtree(old_dir)


def build_pdf_filename(
    work_title: str,
    first_number: int,
    last_number: int,
    last_issue: str,
    *,
    is_oneshot: bool,
) -> str:
    base = (
        f"{work_title}_"
        f"{first_number:03d}-"
        f"{last_number:03d}"
    )

    if is_oneshot:
        return f"{base}.pdf"

    return f"{base}_{last_issue}.pdf"


def prepend_blank_cover(
    images: list[Image.Image],
) -> None:
    if not images:
        return

    width, height = images[0].size
    blank = Image.new(
        "RGB",
        (width, height),
        "white",
    )
    images.insert(0, blank)


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


def first_issue_has_serial_signal(
    issue_dirs: list[Path],
) -> bool:
    """
    初回1話しかない作品について、巻頭カラー相当の color と
    本編の main が両方存在する場合を新連載シグナルとして扱う。

    2話以上ある作品は話数だけで連載確定するため、この判定は不要。
    """
    if len(issue_dirs) != 1:
        return False

    issue = collect_issue_pages(issue_dirs[0])
    return bool(issue.color and issue.main)


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
    block_start = len(result)

    if issue.color:
        print("  layout: COLOR")

        for path in issue.color:
            result.append(open_rgb(path))

        if issue.main:
            result.append(
                create_blank_image(issue.main[0])
            )

            for path in issue.main:
                result.append(open_rgb(path))

    elif issue.main:
        print("  layout: NORMAL")
        result.append(
            create_blank_image(issue.main[0])
        )

        for path in issue.main:
            result.append(open_rgb(path))

    else:
        return

    block_page_count = len(result) - block_start

    if block_page_count % 2 != 0:
        reference = None

        if issue.main:
            reference = issue.main[-1]
        elif issue.color:
            reference = issue.color[-1]

        if reference is not None:
            result.append(
                create_blank_image(reference)
            )
            block_page_count += 1
            print("  trailing blank added")

    print(f"  block pages: {block_page_count}")


def set_right_to_left(
    pdf_file: Path,
) -> None:
    reader = PdfReader(str(pdf_file))
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

    temp_file = pdf_file.with_suffix(".tmp.pdf")

    with temp_file.open("wb") as file:
        writer.write(file)

    temp_file.replace(pdf_file)


def build_pdf(
    images: list[Image.Image],
    output_file: Path,
) -> None:
    if not images:
        raise ValueError("PDF化する画像がありません。")

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

    set_right_to_left(output_file)


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

    issue_dirs.sort(key=lambda path: path.name)

    work_title = work_dir.name
    serial_signal = first_issue_has_serial_signal(
        issue_dirs
    )
    history = update_work_history(
        output_root=output_root,
        work_title=work_title,
        current_issues=[
            path.name
            for path in issue_dirs
        ],
        serial_signal=serial_signal,
    )
    category = classify_work_category(
        history.cumulative_issue_count,
        serial_confirmed=history.serial_confirmed,
    )
    is_oneshot = category == ONESHOT_CATEGORY

    print(
        f"{work_title}: 累計 {history.cumulative_issue_count} 話 / "
        f"{category} / reason={history.serial_reason or 'single_issue'}"
    )

    cleanup_previous_category(
        output_root=output_root,
        work_title=work_title,
        current_category=category,
    )

    output_dir = output_root / category / work_title
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
            issue = collect_issue_pages(issue_dir)

            print()
            print(f"{work_title} / {issue_dir.name}")
            print(f"  color: {len(issue.color)}")
            print(f"  main: {len(issue.main)}")

            append_issue_to_pdf_images(
                pdf_images,
                issue,
            )

        if not pdf_images:
            continue

        first_number = start + 1
        last_number = start + len(group)
        last_issue = group[-1].name

        output_file = (
            output_dir
            / build_pdf_filename(
                work_title=work_title,
                first_number=first_number,
                last_number=last_number,
                last_issue=last_issue,
                is_oneshot=is_oneshot,
            )
        )

        prepend_blank_cover(pdf_images)

        print()
        print(f"PDF作成: {output_file}")
        print(f"PDFページ数: {len(pdf_images)}")

        build_pdf(
            pdf_images,
            output_file,
        )
        created.append(output_file)

    return created
