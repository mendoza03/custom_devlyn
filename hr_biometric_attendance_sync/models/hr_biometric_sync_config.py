from odoo import api, fields, models


class HrBiometricSyncConfig(models.Model):
    _name = "hr.biometric.sync.config"
    _description = "HR Biometric Sync Configuration"

    name = fields.Char(required=True, default="Default")
    active = fields.Boolean(default=True)
    timezone_name = fields.Char(required=True, default="America/Mexico_City")
    sync_interval_seconds = fields.Integer(required=True, default=60)
    debounce_seconds = fields.Integer(required=True, default=90)
    close_time_local = fields.Char(required=True, default="23:59")
    reconcile_time_local = fields.Char(required=True, default="00:15")
    source_mode_label = fields.Char(required=True, default="biometric_v1")
    auto_close_enabled = fields.Boolean(default=True)
    reconcile_enabled = fields.Boolean(default=True)
    accept_unresolved_device = fields.Boolean(default=True)
    last_close_run_date = fields.Date()
    last_reconcile_run_date = fields.Date()

    @api.model
    def get_singleton(self):
        config = self.search([], limit=1)
        if config:
            return config
        return self.create({})

