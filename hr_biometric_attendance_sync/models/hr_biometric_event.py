from odoo import _, fields, models


class HrBiometricEvent(models.Model):
    _name = "hr.biometric.event"
    _description = "HR Biometric Attendance Event"
    _order = "event_occurred_at_utc desc, id desc"
    _rec_name = "name"

    _normalized_event_id_uniq = models.Constraint(
        "UNIQUE (normalized_event_id)",
        "The normalized event was already synchronized.",
    )

    name = fields.Char(required=True, default=lambda self: _("Biometric Event"))
    normalized_event_id = fields.Integer(required=True, index=True)
    source_raw_request_id = fields.Integer(index=True)
    event_kind = fields.Char(required=True, default="access_control", index=True)
    event_occurred_at_utc = fields.Datetime(required=True, index=True)
    event_local_date = fields.Date(index=True)
    event_local_display = fields.Char(index=True)
    user_id_on_device = fields.Char(index=True)
    card_name = fields.Char()
    employee_id = fields.Many2one("hr.employee", index=True)
    device_id_resolved = fields.Char(index=True)
    identity_resolution = fields.Char(index=True)
    source_ip = fields.Char()
    door_name = fields.Char()
    reader_id = fields.Char()
    direction_raw = fields.Selection(
        [("entry", "Entry"), ("exit", "Exit"), ("unknown", "Unknown")],
        default="unknown",
        required=True,
        index=True,
    )
    granted_state = fields.Selection(
        [("granted", "Granted"), ("denied", "Denied"), ("unknown", "Unknown")],
        default="unknown",
        required=True,
        index=True,
    )
    sync_status = fields.Selection(
        [
            ("pending", "Pending"),
            ("check_in_created", "Check-in Created"),
            ("check_out_written", "Check-out Written"),
            ("duplicate_ignored", "Duplicate Ignored"),
            ("employee_not_found", "Employee Not Found"),
            ("denied_ignored", "Denied Ignored"),
            ("after_close_review", "After Close Review"),
            ("error", "Error"),
        ],
        default="pending",
        required=True,
        index=True,
    )
    attendance_action = fields.Selection(
        [
            ("check_in_created", "Check-in Created"),
            ("check_out_written", "Check-out Written"),
            ("duplicate_ignored", "Duplicate Ignored"),
            ("employee_not_found", "Employee Not Found"),
            ("denied_ignored", "Denied Ignored"),
            ("after_close_review", "After Close Review"),
            ("error", "Error"),
        ],
        index=True,
    )
    attendance_id = fields.Many2one("hr.attendance", index=True)
    dedupe_reference_event_id = fields.Many2one("hr.biometric.event", index=True)
    inference_mode = fields.Char(default="biometric_v1", index=True)
    attendance_auto_closed = fields.Boolean(default=False, index=True)
    auto_close_reason = fields.Char()
    message = fields.Text()
    payload_json = fields.Json(default=dict)
