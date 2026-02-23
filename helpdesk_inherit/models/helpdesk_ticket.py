from odoo import models, fields, api

class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    general_description = fields.Char(
        string="General Description",
        required=True
    )

    section_id = fields.Many2one(
        'helpdesk.section',
        string="Section",
        required=True
    )

    category_id = fields.Many2one(
        'helpdesk.category',
        string="Category",
        required=True
    )

    subcategory_id = fields.Many2one(
        'helpdesk.subcategory',
        string="Subcategory",
        required=True
    )

    detailed_description = fields.Html(
        string="Detailed Description"
    )

    @api.onchange('section_id')
    def _onchange_section(self):
        return {
            'domain': {
                'category_id': [('section_id', '=', self.section_id.id)]
            }
        }

    @api.onchange('category_id')
    def _onchange_category(self):
        return {
            'domain': {
                'subcategory_id': [('category_id', '=', self.category_id.id)]
            }
        }