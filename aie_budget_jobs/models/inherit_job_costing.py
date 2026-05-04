# -*- coding: utf-8 -*-
from odoo import models, fields,_
from odoo.exceptions import UserError

class JobCosting(models.Model):
    _inherit = 'job.costing'

    master_budget_id = fields.Many2one(
        comodel_name='master.budget',
        string='Master budget',
        ondelete='restrict',
    )

    requisition_ids = fields.One2many(
        'material.purchase.requisition',
        'job_costing_id',
        string='Material Requisitions'
    )
    requisition_count = fields.Integer(
        compute='_compute_requisition_count',
        string='Requisition Count'
    )

    purchase_order_id = fields.Many2one(
        'purchase.order',
        string='Purchase Order',
        help='Purchase Order generated from this Job Costing'
    )
    hide_add_to_requisition = fields.Boolean(string="Hide Add To Requisition", default=False)

    purchase_order_count = fields.Integer(
        compute="_compute_purchase_order_count",
        string="Purchase Order Count"
    )

    def _compute_purchase_order_count(self):
        for job in self:
            count = self.env['purchase.order'].search_count([('job_costing_id', '=', job.id)])
            job.purchase_order_count = count

    def action_view_purchase_orders(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Purchase Orders',
            'res_model': 'purchase.order',
            'view_mode': 'list,form',
            'domain': [('job_costing_id', '=', self.id)],
            'context': {'default_job_costing_id': self.id},
        }

    def action_generate_purchase_order(self):
        for job in self:
            lines = self.env['master.budget.line'].search([
                ('job_costing_id', '=', job.id),
                ('product_id', '!=', False),
            ])

            if not lines:
                raise UserError(_("No master budget lines with products found for this Job Costing."))

            po = self.env['purchase.order'].create({
                'partner_id': job.partner_id.id or self.env.user.company_id.partner_id.id,
                'origin': job.name,
                'job_costing_id': job.id,
            })

            for line in lines:
                self.env['purchase.order.line'].create({
                    'order_id': po.id,
                    'product_id': line.product_id.product_variant_id.id,
                    'product_qty': line.quantity,
                    'price_unit': line.price_unit,
                    'product_uom': line.product_uom.id,
                    'name': line.product_id.display_name,
                    'date_planned': fields.Date.today(),
                })

            for line in self.job_cost_line_ids:
                line.is_subcontracted = True

            job.purchase_order_id = po
            job.hide_add_to_requisition = True

            return {
                'type': 'ir.actions.act_window',
                'res_model': 'purchase.order',
                'res_id': po.id,
                'view_mode': 'form',
                'target': 'current',
            }

    def _compute_requisition_count(self):
        for rec in self:
            rec.requisition_count = len(rec.requisition_ids)

    def action_view_requisitions(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'name': 'Material Requisitions',
            'res_model': 'material.purchase.requisition',
            'view_mode': 'list,form',
            'domain': [('job_costing_id', '=', self.id)],
            'context': {'default_job_costing_id': self.id},
        }

    def action_create_subcontracting(self):
        self.ensure_one()
        return {
            'type': 'ir.actions.act_window',
            'res_model': 'job.costing.subcontracting.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_job_costing_id': self.id,
            }
        }

