from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path


MODULE_PATH = Path(__file__).resolve().parents[1] / "services" / "report_utils.py"
SPEC = importlib.util.spec_from_file_location("devlyn_report_utils", MODULE_PATH)
REPORT_UTILS = importlib.util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
sys.modules[SPEC.name] = REPORT_UTILS
SPEC.loader.exec_module(REPORT_UTILS)


class ReportUtilsCase(unittest.TestCase):
    def test_extract_center_code(self):
        self.assertEqual(REPORT_UTILS.extract_center_code("DEVLYN_A753_01"), "A753")
        self.assertEqual(REPORT_UTILS.extract_center_code("DEVLYN_A029"), "A029")
        self.assertIsNone(REPORT_UTILS.extract_center_code("TEST_DEVICE_01"))
        self.assertIsNone(REPORT_UTILS.extract_center_code(""))

    def test_choose_center_code(self):
        self.assertEqual(REPORT_UTILS.choose_center_code([None, "A753", None]), "A753")
        self.assertEqual(REPORT_UTILS.choose_center_code(["A317", "A317"]), "A317")
        self.assertIsNone(REPORT_UTILS.choose_center_code(["A317", "A753"]))
        self.assertIsNone(REPORT_UTILS.choose_center_code([None, None]))

    def test_hours_to_hhmm(self):
        self.assertEqual(REPORT_UTILS.hours_to_hhmm(0), "00:00")
        self.assertEqual(REPORT_UTILS.hours_to_hhmm(7.5), "07:30")
        self.assertEqual(REPORT_UTILS.hours_to_hhmm(1.75), "01:45")

    def test_minutes_to_hhmm(self):
        self.assertEqual(REPORT_UTILS.minutes_to_hhmm(0), "00:00")
        self.assertEqual(REPORT_UTILS.minutes_to_hhmm(61), "01:01")

    def test_derive_segment_center_code(self):
        self.assertEqual(
            REPORT_UTILS.derive_segment_center_code("DEVLYN_A753_01", None),
            "A753",
        )
        self.assertEqual(
            REPORT_UTILS.derive_segment_center_code(None, "DEVLYN_A753_02"),
            "A753",
        )
        self.assertIsNone(
            REPORT_UTILS.derive_segment_center_code("DEVLYN_A753_01", "DEVLYN_B204_01")
        )


if __name__ == "__main__":
    unittest.main()
