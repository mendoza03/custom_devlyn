from odoo import fields, models


class HrBiometricSyncCursor(models.Model):
    _name = "hr.biometric.sync.cursor"
    _description = "HR Biometric Sync Cursor"

    _name_uniq = models.Constraint(
        "UNIQUE (name)",
        "The sync cursor name must be unique.",
    )

    name = fields.Char(required=True, default="main")
    active = fields.Boolean(default=True)
    last_normalized_event_id = fields.Integer(default=0)
    last_event_occurred_at_utc = fields.Datetime()
    last_success_at = fields.Datetime()
