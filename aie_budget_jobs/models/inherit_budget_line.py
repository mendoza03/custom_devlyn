from odoo import models, fields, api
from datetime import date

class MasterBudgetLine(models.Model):
    _inherit = 'master.budget.line'

    job_costing_id = fields.Many2one(
        comodel_name='job.costing',
        string='Related Job Costing',
        help='Internal link to created job costing',
        copy=False
    )

    job_cost_line_id = fields.Many2one(
        comodel_name='job.cost.line',
        string='Related Job Cost Line',
        help='Link to created job cost line',
        copy=False
    )

    categ_product = fields.Char(related='product_id.categ_id.display_name', string='Category')
    ref_product = fields.Char(related='product_id.default_code', string='Reference')



    @api.model
    def create(self, vals):
        line = super().create(vals)

        if line.type == 'concept':
            job_costing = self.env['job.costing'].create({
                'master_budget_id': line.budget_id.id,
                'project_id': line.budget_id.project_id.id,
                'analytic_id': line.budget_id.project_id.account_id.id if line.budget_id.project_id.account_id else False,
                'partner_id': line.budget_id.project_id.partner_id.id if line.budget_id.project_id.partner_id else False,
                'name': line.name,
                'description': line.name,
                'task_id': line.parent_id.task_id.id,
            })
            line.job_costing_id = job_costing

        elif line.type == 'budget_item' and line.parent_id and line.parent_id.type == 'concept':
            product = line.product_id
            if product:
                if product.type == 'consu' or product.type == 'service':
                    job_search = 'Material' if product.type == 'consu' else 'Mano de Obra' if product.type == 'service' else None
                    job_type = 'material' if product.type == 'consu' else 'labour' if product.type == 'service' else 'overhead'
                    job_type_rec = self.env['job.type'].search([('name', '=', job_search)], limit=1)

                    job_cost_line = self.env['job.cost.line'].create({
                        'direct_id': line.parent_id.job_costing_id.id,
                        'date': date.today(),
                        'description': product.name,
                        'product_id': product.product_variant_id.id,
                        'product_qty': line.quantity,
                        'cost_price': line.price_unit,
                        'uom_id': line.product_uom.id,
                        'job_type': job_type,
                        'job_type_id': job_type_rec.id if job_type_rec else False,
                    })

                    line.job_cost_line_id = job_cost_line.id

        return line

    def write(self, vals):
        res = super().write(vals)
        for line in self:
            if line.job_cost_line_id:
                updates = {}
                if 'product_id' in vals:
                    updates['product_id'] = line.product_id.product_variant_id.id
                    updates['description'] = line.product_id.name
                if 'quantity' in vals:
                    updates['product_qty'] = line.quantity
                if 'price_unit' in vals:
                    updates['cost_price'] = line.price_unit
                if 'product_uom' in vals:
                    updates['uom_id'] = line.product_uom.id
                if updates:
                    line.job_cost_line_id.write(updates)
        return res

