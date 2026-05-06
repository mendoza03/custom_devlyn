from odoo import fields, models


class HelpdeskCancelReason(models.Model):
    _name = 'helpdesk.cancel.reason'
    _description = 'Helpdesk Cancel Reason'
    _order = 'sequence, name'

    name = fields.Char(
        string='Reason',
        required=True,
        translate=True,
    )
    sequence = fields.Integer(
        default=10,
    )
    active = fields.Boolean(
        default=True,
    )
    description = fields.Text(
        string='Description',
        translate=True,
    )
