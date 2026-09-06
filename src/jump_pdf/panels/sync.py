import hashlib
import shutil
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


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


def build_sync_plan(
    source_root: Path,
    panels_root: Path,
    *,
    delete_orphans: bool = False,
) -> list[SyncItem]:
    """
    data/pdf と Panels 側のPDFを比較して同期計画を返す。

    デフォルトではPanels側にしか存在しないファイルは削除しない。
    delete_orphans=True の場合だけ削除対象にする。
    """

    source_root = source_root.expanduser().resolve()
    panels_root = panels_root.expanduser().resolve()

    if not source_root.exists():
        raise FileNotFoundError(
            f"PDF出力フォルダがありません: {source_root}"
        )

    source_files = collect_pdfs(source_root)
    panels_files = collect_pdfs(panels_root)

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

    if delete_orphans:
        for relative_path in sorted(
            set(panels_files) - set(source_files)
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
    """

    plan = build_sync_plan(
        source_root=source_root,
        panels_root=panels_root,
        delete_orphans=delete_orphans,
    )

    print_sync_plan(plan)

    if dry_run:
        return plan

    panels_root = panels_root.expanduser().resolve()
    panels_root.mkdir(
        parents=True,
        exist_ok=True,
    )

    for item in plan:
        if item.action == SyncAction.UNCHANGED:
            continue

        if item.action == SyncAction.DELETE:
            item.destination.unlink(
                missing_ok=True
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

    return plan
