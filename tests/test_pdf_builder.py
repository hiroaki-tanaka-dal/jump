import tempfile
import unittest
from pathlib import Path

from jump_pdf.pdf.builder import (
    ONESHOT_CATEGORY,
    SERIAL_CATEGORY,
    build_pdf_filename,
    classify_work_category,
    cleanup_previous_category,
    cleanup_stale_generated_pdfs,
    first_issue_has_serial_signal,
)


class PdfBuilderNamingTest(unittest.TestCase):
    def test_single_issue_is_oneshot(self):
        self.assertEqual(
            classify_work_category(1),
            ONESHOT_CATEGORY,
        )

    def test_single_issue_can_be_confirmed_serial(self):
        self.assertEqual(
            classify_work_category(
                1,
                serial_confirmed=True,
            ),
            SERIAL_CATEGORY,
        )

    def test_multiple_issues_are_serial(self):
        self.assertEqual(
            classify_work_category(2),
            SERIAL_CATEGORY,
        )

    def test_first_issue_color_and_main_is_serial_signal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            issue_dir = Path(temp_dir) / "2026-39"
            color_dir = issue_dir / "color"
            main_dir = issue_dir / "main"
            color_dir.mkdir(parents=True)
            main_dir.mkdir(parents=True)
            (color_dir / "001.png").write_bytes(b"png")
            (main_dir / "001.png").write_bytes(b"png")

            self.assertTrue(
                first_issue_has_serial_signal([issue_dir])
            )

    def test_first_issue_without_color_is_not_serial_signal(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            issue_dir = Path(temp_dir) / "2026-39"
            main_dir = issue_dir / "main"
            main_dir.mkdir(parents=True)
            (main_dir / "001.png").write_bytes(b"png")

            self.assertFalse(
                first_issue_has_serial_signal([issue_dir])
            )

    def test_oneshot_filename(self):
        self.assertEqual(
            build_pdf_filename(
                work_title="テスト作品",
                first_number=1,
                last_number=1,
                last_issue="2026-37_38",
                is_oneshot=True,
            ),
            "テスト作品_001-001.pdf",
        )

    def test_serial_filename_contains_last_issue(self):
        self.assertEqual(
            build_pdf_filename(
                work_title="テスト作品",
                first_number=1,
                last_number=10,
                last_issue="2026-37_38",
                is_oneshot=False,
            ),
            "テスト作品_001-010_2026-37_38.pdf",
        )

    def test_cleanup_removes_old_oneshot_folder_after_promotion(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            old_dir = (
                output_root
                / ONESHOT_CATEGORY
                / "テスト作品"
            )
            old_dir.mkdir(parents=True)
            (old_dir / "テスト作品_001-001.pdf").write_bytes(b"pdf")

            cleanup_previous_category(
                output_root=output_root,
                work_title="テスト作品",
                current_category=SERIAL_CATEGORY,
            )

            self.assertFalse(old_dir.exists())

    def test_cleanup_removes_legacy_ongoing_folder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            old_dir = (
                output_root
                / "連載中"
                / "テスト作品"
            )
            old_dir.mkdir(parents=True)
            (old_dir / "old.pdf").write_bytes(b"pdf")

            cleanup_previous_category(
                output_root=output_root,
                work_title="テスト作品",
                current_category=SERIAL_CATEGORY,
            )

            self.assertFalse(old_dir.exists())

    def test_cleanup_stale_generated_pdf_keeps_expected_and_unrelated_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_dir = Path(temp_dir) / "連載作品" / "テスト作品"
            output_dir.mkdir(parents=True)

            expected = output_dir / "テスト作品_011-012_2026-39.pdf"
            stale = output_dir / "テスト作品_011-011_2026-37_38.pdf"
            unrelated = output_dir / "手動保存.pdf"
            expected.write_bytes(b"new")
            stale.write_bytes(b"old")
            unrelated.write_bytes(b"manual")

            removed = cleanup_stale_generated_pdfs(
                output_dir=output_dir,
                work_title="テスト作品",
                expected_files=[expected],
            )

            self.assertEqual(removed, [stale])
            self.assertTrue(expected.exists())
            self.assertFalse(stale.exists())
            self.assertTrue(unrelated.exists())


if __name__ == "__main__":
    unittest.main()
