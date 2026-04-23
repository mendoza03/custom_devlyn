from odoo import models
from odoo.exceptions import AccessDenied


class ResUsers(models.Model):
    _inherit = "res.users"

    def _auth_oauth_signin(self, provider, validation, params):
        try:
            return super()._auth_oauth_signin(provider, validation, params)
        except AccessDenied:
            oauth_uid = validation.get("user_id")
            email = (validation.get("email") or "").strip().lower()
            preferred_username = (validation.get("preferred_username") or "").strip().lower()

            domain = []
            if email and preferred_username:
                domain = ["|", ("login", "=", email), ("login", "=", preferred_username)]
            elif email:
                domain = [("login", "=", email)]
            elif preferred_username:
                domain = [("login", "=", preferred_username)]

            if not domain:
                raise

            user = self.search(domain, limit=1)
            if not user:
                raise

            user.sudo().write(
                {
                    "oauth_provider_id": provider,
                    "oauth_uid": oauth_uid,
                    "oauth_access_token": params.get("access_token"),
                }
            )
            return user.login
