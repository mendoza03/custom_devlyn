from odoo import models, fields

class HelpdeskSection(models.Model):
    _name = 'helpdesk.section'
    _description = 'Section'

    name = fields.Char(string="Name", required=True)


class HelpdeskCategory(models.Model):
    _name = 'helpdesk.category'
    _description = 'Category'

    name = fields.Char(string="Name", required=True)
    section_id = fields.Many2one(
        'helpdesk.section',
        string="Section"
    )


class HelpdeskSubcategory(models.Model):
    _name = 'helpdesk.subcategory'
    _description = 'Subcategory'

    name = fields.Char(string="Name", required=True)
    category_id = fields.Many2one(
        'helpdesk.category',
        string="Category"
    )