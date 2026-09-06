import json
import tempfile
import unittest
from pathlib import Path

from jump_pdf.panels.sync import (
    MANIFEST_FILE,
    SyncAction,
    build_sync_plan,
    sync_pdfs,
)


class PanelsSyncTest(unittest.TestCase):
    def _write_pdf(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    def test_only_serial_category_is_synced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            panels = root / "panels"

            serial = source / "連載作品" / "作品A" / "作品A_001-001_2026-39.pdf"
            oneshot = source / "読み切り" / "作品B" / "作品B_001-001.pdf"
            self._write_pdf(serial, b"serial")
            self._write_pdf(oneshot, b"oneshot")

            plan = build_sync_plan(source, panels)
            paths = {item.relative_path for item in plan}

            self.assertIn(
                Path("連載作品/作品A/作品A_001-001_2026-39.pdf"),
                paths,
            )
            self.assertNotIn(
                Path("読み切り/作品B/作品B_001-001.pdf"),
                paths,
            )

    def test_dry_run_does_not_write_files_or_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            panels = root / "panels"
            pdf = source / "連載作品" / "作品A" / "作品A_001-001_2026-39.pdf"
            self._write_pdf(pdf, b"pdf")

            sync_pdfs(source, panels, dry_run=True)

            self.assertFalse(panels.exists())
            self.assertFalse((panels / MANIFEST_FILE).exists())

    def test_apply_copies_pdf_and_writes_manifest(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            panels = root / "panels"
            relative = Path("連載作品/作品A/作品A_001-001_2026-39.pdf")
            self._write_pdf(source / relative, b"pdf")

            plan = sync_pdfs(source, panels, dry_run=False)

            self.assertEqual(plan[0].action, SyncAction.ADD)
            self.assertEqual((panels / relative).read_bytes(), b"pdf")
            manifest = json.loads(
                (panels / MANIFEST_FILE).read_text(encoding="utf-8")
            )
            self.assertIn(relative.as_posix(), manifest["files"])

    def test_managed_renamed_pdf_is_deleted_and_new_pdf_added(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            panels = root / "panels"
            old_relative = Path(
                "連載作品/作品A/作品A_011-011_2026-37_38.pdf"
            )
            new_relative = Path(
                "連載作品/作品A/作品A_011-012_2026-39.pdf"
            )

            self._write_pdf(source / old_relative, b"old")
            sync_pdfs(source, panels, dry_run=False)

            (source / old_relative).unlink()
            self._write_pdf(source / new_relative, b"new")

            plan = build_sync_plan(source, panels)
            actions = {
                item.relative_path: item.action
                for item in plan
            }

            self.assertEqual(actions[old_relative], SyncAction.DELETE)
            self.assertEqual(actions[new_relative], SyncAction.ADD)

            sync_pdfs(source, panels, dry_run=False)

            self.assertFalse((panels / old_relative).exists())
            self.assertEqual((panels / new_relative).read_bytes(), b"new")

    def test_unmanaged_panels_pdf_is_not_deleted(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            panels = root / "panels"
            source.mkdir(parents=True)
            manual = panels / "手動" / "manual.pdf"
            self._write_pdf(manual, b"manual")

            plan = build_sync_plan(source, panels)

            self.assertFalse(
                any(
                    item.relative_path == Path("手動/manual.pdf")
                    and item.action == SyncAction.DELETE
                    for item in plan
                )
            )

    def test_changed_same_path_is_replaced(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            source = root / "source"
            panels = root / "panels"
            relative = Path("連載作品/作品A/作品A_001-010_2026-36.pdf")
            self._write_pdf(source / relative, b"version1")
            sync_pdfs(source, panels, dry_run=False)

            (source / relative).write_bytes(b"version2")
            plan = build_sync_plan(source, panels)

            action = next(
                item.action
                for item in plan
                if item.relative_path == relative
            )
            self.assertEqual(action, SyncAction.REPLACE)


if __name__ == "__main__":
    unittest.main()
