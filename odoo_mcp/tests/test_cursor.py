from odoo_mcp.cursor import decode_offset_cursor, encode_offset_cursor


def test_offset_cursor_roundtrip():
    cursor = encode_offset_cursor(150)
    assert cursor
    assert decode_offset_cursor(cursor) == 150


def test_offset_cursor_defaults_to_zero():
    assert decode_offset_cursor(None) == 0
