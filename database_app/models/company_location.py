from odoo import models, fields

class CompanyLocation(models.Model):
    _name = 'company.location'
    _description = 'Company Location'

    name = fields.Char(string='Name', required=True)
    address = fields.Char(string='Address (URL)', required=True)
