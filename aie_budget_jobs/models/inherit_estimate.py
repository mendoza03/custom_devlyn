from odoo import models, fields

class JobCostEstimate(models.TransientModel):
    _inherit = 'job.cost.estimate'

    estimated_qty = fields.Float(
        string='Estimated Quantity',
        help='Enter the estimated quantity for the job costing.'
    )