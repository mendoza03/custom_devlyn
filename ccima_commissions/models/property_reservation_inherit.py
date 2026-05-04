from odoo import models, fields


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    contract_date = fields.Date(
        string='Fecha de Contrato',
        default=fields.Date.today
    )
