import tempfile
import unittest
from pathlib import Path

from jump_pdf.pdf.history import update_work_history


class PdfHistoryTest(unittest.TestCase):
    def test_existing_aggregate_pdf_prevents_oneshot_reset(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)
            existing_dir = output_root / "連載中" / "テスト作品"
            existing_dir.mkdir(parents=True)
            (
                existing_dir
                / "テスト作品_001-010_2026-36.pdf"
            ).touch()

            history = update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-37_38"],
            )

            self.assertEqual(
                history.cumulative_issue_count,
                11,
            )

    def test_new_issue_is_added_only_once(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)

            first = update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-36", "2026-37_38"],
            )
            second = update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-36", "2026-37_38"],
            )

            self.assertEqual(first.cumulative_issue_count, 2)
            self.assertEqual(second.cumulative_issue_count, 2)

    def test_following_issue_increments_cumulative_count(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)

            update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-36", "2026-37_38"],
            )
            history = update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=[
                    "2026-36",
                    "2026-37_38",
                    "2026-39",
                ],
            )

            self.assertEqual(
                history.cumulative_issue_count,
                3,
            )


if __name__ == "__main__":
    unittest.main()
