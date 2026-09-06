"""最新号取得からPDF生成・Panels USB同期までを一括実行する。"""

import argparse
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

from jump_pdf.pdf.builder import build_work_pdfs
from jump_pdf.panels.usb import sync_pdfs_usb
from jump_pdf.sync import sync_magazines


AUTH_FILE = Path("auth.json")
WORKS_ROOT = Path("data/works")
PDF_ROOT = Path("data/pdf")
ISSUES_PER_PDF = 10
VIEWPORT_WIDTH = 1720
VIEWPORT_HEIGHT = 1000


def iter_work_dirs(works_root: Path) -> list[Path]:
    if not works_root.exists():
        raise RuntimeError(f"作品ルートがありません: {works_root}")

    return sorted(
        (
            path
            for path in works_root.iterdir()
            if path.is_dir() and not path.name.startswith("_")
        ),
        key=lambda path: path.name,
    )


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="最新のジャンプ更新からPanels USB同期までを一括実行します。"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="取得・Panels転送を書き込まず、確認用に実行します。",
    )
    parser.add_argument(
        "--skip-download",
        action="store_true",
        help="本棚更新・未処理号取得をスキップします。",
    )
    parser.add_argument(
        "--skip-pdf",
        action="store_true",
        help="PDF生成をスキップします。",
    )
    parser.add_argument(
        "--skip-panels",
        action="store_true",
        help="Panels USB同期をスキップします。",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="今回取得する未処理号数の上限。省略時は全未処理号。",
    )
    return parser.parse_args()


def download_pending_magazines(*, limit: int | None, dry_run: bool) -> None:
    if not AUTH_FILE.exists():
        raise RuntimeError(
            f"認証ファイルがありません: {AUTH_FILE}。先にログイン処理を実行してください。"
        )

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=False)
        try:
            context = browser.new_context(
                storage_state=str(AUTH_FILE),
                viewport={
                    "width": VIEWPORT_WIDTH,
                    "height": VIEWPORT_HEIGHT,
                },
                device_scale_factor=2.56,
            )
            page = context.new_page()
            sync_magazines(
                page,
                limit=limit,
                dry_run=dry_run,
                newest_first=True,
            )
        finally:
            browser.close()


def build_all_pdfs() -> None:
    work_dirs = iter_work_dirs(WORKS_ROOT)
    failed: list[tuple[str, Exception]] = []

    print()
    print("=" * 80)
    print("PDF更新")
    print("=" * 80)
    print(f"対象作品数: {len(work_dirs)}")

    for index, work_dir in enumerate(work_dirs, start=1):
        print(f"[{index}/{len(work_dirs)}] {work_dir.name}")
        try:
            build_work_pdfs(
                work_dir=work_dir,
                output_root=PDF_ROOT,
                issues_per_pdf=ISSUES_PER_PDF,
            )
        except Exception as exc:
            failed.append((work_dir.name, exc))
            print(f"ERROR: {work_dir.name}: {exc}")

    if failed:
        details = "\n".join(
            f"  {work_title}: {error}"
            for work_title, error in failed
        )
        raise RuntimeError(f"PDF生成に失敗した作品があります:\n{details}")


def sync_panels(*, dry_run: bool) -> None:
    if shutil.which("afcclient") is None:
        raise RuntimeError(
            "afcclient が見つかりません。libimobiledevice を確認してください。"
        )

    print()
    print("=" * 80)
    print("Panels USB同期")
    print("=" * 80)

    sync_pdfs_usb(
        source_root=PDF_ROOT,
        dry_run=dry_run,
    )

    if not dry_run:
        print()
        print("PanelsへのUSB転送が完了しました。")
        print("iPadのPanelsでライブラリのスキャンを実行してください。")


def main() -> None:
    args = parse_args()

    print("=" * 80)
    print("JUMP UPDATE")
    print("=" * 80)
    print(f"mode: {'DRY RUN' if args.dry_run else 'APPLY'}")

    if not args.skip_download:
        download_pending_magazines(
            limit=args.limit,
            dry_run=args.dry_run,
        )
    else:
        print("本棚更新・未処理号取得: SKIP")

    # dry-run時は取得結果を書き込まないため、既存データをPDF化しても
    # 一括処理の確認になりにくい。PDF/USBも変更せず終了する。
    if args.dry_run:
        print()
        print("DRY RUN完了。PDF生成・Panels転送は実行していません。")
        return

    if not args.skip_pdf:
        build_all_pdfs()
    else:
        print("PDF生成: SKIP")

    if not args.skip_panels:
        sync_panels(dry_run=False)
    else:
        print("Panels USB同期: SKIP")

    print()
    print("=" * 80)
    print("JUMP UPDATE 完了")
    print("=" * 80)


if __name__ == "__main__":
    main()
