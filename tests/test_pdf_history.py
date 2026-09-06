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
            self.assertTrue(history.serial_confirmed)

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
            self.assertTrue(second.serial_confirmed)

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
            self.assertTrue(history.serial_confirmed)

    def test_color_signal_confirms_serial_on_first_issue(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)

            history = update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-39"],
                serial_signal=True,
            )

            self.assertEqual(history.cumulative_issue_count, 1)
            self.assertTrue(history.serial_confirmed)
            self.assertEqual(
                history.serial_reason,
                "first_issue_color_and_main",
            )

    def test_second_issue_promotes_oneshot_to_serial(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)

            first = update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-39"],
            )
            second = update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-39", "2026-40"],
            )

            self.assertFalse(first.serial_confirmed)
            self.assertTrue(second.serial_confirmed)
            self.assertEqual(
                second.serial_reason,
                "multiple_issues",
            )

    def test_serial_confirmation_is_not_lost(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            output_root = Path(temp_dir)

            update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-39"],
                serial_signal=True,
            )
            history = update_work_history(
                output_root=output_root,
                work_title="テスト作品",
                current_issues=["2026-39"],
            )

            self.assertTrue(history.serial_confirmed)
            self.assertEqual(
                history.serial_reason,
                "first_issue_color_and_main",
            )


if __name__ == "__main__":
    unittest.main()
