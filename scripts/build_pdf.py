from pathlib import Path

from jump_pdf.pdf.builder import (
    build_work_pdfs,
)


WORKS_ROOT = Path("data/works")
PDF_ROOT = Path("data/pdf")

WORK_TITLE = "カノンマスター"

ISSUES_PER_PDF = 10


def main():
    work_dir = (
        WORKS_ROOT
        / WORK_TITLE
    )

    if not work_dir.exists():
        raise RuntimeError(
            f"作品フォルダがありません: "
            f"{work_dir}"
        )

    files = build_work_pdfs(
        work_dir=work_dir,
        output_root=PDF_ROOT,
        issues_per_pdf=ISSUES_PER_PDF,
    )

    print()
    print("=" * 80)
    print(
        f"PDF作成完了: {len(files)}"
    )

    for file in files:
        print(file)


if __name__ == "__main__":
    main()