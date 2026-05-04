# -*- coding: utf-8 -*-

from odoo import fields, models


class ResConfigSettings(models.TransientModel):
    _inherit = 'res.config.settings'

    commission_upon_signing = fields.Float(related='company_id.commission_upon_signing', readonly=False)
    commission_on_the_deed = fields.Float(related='company_id.commission_on_the_deed', readonly=False)