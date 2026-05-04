from odoo import models, fields, api, _
from odoo.exceptions import UserError

class JobCostLine(models.Model):
    _inherit = 'job.cost.line'

    direct_id = fields.Many2one(
        comodel_name='job.costing',
        string='Job Costing'
    )

    hide_add_to_requisition = fields.Boolean(
        string="Hide Add To Requisition",
        related='direct_id.hide_add_to_requisition',
        store=False,
        readonly=True,
    )

    is_subcontracted = fields.Boolean(string="Subcontracted", default=False)

    def action_add_to_requisition(self):
        for line in self:
            job = line.direct_id
            if not job:
                raise UserError(_("This cost line is not linked to any job costing."))

            if not line.product_id:
                raise UserError(_("No product selected on this line."))

            requisitions = self.env['material.purchase.requisition'].search([
                ('job_costing_id', '=', job.id),
            ])

            requisition_lines = self.env['material.purchase.requisition.line'].search([
                ('requisition_id', 'in', requisitions.ids),
                ('product_id', '=', line.product_id.id),
            ])

            total_requested_qty = sum(requisition_lines.mapped('qty'))
            missing_qty = line.product_qty - total_requested_qty

            if missing_qty <= 0:
                raise UserError(_("This product has already been fully added to requisitions for this job costing."))

            requisition = self.env['material.purchase.requisition'].search([
                ('state', '=', 'draft'),
                ('job_costing_id', '=', job.id),
            ], limit=1)

            if not requisition:
                employee = self.env['hr.employee'].search([('user_id', '=', self.env.uid)], limit=1)
                if not employee:
                    raise UserError(_("No employee record found for current user."))

                requisition_vals = {
                    'requisiton_responsible_id': employee.id,
                    'project_id': job.project_id.id,
                    'department_id': employee.department_id.id,
                    'company_id': job.company_id.id,
                    'request_date': fields.Date.today(),
                    'job_costing_id': job.id,
                    'project_id': job.project_id.id,
                    'task_id': job.task_id.id,
                }

                requisition = self.env['material.purchase.requisition'].create(requisition_vals)

            self.env['material.purchase.requisition.line'].create({
                'requisition_id': requisition.id,
                'product_id': line.product_id.id,
                'description': line.description or line.product_id.display_name,
                'qty': missing_qty,
                'uom': line.uom_id.id,
                'requisition_type': 'purchase',
            })

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'material.purchase.requisition',
                'res_id': requisition.id,
                'view_mode': 'form',
                'target': 'current',
            }
