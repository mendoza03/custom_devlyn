# -*- coding: utf-8 -*-
from odoo import models, fields

class UtmSource(models.Model):
    _inherit = 'utm.source'

    crm_check = fields.Boolean(
        string='show crm',
    )


class UtmMedium(models.Model):
    _inherit = 'utm.medium'

    crm_check = fields.Boolean(
        string='show crm',
    )