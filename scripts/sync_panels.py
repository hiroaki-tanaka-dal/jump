import argparse
from pathlib import Path

from jump_pdf.panels.sync import sync_pdfs


DEFAULT_PDF_ROOT = Path("data/pdf")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "生成済みPDFをPanelsのフォルダへ差分同期します。"
        )
    )
    parser.add_argument(
        "panels_root",
        type=Path,
        help="Panelsから参照しているPDFフォルダ",
    )
    parser.add_argument(
        "--source",
        type=Path,
        default=DEFAULT_PDF_ROOT,
        help="生成済みPDFのルート (default: data/pdf)",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="実際に追加・置換を行う。省略時はdry-run。",
    )
    parser.add_argument(
        "--delete-orphans",
        action="store_true",
        help=(
            "Panels側にしかないPDFも削除する。"
            "通常は指定しないことを推奨。"
        ),
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()

    print("=" * 80)
    print("Panels PDF Sync")
    print("=" * 80)
    print(f"source: {args.source}")
    print(f"panels: {args.panels_root}")
    print(f"mode: {'APPLY' if args.apply else 'DRY RUN'}")
    print()

    plan = sync_pdfs(
        source_root=args.source,
        panels_root=args.panels_root,
        dry_run=not args.apply,
        delete_orphans=args.delete_orphans,
    )

    changed = sum(
        item.action.value != "unchanged"
        for item in plan
    )

    print()
    print(f"差分: {changed}件")

    if not args.apply and changed:
        print(
            "内容を確認後、同じコマンドに --apply を付けると同期します。"
        )


if __name__ == "__main__":
    main()
