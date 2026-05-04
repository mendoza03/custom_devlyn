from odoo import models, api, fields, _
from logging import getLogger
_log = getLogger(__name__)

class InheritAccountPayment(models.Model):
    _inherit = 'account.payment'

    def action_post(self):
        res = super().action_post()
        # if self.invoice_ids:
        #     if self.invoice_ids[0].line_id:
        #         self.invoice_ids[0].line_id.amount_paid = self.amount
        return res