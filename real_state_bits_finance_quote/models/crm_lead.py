# -*- coding: utf-8 -*-
from odoo import models

class CrmLeadInherit(models.Model):
    _inherit = 'crm.lead'

    #* ---------------------------------------------------------
    #* Super Methods
    #* ---------------------------------------------------------

    def _prepare_opportunity_quotation_context(self):
        res = super()._prepare_opportunity_quotation_context()
        #res['default_order_line'] = [(0, 0, {'product_template_id': self.property_id.id, 'product_id': self.property_id.product_variant_id.id, 'product_uom_qty': 1})]
        return res