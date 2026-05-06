from odoo import api, fields, models


class BiometricPolicy(models.Model):
    _name = "biometric.policy"
    _description = "Biometric Policy"

    name = fields.Char(default="Default Policy", required=True)
    active = fields.Boolean(default=True)

    biometric_mode = fields.Selection(
        [
            ("disabled", "Disabled"),
            ("admin_demo_only", "Admin Demo Only"),
            ("all_users", "All Users"),
        ],
        default="admin_demo_only",
        required=True,
    )
    attendance_sync_enabled = fields.Boolean(default=False)
    admin_demo_login = fields.Char(default="admin")

    liveness_threshold = fields.Float(default=80.0)
    liveness_max_attempts = fields.Integer(default=3)

    gps_required = fields.Boolean(default=True)
    geofence_enforced = fields.Boolean(default=False)

    alert_country_change = fields.Boolean(default=True)
    alert_asn_change = fields.Boolean(default=True)
    alert_new_device = fields.Boolean(default=True)
    alert_low_score = fields.Boolean(default=True)

    auth_base_url = fields.Char(default="https://auth.odootest.mvpstart.click")
    erp_base_url = fields.Char(default="https://erp.odootest.mvpstart.click")

    api_key = fields.Char(string="Gateway API Key")

    @api.model
    def get_active_policy(self):
        policy = self.search([("active", "=", True)], limit=1)
        if not policy:
            policy = self.create({"name": "Default Policy"})
        return policy

    def should_force_gateway(self):
        self.ensure_one()
        return self.biometric_mode == "all_users"

    def is_demo_login_allowed(self, login):
        self.ensure_one()
        candidate = (login or "").strip().lower()
        expected = (self.admin_demo_login or "").strip().lower()
        return bool(
            candidate
            and expected
            and self.biometric_mode in {"admin_demo_only", "all_users"}
            and candidate == expected
        )
