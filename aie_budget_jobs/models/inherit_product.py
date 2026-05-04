from odoo import models, fields, api
from datetime import date



class ProductTemplate(models.Model):
    _inherit = 'product.template'

    def name_get(self):
        return [(template.id, template.name) for template in self]

    @api.model
    def name_search(self, name='', args=None, operator='ilike', limit=100):
        args = args or []
        templates = self.search(args + [('name', operator, name)], limit=limit)
        return templates.name_get()