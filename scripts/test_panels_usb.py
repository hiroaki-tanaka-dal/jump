from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


APP_ID = "es.produkt.app.panels"
SOURCE_ROOT = Path("data/pdf/連載作品")
REMOTE_TEST_DIR = "/Documents/連載作品/テスト作品"
REMOTE_TEST_FILE = f"{REMOTE_TEST_DIR}/USB転送テスト.pdf"


def run_afc(*args: str) -> None:
    command = [
        "afcclient",
        "--documents",
        APP_ID,
        *args,
    ]
    print("$ " + " ".join(command))
    subprocess.run(command, check=True)


def pick_test_pdf() -> Path:
    if not SOURCE_ROOT.exists():
        raise FileNotFoundError(
            f"連載PDFフォルダが見つかりません: {SOURCE_ROOT}"
        )

    pdfs = sorted(SOURCE_ROOT.rglob("*.pdf"))
    if not pdfs:
        raise FileNotFoundError(
            f"テストに使えるPDFがありません: {SOURCE_ROOT}"
        )

    return pdfs[0]


def main() -> int:
    if shutil.which("afcclient") is None:
        print("afcclient が見つかりません。", file=sys.stderr)
        return 1

    source_pdf = pick_test_pdf()

    print("Panels USB転送テスト")
    print(f"使用PDF: {source_pdf}")
    print(f"転送先: {REMOTE_TEST_FILE}")
    print()

    try:
        # mkdir は既存ディレクトリだと失敗する場合があるため、
        # テスト用ディレクトリ作成だけは個別に許容する。
        try:
            run_afc("mkdir", REMOTE_TEST_DIR)
        except subprocess.CalledProcessError:
            print("テスト用フォルダは既に存在する可能性があります。続行します。")

        print("\n--- PUT ---")
        run_afc(
            "put",
            str(source_pdf.resolve()),
            REMOTE_TEST_FILE,
        )

        print("\n--- LS ---")
        run_afc("ls", REMOTE_TEST_DIR)

        print("\n--- RM ---")
        run_afc("rm", REMOTE_TEST_FILE)

        print("\n--- LS after delete ---")
        run_afc("ls", REMOTE_TEST_DIR)

    except subprocess.CalledProcessError as exc:
        print(
            f"\nUSB転送テストに失敗しました。終了コード: {exc.returncode}",
            file=sys.stderr,
        )
        return exc.returncode or 1

    print("\nPanels USB転送テスト成功: put / ls / rm がすべて通りました。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
