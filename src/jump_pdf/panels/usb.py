import json
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from jump_pdf.panels.sync import (
    MANIFEST_VERSION,
    SyncAction,
    collect_source_pdfs,
    file_sha256,
)


PANELS_APP_ID = "es.produkt.app.panels"
PANELS_DOCUMENTS_ROOT = PurePosixPath("/Documents")
USB_MANIFEST_FILE = "panels_usb.json"


@dataclass(frozen=True)
class UsbSyncItem:
    action: SyncAction
    relative_path: Path
    source: Path | None
    remote_path: PurePosixPath


def usb_manifest_path(source_root: Path) -> Path:
    return source_root / "_state" / USB_MANIFEST_FILE


def load_usb_manifest(source_root: Path) -> dict:
    path = usb_manifest_path(source_root)
    if not path.exists():
        return {"version": MANIFEST_VERSION, "files": {}}

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    files = data.get("files", {})
    if not isinstance(files, dict):
        raise ValueError(f"USB同期マニフェストの形式が不正です: {path}")

    return {
        "version": int(data.get("version", MANIFEST_VERSION)),
        "files": files,
    }


def save_usb_manifest(source_root: Path, source_files: dict[Path, Path]) -> None:
    path = usb_manifest_path(source_root)
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix(".tmp")

    data = {
        "version": MANIFEST_VERSION,
        "files": {
            relative_path.as_posix(): {"sha256": file_sha256(source)}
            for relative_path, source in sorted(
                source_files.items(), key=lambda item: item[0].as_posix()
            )
        },
    }

    with temp.open("w", encoding="utf-8") as file:
        json.dump(data, file, ensure_ascii=False, indent=2, sort_keys=True)
        file.write("\n")

    temp.replace(path)


def remote_path_for(relative_path: Path) -> PurePosixPath:
    return PANELS_DOCUMENTS_ROOT.joinpath(*relative_path.parts)


def ensure_afcclient() -> None:
    if shutil.which("afcclient") is None:
        raise RuntimeError(
            "afcclient が見つかりません。brew install libimobiledevice を確認してください。"
        )


def run_afc(*args: str, capture_output: bool = False) -> subprocess.CompletedProcess[str]:
    command = [
        "afcclient",
        "--documents",
        PANELS_APP_ID,
        *args,
    ]
    return subprocess.run(
        command,
        check=True,
        text=True,
        capture_output=capture_output,
    )


def check_panels_connection() -> None:
    ensure_afcclient()
    try:
        run_afc("ls", str(PANELS_DOCUMENTS_ROOT), capture_output=True)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or exc.stdout or "").strip()
        raise RuntimeError(
            "USB接続中のPanels Documentsへアクセスできません。"
            " iPadのロック解除・信頼状態・USB接続を確認してください。"
            + (f"\n{detail}" if detail else "")
        ) from exc


def build_usb_sync_plan(source_root: Path) -> list[UsbSyncItem]:
    source_root = source_root.expanduser().resolve()
    if not source_root.exists():
        raise FileNotFoundError(f"PDF出力フォルダがありません: {source_root}")

    source_files = collect_source_pdfs(source_root)
    manifest = load_usb_manifest(source_root)
    previous_files: dict[str, dict] = manifest["files"]

    plan: list[UsbSyncItem] = []

    for relative_path in sorted(source_files):
        source = source_files[relative_path]
        key = relative_path.as_posix()
        previous = previous_files.get(key)
        current_hash = file_sha256(source)

        if previous is None:
            action = SyncAction.ADD
        elif previous.get("sha256") != current_hash:
            action = SyncAction.REPLACE
        else:
            action = SyncAction.UNCHANGED

        plan.append(
            UsbSyncItem(
                action=action,
                relative_path=relative_path,
                source=source,
                remote_path=remote_path_for(relative_path),
            )
        )

    current_keys = {path.as_posix() for path in source_files}
    for key in sorted(set(previous_files) - current_keys):
        relative_path = Path(key)
        plan.append(
            UsbSyncItem(
                action=SyncAction.DELETE,
                relative_path=relative_path,
                source=None,
                remote_path=remote_path_for(relative_path),
            )
        )

    return plan


def print_usb_sync_plan(plan: list[UsbSyncItem]) -> None:
    changed = 0
    for item in plan:
        if item.action == SyncAction.UNCHANGED:
            continue
        changed += 1
        print(f"[{item.action.value.upper():7}] {item.relative_path}")

    if changed == 0:
        print("同期が必要なPDFはありません。")


def mkdir_remote_tree(remote_dir: PurePosixPath) -> None:
    current = PurePosixPath("/")
    for part in remote_dir.parts[1:]:
        current = current / part
        if current == PANELS_DOCUMENTS_ROOT:
            continue
        try:
            run_afc("mkdir", str(current), capture_output=True)
        except subprocess.CalledProcessError as exc:
            # mkdirは既存ディレクトリでも失敗する実装があるため、lsできれば既存扱い。
            try:
                run_afc("ls", str(current), capture_output=True)
            except subprocess.CalledProcessError:
                raise exc


def remove_remote_file(remote_path: PurePosixPath) -> None:
    try:
        run_afc("rm", str(remote_path), capture_output=True)
    except subprocess.CalledProcessError as exc:
        # 既に消えている場合は同期上問題ない。
        message = ((exc.stderr or "") + (exc.stdout or "")).lower()
        if "no such file" not in message and "not found" not in message:
            raise


def sync_pdfs_usb(
    source_root: Path,
    *,
    dry_run: bool = True,
) -> list[UsbSyncItem]:
    source_root = source_root.expanduser().resolve()
    plan = build_usb_sync_plan(source_root)
    print_usb_sync_plan(plan)

    if dry_run:
        return plan

    check_panels_connection()

    for item in plan:
        if item.action == SyncAction.UNCHANGED:
            continue

        if item.action in (SyncAction.DELETE, SyncAction.REPLACE):
            remove_remote_file(item.remote_path)

        if item.action in (SyncAction.ADD, SyncAction.REPLACE):
            if item.source is None:
                continue
            mkdir_remote_tree(item.remote_path.parent)
            print(f"転送: {item.relative_path}")
            run_afc("put", str(item.source.resolve()), str(item.remote_path))

    source_files = collect_source_pdfs(source_root)
    save_usb_manifest(source_root, source_files)
    return plan
