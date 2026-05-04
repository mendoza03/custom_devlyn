from odoo.exceptions import UserError
from odoo import models, fields,_, api

class JobCostingSubcontractingWizard(models.TransientModel):
    _name = 'job.costing.subcontracting.wizard'
    _description = 'Subcontracting Wizard'

    job_costing_id = fields.Many2one('job.costing', string='Job Costing', required=True, readonly=True)
    job_cost_line_id = fields.Many2one('job.cost.line', string='Job Cost Line', required=True,
        domain="[('direct_id', '=', job_costing_id)]")
    quantity = fields.Float(string="Quantity")

    @api.onchange('job_cost_line_id')
    def _onchange_job_cost_line_id(self):
        if self.job_cost_line_id:
            self.quantity = self.job_cost_line_id.product_qty

    def action_confirm(self):
        self.ensure_one()
        line = self.job_cost_line_id
        job = self.job_costing_id

        if not line.product_id:
            raise UserError("The selected job cost line has no product.")
        if self.quantity <= 0:
            raise UserError("Quantity must be greater than zero.")

        purchase_order = self.env['purchase.order'].create({
            'partner_id': job.partner_id.id or self.env.user.company_id.partner_id.id,
            'origin': job.name,
            'job_costing_id': job.id,
        })

        self.env['purchase.order.line'].create({
            'order_id': purchase_order.id,
            'product_id': line.product_id.id,
            'name': line.product_id.name,
            'product_qty': self.quantity,
            'price_unit': line.product_id.lst_price,
            'product_uom': line.product_id.uom_id.id,
            'date_planned': fields.Date.today(),
        })

        self.job_cost_line_id.is_subcontracted = True

        return {
            'type': 'ir.actions.act_window',
            'res_model': 'purchase.order',
            'res_id': purchase_order.id,
            'view_mode': 'form',
            'target': 'current',
        }
