from odoo import fields, models


class BiometricAuthAlert(models.Model):
    _name = "biometric.auth.alert"
    _description = "Biometric Authentication Alert"
    _order = "create_date desc"

    name = fields.Char(required=True)
    event_id = fields.Many2one("biometric.auth.event", ondelete="cascade")
    user_id = fields.Many2one("res.users")

    severity = fields.Selection(
        [
            ("low", "Low"),
            ("medium", "Medium"),
            ("high", "High"),
            ("critical", "Critical"),
        ],
        default="medium",
        required=True,
    )
    code = fields.Char(required=True)
    message = fields.Text(required=True)

    resolved = fields.Boolean(default=False)
    resolved_by = fields.Many2one("res.users")
    resolved_at = fields.Datetime()

    def action_resolve(self):
        for rec in self:
            rec.resolved = True
            rec.resolved_by = self.env.user
            rec.resolved_at = fields.Datetime.now()
