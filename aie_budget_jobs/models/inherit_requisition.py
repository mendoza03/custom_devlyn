from odoo import models, fields

class MaterialPurchaseRequisition(models.Model):
    _inherit = 'material.purchase.requisition'

    job_costing_id = fields.Many2one(
        'job.costing',
        string='Job Costing',
        ondelete='set null'
    )