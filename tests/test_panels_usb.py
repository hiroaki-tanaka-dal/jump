import tempfile
import unittest
from pathlib import Path

from jump_pdf.panels.sync import SyncAction
from jump_pdf.panels.usb import (
    build_usb_sync_plan,
    save_usb_manifest,
)


class PanelsUsbSyncTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.root = Path(self.temp_dir.name) / "pdf"
        self.work_dir = self.root / "連載作品" / "テスト作品"
        self.work_dir.mkdir(parents=True)

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def write_pdf(self, name: str, content: bytes) -> Path:
        path = self.work_dir / name
        path.write_bytes(content)
        return path

    def test_first_sync_is_add(self) -> None:
        self.write_pdf("テスト作品_001-010.pdf", b"pdf-a")

        plan = build_usb_sync_plan(self.root)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].action, SyncAction.ADD)

    def test_unchanged_after_manifest(self) -> None:
        pdf = self.write_pdf("テスト作品_001-010.pdf", b"pdf-a")
        save_usb_manifest(
            self.root,
            {Path("連載作品/テスト作品/テスト作品_001-010.pdf"): pdf},
        )

        plan = build_usb_sync_plan(self.root)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].action, SyncAction.UNCHANGED)

    def test_same_path_changed_is_replace(self) -> None:
        pdf = self.write_pdf("テスト作品_001-010.pdf", b"pdf-a")
        save_usb_manifest(
            self.root,
            {Path("連載作品/テスト作品/テスト作品_001-010.pdf"): pdf},
        )
        pdf.write_bytes(b"pdf-b")

        plan = build_usb_sync_plan(self.root)

        self.assertEqual(len(plan), 1)
        self.assertEqual(plan[0].action, SyncAction.REPLACE)

    def test_partial_tail_rename_becomes_add_and_delete(self) -> None:
        old_pdf = self.write_pdf("テスト作品_011-011.pdf", b"old")
        old_relative = Path("連載作品/テスト作品/テスト作品_011-011.pdf")
        save_usb_manifest(self.root, {old_relative: old_pdf})
        old_pdf.unlink()
        self.write_pdf("テスト作品_011-012.pdf", b"new")

        plan = build_usb_sync_plan(self.root)
        actions = {item.relative_path: item.action for item in plan}

        self.assertEqual(
            actions[Path("連載作品/テスト作品/テスト作品_011-011.pdf")],
            SyncAction.DELETE,
        )
        self.assertEqual(
            actions[Path("連載作品/テスト作品/テスト作品_011-012.pdf")],
            SyncAction.ADD,
        )


if __name__ == "__main__":
    unittest.main()
