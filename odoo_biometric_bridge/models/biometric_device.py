from odoo import fields, models


class BiometricDevice(models.Model):
    _name = "biometric.device"
    _description = "Biometric Device"

    name = fields.Char(compute="_compute_name", store=True)
    user_id = fields.Many2one("res.users", required=True, ondelete="cascade")
    device_fingerprint = fields.Char(required=True, index=True)
    browser = fields.Char()
    os = fields.Char()
    device_type = fields.Selection(
        [
            ("desktop", "Desktop"),
            ("mobile", "Mobile"),
            ("tablet", "Tablet"),
            ("other", "Other"),
        ],
        default="other",
    )
    first_seen = fields.Datetime(default=fields.Datetime.now)
    last_seen = fields.Datetime(default=fields.Datetime.now)

    _uniq_biometric_device_user_fingerprint = models.Constraint(
        "UNIQUE(user_id, device_fingerprint)",
        "La huella del dispositivo ya existe para este usuario.",
    )

    def _compute_name(self):
        for rec in self:
            rec.name = f"{rec.user_id.login} - {rec.device_type}"
