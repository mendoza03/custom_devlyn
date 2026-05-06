from odoo import _, fields, models


class HrBiometricSyncRun(models.Model):
    _name = "hr.biometric.sync.run"
    _description = "HR Biometric Sync Run"
    _order = "started_at desc, id desc"

    name = fields.Char(required=True, default=lambda self: _("Biometric Sync Run"))
    run_type = fields.Selection(
        [
            ("sync", "Sync"),
            ("close", "Daily Close"),
            ("reconcile", "Reconcile"),
            ("backfill", "Relleno histórico"),
        ],
        required=True,
        default="sync",
        index=True,
    )
    status = fields.Selection(
        [("running", "Running"), ("success", "Success"), ("failed", "Failed")],
        required=True,
        default="running",
        index=True,
    )
    started_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True)
    finished_at = fields.Datetime()
    last_normalized_event_id = fields.Integer()
    processed_count = fields.Integer(default=0)
    created_count = fields.Integer(default=0)
    updated_count = fields.Integer(default=0)
    skipped_count = fields.Integer(default=0)
    error_count = fields.Integer(default=0)
    message = fields.Text()
