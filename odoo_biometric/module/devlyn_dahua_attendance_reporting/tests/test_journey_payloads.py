from __future__ import annotations

import importlib.util
import sys
import unittest
from datetime import datetime
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "services" / "report_utils.py"
SPEC = importlib.util.spec_from_file_location("devlyn_report_utils", MODULE_PATH)
REPORT_UTILS = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = REPORT_UTILS
SPEC.loader.exec_module(REPORT_UTILS)


class JourneyPayloadsCase(unittest.TestCase):
    def _segment(self, attendance_id, check_in_text, check_out_text, worked_minutes, *, auto_closed=False):
        fmt = "%Y-%m-%d %H:%M:%S"
        return REPORT_UTILS.SegmentSnapshot(
            attendance_id=attendance_id,
            check_in_local=datetime.strptime(check_in_text, fmt),
            check_out_local=datetime.strptime(check_out_text, fmt) if check_out_text else None,
            worked_minutes=worked_minutes,
            auto_closed=auto_closed,
            center_code="A753",
            branch_id=10,
        )

    def test_single_segment_summary(self):
        payloads, summary = REPORT_UTILS.build_segment_payloads(
            [self._segment(1, "2026-04-21 09:00:00", "2026-04-21 18:00:00", 540)]
        )
        self.assertEqual(len(payloads), 1)
        self.assertEqual(summary["segment_count"], 1)
        self.assertEqual(summary["intermittence_count"], 0)
        self.assertEqual(summary["total_gap_minutes"], 0)
        self.assertEqual(summary["day_state"], "closed")

    def test_multi_segment_summary(self):
        payloads, summary = REPORT_UTILS.build_segment_payloads(
            [
                self._segment(1, "2026-04-21 09:00:00", "2026-04-21 14:00:00", 300),
                self._segment(2, "2026-04-21 15:00:00", "2026-04-21 19:00:00", 240),
                self._segment(3, "2026-04-21 20:00:00", "2026-04-21 23:59:59", 240, auto_closed=True),
            ]
        )
        self.assertEqual(len(payloads), 3)
        self.assertEqual(summary["segment_count"], 3)
        self.assertEqual(summary["intermittence_count"], 2)
        self.assertEqual(summary["total_gap_minutes"], 120)
        self.assertEqual(summary["day_state"], "closed_auto")
        self.assertEqual(payloads[1]["gap_before_minutes"], 60)
        self.assertEqual(payloads[2]["gap_before_minutes"], 60)

    def test_open_segment_takes_open_day_state(self):
        payloads, summary = REPORT_UTILS.build_segment_payloads(
            [
                self._segment(1, "2026-04-21 09:00:00", "2026-04-21 14:00:00", 300),
                self._segment(2, "2026-04-21 15:30:00", None, 0),
            ]
        )
        self.assertEqual(summary["segment_count"], 2)
        self.assertEqual(summary["intermittence_count"], 1)
        self.assertEqual(summary["total_gap_minutes"], 90)
        self.assertEqual(summary["day_state"], "open")
        self.assertEqual(payloads[1]["segment_state"], "open")


if __name__ == "__main__":
    unittest.main()
