from odoo import api, fields, models, _
from odoo.exceptions import UserError


class ProjectCategory(models.Model):
    _name = "project.worksite.category"
    _description = "Project Worksite Category"

    name = fields.Char()


class Amenities(models.Model):
    _name = "project.amenities"
    _description = "Project Amenities"

    name = fields.Char("Amenity", required=True)


class Utilities(models.Model):
    _name = "property.utilities"
    _description = "Utilities"

    name = fields.Char("Utility")
    price = fields.Float("Price")
    property_id = fields.Many2one("product.template")
    project_id = fields.Many2one("project.worksite")


class Taxes(models.Model):
    _name = "price.taxes"
    _description = "Taxes"

    name = fields.Char("Tax Name")
    tax_rate = fields.Float("Tax Rate")
    description = fields.Char("Description",related="name")

    calculated_tax = fields.Float(string="Calculated Tax", compute="_compute_tax_calculate", store=True)
    contract_id = fields.Many2one("property.contract")
    tax_base_amount = fields.Float(related="contract_id.tax_base_amount", string="Tax Base Amount", store=True)

    @api.depends('tax_base_amount', 'tax_rate')
    def _compute_tax_calculate(self):
        for rec in self:
            rec.calculated_tax = rec.tax_base_amount * rec.tax_rate / 100
