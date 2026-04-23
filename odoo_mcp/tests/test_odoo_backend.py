from __future__ import annotations

from odoo_mcp.backends.odoo_backend import _normalize_record


def test_normalize_record_keeps_many2one_shape():
    payload = {"project_id": [3, "Biométricos"]}
    field_map = {"project_id": {"type": "many2one"}}

    normalized = _normalize_record(payload, field_map)

    assert normalized["project_id"] == {"id": 3, "display_name": "Biométricos"}


def test_normalize_record_keeps_many2many_as_raw_ids():
    payload = {"user_ids": [2, 10]}
    field_map = {"user_ids": {"type": "many2many"}}

    normalized = _normalize_record(payload, field_map)

    assert normalized["user_ids"] == [2, 10]
