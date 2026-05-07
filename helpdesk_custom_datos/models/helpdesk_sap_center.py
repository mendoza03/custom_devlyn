from odoo import models, fields, api


class HelpdeskSapCenter(models.Model):
    _name = 'helpdesk.sap.center'
    _description = 'SAP Center'
    _rec_name = 'display_name'

    code = fields.Char(
        string='Centro SAP',
        required=True,
    )

    x_branch_id = fields.Many2one(
        'devlyn.catalog.branch',
        string='Óptica',
        domain=[('active', '=', True)],
        ondelete='restrict',
    )

    active = fields.Boolean(
        default=True
    )

    display_name = fields.Char(
        string='Nombre',
        compute='_compute_display_name',
        store=True,
    )

    @api.depends('code', 'x_branch_id', 'x_branch_id.name')
    def _compute_display_name(self):
        for rec in self:
            code = rec.code or ''
            branch_name = rec.x_branch_id.name or ''

            if branch_name:
                rec.display_name = f"{code} - {branch_name}"
            else:
                rec.display_name = code