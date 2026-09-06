import unittest

from jump_pdf.pdf.builder import (
    ONESHOT_CATEGORY,
    ONGOING_CATEGORY,
    build_pdf_filename,
    classify_work_category,
)


class PdfBuilderNamingTest(unittest.TestCase):
    def test_single_issue_is_oneshot(self):
        self.assertEqual(
            classify_work_category(1),
            ONESHOT_CATEGORY,
        )

    def test_multiple_issues_are_ongoing(self):
        self.assertEqual(
            classify_work_category(2),
            ONGOING_CATEGORY,
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


if __name__ == "__main__":
    unittest.main()
