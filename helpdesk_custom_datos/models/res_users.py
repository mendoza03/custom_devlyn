from odoo import fields, models


class ResUsers(models.Model):
    _inherit = "res.users"

    x_branch_id = fields.Many2one(
        "devlyn.catalog.branch",
        string="Sucursal",
        domain=[("active", "=", True)],
        ondelete="restrict",
    )

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + ["x_branch_id"]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + ["x_branch_id"]
