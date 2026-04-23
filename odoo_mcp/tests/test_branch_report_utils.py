from datetime import date

from odoo_mcp.branch_report import choose_center_code, extract_center_code, hours_to_hhmm, utc_bounds_for_local_dates


def test_extract_center_code():
    assert extract_center_code("DEVLYN_A753_01") == "A753"
    assert extract_center_code("other") is None


def test_choose_center_code_requires_unique_value():
    assert choose_center_code(["A753", "A753", None]) == "A753"
    assert choose_center_code(["A753", "B204"]) is None


def test_hours_to_hhmm():
    assert hours_to_hhmm(3.5) == "03:30"


def test_utc_bounds_for_local_dates():
    start, end = utc_bounds_for_local_dates(date(2026, 4, 10), date(2026, 4, 10), "America/Mexico_City", "UTC")
    assert start < end
