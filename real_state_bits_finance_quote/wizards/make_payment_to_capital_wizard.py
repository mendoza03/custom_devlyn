# -*- coding: utf-8 -*-
from odoo import models, fields  # type: ignore

#* ------------------------------- TMP -------------------------------
import sys
from loguru import logger as _logger
_logger.remove() 
log_format = "<level>{time:YYYY-MM-DD HH:mm:ss.SSS}</level> | <level>{level: <8}</level> | <level>{name}</level>:<level>{function}</level>:<level>{line}</level> - <level>{message}</level>"
_logger.add(sys.stdout, format=log_format, catch=True, colorize=True)
#* ------------------------------- REMOVE -------------------------------

class PaymentToCapitalWizard(models.TransientModel):
    _name = 'payment.to.capital.wizard'
    _description = "Payment To Capital Wizard"

    currency_id = fields.Many2one('res.currency', string="Currency Id")
    payment_amount = fields.Monetary(string="amount to be paid")
    contract_id = fields.Integer(string='contract id')
    payment_number = fields.Integer(string='payment number')

    def apply_payment_in_contract(self) -> dict[str, str]:
        contract_id = self.env['property.contract'].browse(self.contract_id)
        line_number = self.payment_number
        payment_amount = self.payment_amount
        contract_id._recalculate_lines(line_number, payment_amount) 
        return {
            'type': 'ir.actions.client',
            'tag': 'reload',
        }
