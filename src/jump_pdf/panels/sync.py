import hashlib
import json
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


PANEL_SYNC_CATEGORIES = (
    "連載作品",
)
MANIFEST_FILE = ".jump_pdf_sync.json"
MANIFEST_VERSION = 1


class SyncAction(str, Enum):
    ADD = "add"
    REPLACE = "replace"
    DELETE = "delete"
    UNCHANGED = "unchanged"


@dataclass(frozen=True)
class SyncItem:
    action: SyncAction
    relative_path: Path
    source: Path | None
    destination: Path


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(
            lambda: file.read(1024 * 1024),
            b"",
        ):
            digest.update(chunk)

    return digest.hexdigest()


def collect_pdfs(root: Path) -> dict[Path, Path]:
    if not root.exists():
        return {}

    return {
        path.relative_to(root): path
        for path in root.rglob("*.pdf")
        if path.is_file()
    }


def collect_source_pdfs(source_root: Path) -> dict[Path, Path]:
    """
    Panelsへ連携するカテゴリだけを収集する。

    読み切りはローカル保存のみとし、Panelsへは同期しない。
    現時点では「連載作品」だけをPanels同期対象とする。
    """
    result: dict[Path, Path] = {}

    for category in PANEL_SYNC_CATEGORIES:
        category_root = source_root / category

        for relative_path, path in collect_pdfs(category_root).items():
            result[Path(category) / relative_path] = path

    return result


def manifest_path(panels_root: Path) -> Path:
    return panels_root / MANIFEST_FILE


def load_manifest(panels_root: Path) -> dict:
    path = manifest_path(panels_root)

    if not path.exists():
        return {
            "version": MANIFEST_VERSION,
            "files": {},
        }

    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, dict):
        raise ValueError(
            f"Panels同期マニフェストの形式が不正です: {path}"
        )

    files = data.get("files", {})
    if not isinstance(files, dict):
        raise ValueError(
            f"Panels同期マニフェストのfilesが不正です: {path}"
        )

    return {
        "version": int(data.get("version", MANIFEST_VERSION)),
        "files": files,
    }


def save_manifest(
    panels_root: Path,
    source_files: dict[Path, Path],
) -> None:
    panels_root.mkdir(parents=True, exist_ok=True)
    path = manifest_path(panels_root)
    temp = path.with_suffix(".tmp")

    data = {
        "version": MANIFEST_VERSION,
        "files": {
            relative_path.as_posix(): {
                "sha256": file_sha256(source),
            }
            for relative_path, source in sorted(
                source_files.items(),
                key=lambda item: item[0].as_posix(),
            )
        },
    }

    with temp.open("w", encoding="utf-8") as file:
        json.dump(
            data,
            file,
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        file.write("\n")

    temp.replace(path)


def managed_paths_from_manifest(
    panels_root: Path,
) -> set[Path]:
    manifest = load_manifest(panels_root)
    return {
        Path(value)
        for value in manifest["files"]
    }


def build_sync_plan(
    source_root: Path,
    panels_root: Path,
    *,
    delete_orphans: bool = False,
) -> list[SyncItem]:
    """
    data/pdf と Panels 側のPDFを比較して同期計画を返す。

    通常の削除対象は、前回マニフェストでこのアプリが管理していたが
    現在の同期元には存在しないPDFだけ。これによりPanelsへ手動で
    追加したファイルは削除しない。

    delete_orphans=True は互換用の強制モードで、Panels側だけにある
    PDFも削除対象にするため、通常利用では指定しない。
    """
    source_root = source_root.expanduser().resolve()
    panels_root = panels_root.expanduser().resolve()

    if not source_root.exists():
        raise FileNotFoundError(
            f"PDF出力フォルダがありません: {source_root}"
        )

    source_files = collect_source_pdfs(source_root)
    panels_files = collect_pdfs(panels_root)
    managed_paths = managed_paths_from_manifest(panels_root)

    plan: list[SyncItem] = []

    for relative_path in sorted(source_files):
        source = source_files[relative_path]
        destination = panels_root / relative_path
        current = panels_files.get(relative_path)

        if current is None:
            action = SyncAction.ADD
        elif file_sha256(source) != file_sha256(current):
            action = SyncAction.REPLACE
        else:
            action = SyncAction.UNCHANGED

        plan.append(
            SyncItem(
                action=action,
                relative_path=relative_path,
                source=source,
                destination=destination,
            )
        )

    stale_managed = managed_paths - set(source_files)

    for relative_path in sorted(stale_managed):
        destination = panels_root / relative_path

        if destination.exists() and destination.is_file():
            plan.append(
                SyncItem(
                    action=SyncAction.DELETE,
                    relative_path=relative_path,
                    source=None,
                    destination=destination,
                )
            )

    if delete_orphans:
        already_deleted = {
            item.relative_path
            for item in plan
            if item.action == SyncAction.DELETE
        }

        for relative_path in sorted(
            set(panels_files)
            - set(source_files)
            - already_deleted
        ):
            plan.append(
                SyncItem(
                    action=SyncAction.DELETE,
                    relative_path=relative_path,
                    source=None,
                    destination=panels_files[relative_path],
                )
            )

    return plan


def print_sync_plan(plan: list[SyncItem]) -> None:
    changed = 0

    for item in plan:
        if item.action == SyncAction.UNCHANGED:
            continue

        changed += 1
        print(
            f"[{item.action.value.upper():7}] "
            f"{item.relative_path}"
        )

    if changed == 0:
        print("同期が必要なPDFはありません。")


def remove_empty_parent_dirs(
    path: Path,
    stop_at: Path,
) -> None:
    current = path.parent
    stop_at = stop_at.resolve()

    while current.resolve() != stop_at:
        try:
            current.rmdir()
        except OSError:
            break
        current = current.parent


def sync_pdfs(
    source_root: Path,
    panels_root: Path,
    *,
    dry_run: bool = True,
    delete_orphans: bool = False,
) -> list[SyncItem]:
    """
    PDF出力フォルダをPanelsフォルダへ同期する。

    dry_run=True がデフォルト。まず差分だけ表示して、
    明示的に dry_run=False を指定した場合だけ書き換える。

    apply成功後にマニフェストを更新し、次回以降はこのアプリが
    管理したPDFだけを安全に削除できるようにする。
    """
    source_root = source_root.expanduser().resolve()
    panels_root = panels_root.expanduser().resolve()

    plan = build_sync_plan(
        source_root=source_root,
        panels_root=panels_root,
        delete_orphans=delete_orphans,
    )

    print_sync_plan(plan)

    if dry_run:
        return plan

    panels_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    for item in plan:
        if item.action == SyncAction.UNCHANGED:
            continue

        if item.action == SyncAction.DELETE:
            item.destination.unlink(missing_ok=True)
            remove_empty_parent_dirs(
                item.destination,
                panels_root,
            )
            continue

        if item.source is None:
            continue

        item.destination.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            item.source,
            item.destination,
        )

    source_files = collect_source_pdfs(source_root)
    save_manifest(
        panels_root=panels_root,
        source_files=source_files,
    )

    return plan
