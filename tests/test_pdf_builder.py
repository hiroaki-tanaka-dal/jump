import tempfile
import unittest
from pathlib import Path

from jump_pdf.pdf.builder import (
    ONESHOT_CATEGORY,
    SERIAL_CATEGORY,
    build_pdf_filename,
    classify_work_category,
    cleanup_previous_category,
)


class PdfBuilderNamingTest(unittest.TestCase):
    def test_single_issue_is_oneshot(self):
        self.assertEqual(
            classify_work_category(1),
            ONESHOT_CATEGORY,
        )

    def test_multiple_issues_are_serial(self):
        self.assertEqual(
            classify_work_category(2),
            SERIAL_CATEGORY,
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


if __name__ == "__main__":
    unittest.main()
