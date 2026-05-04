from odoo import api, fields, models, _
from odoo.exceptions import UserError


class PropertyType(models.Model):
    _name = "property.type"
    _description = "Property Type"

    name = fields.Char(string="Property Type")


class ProductCategory(models.Model):
    _inherit = "product.category"

    @api.depends()
    def _compute_is_apply(self):
        commission_based_on = self.env.company.commission_based_on
        for rec in self:
            rec.is_apply = False
            if commission_based_on == 'product_category':
                rec.is_apply = True

    commission_type = fields.Selection(string="Commission Amount Type", selection=[('percentage', 'By Percentage'),
                                                                                   ('fix', 'Fixed Amount')])
    is_apply = fields.Boolean(string='Is Apply ?', compute='_compute_is_apply')
    commission_range_ids = fields.One2many('sales.commission.range', 'commission_category_id',
                                           string='Sales Commission Range Category')
