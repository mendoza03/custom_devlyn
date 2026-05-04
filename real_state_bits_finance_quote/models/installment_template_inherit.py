# -*- coding: utf-8 -*-
from odoo import models, _, fields

class CustomInstallmentTemplate(models.Model):
    _inherit = 'installment.template'

    payment_term_ids = fields.One2many('payment.terms', 'installment_template_id', string="Payment Terms")
    cat = fields.Float(string="CAT")