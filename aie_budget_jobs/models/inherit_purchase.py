from odoo import models, fields, api
from datetime import date

class InheritPurchaseOrder(models.Model):
    _inherit = 'purchase.order'

    job_costing_id = fields.Many2one('job.costing', string="Job Costing")
