import argparse
from pathlib import Path

from jump_pdf.panels.sync import MANIFEST_FILE, sync_pdfs
from jump_pdf.panels.usb import PANELS_APP_ID, USB_MANIFEST_FILE, sync_pdfs_usb


DEFAULT_PDF_ROOT = Path("data/pdf")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "生成済みの連載作品PDFをPanelsへ安全に差分同期します。"
        )
    )
    parser.add_argument(
        "panels_root",
        nargs="?",
        type=Path,
        help="ローカル同期時のPanels参照フォルダ。--usb時は不要。",
    )
    parser.add_argument(
        "--usb",
        action="store_true",
        help="USB接続中のiPad上のPanels Documentsへafcclientで同期する。",
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
        help="実際に追加・置換・管理済み旧PDFの削除を行う。省略時はdry-run。",
    )
    parser.add_argument(
        "--delete-orphans",
        action="store_true",
        help=(
            "ローカル同期専用。管理外も含めPanels側にしかないPDFを削除する強制モード。"
            "通常は指定しないことを推奨。"
        ),
    )
    args = parser.parse_args()

    if args.usb and args.panels_root is not None:
        parser.error("--usb 使用時は panels_root を指定しません。")
    if not args.usb and args.panels_root is None:
        parser.error("ローカル同期では panels_root が必要です。USB同期は --usb を指定してください。")
    if args.usb and args.delete_orphans:
        parser.error("--delete-orphans は --usb では使用できません。")

    return args


def main() -> None:
    args = parse_args()

    print("=" * 80)
    print("Panels PDF Sync")
    print("=" * 80)
    print(f"source: {args.source}")
    print(f"mode: {'APPLY' if args.apply else 'DRY RUN'}")

    if args.usb:
        print("transport: USB / afcclient")
        print(f"Panels app: {PANELS_APP_ID}")
        print(f"manifest: {args.source / '_state' / USB_MANIFEST_FILE}")
        print()
        plan = sync_pdfs_usb(
            source_root=args.source,
            dry_run=not args.apply,
        )
    else:
        print("transport: local filesystem")
        print(f"panels: {args.panels_root}")
        print(f"manifest: {args.panels_root / MANIFEST_FILE}")
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
    elif args.apply:
        if args.usb:
            print(
                f"USB同期完了。管理情報を {USB_MANIFEST_FILE} に保存しました。"
            )
        else:
            print(
                f"同期完了。管理情報を {MANIFEST_FILE} に保存しました。"
            )


if __name__ == "__main__":
    main()
