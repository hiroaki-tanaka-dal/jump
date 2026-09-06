import argparse
from pathlib import Path

from jump_pdf.pdf.builder import build_work_pdfs


WORKS_ROOT = Path("data/works")
PDF_ROOT = Path("data/pdf")
ISSUES_PER_PDF = 10


def iter_work_dirs(works_root: Path) -> list[Path]:
    """PDF化対象の作品フォルダを列挙する。"""
    if not works_root.exists():
        raise RuntimeError(
            f"作品ルートがありません: {works_root}"
        )

    return sorted(
        [
            path
            for path in works_root.iterdir()
            if path.is_dir()
            and not path.name.startswith("_")
        ],
        key=lambda path: path.name,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="data/works 配下の作品をPDF化します。"
    )
    parser.add_argument(
        "--work",
        help="指定した作品だけPDF化します。省略時は全作品を対象にします。",
    )
    parser.add_argument(
        "--works-root",
        type=Path,
        default=WORKS_ROOT,
        help=f"作品ルート。既定値: {WORKS_ROOT}",
    )
    parser.add_argument(
        "--output-root",
        type=Path,
        default=PDF_ROOT,
        help=f"PDF出力ルート。既定値: {PDF_ROOT}",
    )
    parser.add_argument(
        "--issues-per-pdf",
        type=int,
        default=ISSUES_PER_PDF,
        help=f"1PDFあたりの話数。既定値: {ISSUES_PER_PDF}",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    if args.issues_per_pdf <= 0:
        raise ValueError(
            "--issues-per-pdf は1以上を指定してください。"
        )

    if args.work:
        work_dirs = [args.works_root / args.work]

        if not work_dirs[0].exists():
            raise RuntimeError(
                f"作品フォルダがありません: {work_dirs[0]}"
            )
    else:
        work_dirs = iter_work_dirs(args.works_root)

    if not work_dirs:
        print(
            f"PDF化対象の作品がありません: {args.works_root}"
        )
        return

    print("=" * 80)
    print(f"対象作品数: {len(work_dirs)}")
    print(f"作品ルート: {args.works_root}")
    print(f"PDF出力先: {args.output_root}")
    print(f"1PDFあたり: {args.issues_per_pdf} 話")
    print("=" * 80)

    created_files: list[Path] = []
    failed: list[tuple[str, Exception]] = []

    for index, work_dir in enumerate(work_dirs, start=1):
        print()
        print("#" * 80)
        print(
            f"[{index}/{len(work_dirs)}] {work_dir.name}"
        )
        print("#" * 80)

        try:
            files = build_work_pdfs(
                work_dir=work_dir,
                output_root=args.output_root,
                issues_per_pdf=args.issues_per_pdf,
            )
            created_files.extend(files)
        except Exception as exc:
            failed.append((work_dir.name, exc))
            print(
                f"ERROR: {work_dir.name}: {exc}"
            )

    print()
    print("=" * 80)
    print("PDF作成結果")
    print("=" * 80)
    print(f"対象作品数: {len(work_dirs)}")
    print(f"作成PDF数: {len(created_files)}")
    print(f"失敗作品数: {len(failed)}")

    if created_files:
        print()
        print("作成ファイル:")
        for file in created_files:
            print(f"  {file}")

    if failed:
        print()
        print("失敗作品:")
        for work_title, error in failed:
            print(f"  {work_title}: {error}")

        raise SystemExit(1)


if __name__ == "__main__":
    main()
