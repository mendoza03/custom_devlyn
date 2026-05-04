from odoo import models, fields


class CancelTypes(models.Model):
    _name = 'cancel.types'
    _description = 'Cancel Types'
    _rec_name = 'name'

    name = fields.Char(
        string='Name',
        required=True
    )

    description = fields.Text(
        string='Description'
    )

    active = fields.Boolean(
        default=True
    )
