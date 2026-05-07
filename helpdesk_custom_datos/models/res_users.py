from odoo import fields, models, api


class ResUsers(models.Model):
    _inherit = "res.users"

    x_branch_id = fields.Many2one(
        "devlyn.catalog.branch",
        string="Sucursal",
        domain=[("active", "=", True)],
        ondelete="restrict",
    )

    sap_center_id = fields.Many2one(
        'helpdesk.sap.center',
        string='Centro SAP',
    )

    @api.onchange('sap_center_id')
    def _onchange_sap_center_id(self):
        for rec in self:
            rec.x_branch_id = rec.sap_center_id.x_branch_id

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            sap_center_id = vals.get('sap_center_id')

            if sap_center_id and not vals.get('x_branch_id'):
                sap_center = self.env['helpdesk.sap.center'].browse(sap_center_id)
                vals['x_branch_id'] = sap_center.x_branch_id.id

        return super().create(vals_list)

    def write(self, vals):
        if vals.get('sap_center_id'):
            sap_center = self.env['helpdesk.sap.center'].browse(vals['sap_center_id'])
            vals['x_branch_id'] = sap_center.x_branch_id.id

        return super().write(vals)

    @property
    def SELF_READABLE_FIELDS(self):
        return super().SELF_READABLE_FIELDS + [
            "x_branch_id",
            "sap_center_id",
        ]

    @property
    def SELF_WRITEABLE_FIELDS(self):
        return super().SELF_WRITEABLE_FIELDS + [
            "x_branch_id",
            "sap_center_id",
        ]