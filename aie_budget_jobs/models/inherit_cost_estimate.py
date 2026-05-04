from odoo import models, fields, api
from odoo.exceptions import UserError
from datetime import date

class JobCostEstimateInherit(models.TransientModel):
    _inherit = 'job.cost.estimate'

    @api.model
    def default_get(self, fields_list):
        res = super().default_get(fields_list)

        jobcost = self.env['job.costing'].browse(self.env.context.get('active_id'))
        if not jobcost:
            return res

        po_lines = self.env['purchase.order.line'].search([
            ('order_id.job_costing_id', '=', jobcost.id)
        ])
        received_qty = sum(po_lines.mapped('qty_received'))

        if received_qty > 0:
            res['estimated_qty'] = received_qty

        return res

    def create_estimation(self):
        self.ensure_one()
        jobcost = self.env['job.costing'].browse(self._context.get('active_id'))
        budget_line = self.env['master.budget.line'].search([('job_costing_id', '=', jobcost.id)], limit=1)

        if not budget_line or not budget_line.product_id:
            raise UserError("No related budget line with product found for this job costing.")

        product = budget_line.product_id.product_variant_id

        po_lines = self.env['purchase.order.line'].search([
            ('order_id.job_costing_id', '=', jobcost.id)
        ])
        received_qty = sum(po_lines.mapped('qty_received'))
        user_qty = self.estimated_qty

        if received_qty > 0:
            if user_qty and user_qty != received_qty:
                raise UserError(
                    "You cannot manually modify the estimated quantity because there are received purchases.\n"
                    f"Received quantity: {received_qty}"
                )
            qty = received_qty
        else:
            qty = user_qty

        if qty > budget_line.quantity:
            raise UserError(
                f"Estimated quantity ({qty}) cannot be greater than the quantity defined in the related budget line ({budget_line.quantity})."
            )

        bom = product.bom_ids and product.bom_ids[0] or False
        if not bom:
            raise UserError("The product does not have a Bill of Materials defined.")

        estimate = self.env['sale.estimate.job'].create({
            'partner_id': self.partner_id.id,
            'pricelist_id': self.price_list_id.id,
            'estimate_date': fields.Date.today(),
            'company_id': jobcost.company_id.id,
            'currency_id': jobcost.currency_id.id,
            'project_id': jobcost.project_id.id,
            'jobcost_id': jobcost.id,
        })

        self.env['sale.estimate.line.job'].create({
            'estimate_id': estimate.id,
            'product_id': product.id,
            'product_description': product.name,
            'product_uom_qty': qty,
            'product_uom': product.uom_id.id,
            'price_unit': product.lst_price,
            'job_type': 'material',
            'company_id': jobcost.company_id.id,
        })

        picking_type = self.env.ref('stock.picking_type_out', raise_if_not_found=False)
        if picking_type and picking_type.warehouse_id.company_id.id != jobcost.company_id.id:
            picking_type = self.env['stock.picking.type'].search([
                ('code', '=', 'outgoing'),
                ('company_id', '=', jobcost.company_id.id)
            ], limit=1)

        if not picking_type:
            raise UserError("No outgoing picking type found. Please configure one in Inventory.")

        picking = self.env['stock.picking'].create({
            'picking_type_id': picking_type.id,
            'partner_id': self.partner_id.id,
            'origin': estimate.number,
            'location_id': picking_type.default_location_src_id.id,
            'location_dest_id': picking_type.default_location_dest_id.id,
            'scheduled_date': date.today(),
            'company_id': jobcost.company_id.id,
        })

        for line in bom.bom_line_ids:
            self.env['stock.move'].create({
                'name': line.product_id.name,
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty * qty,
                'product_uom': line.product_uom_id.id,
                'picking_id': picking.id,
                'location_id': picking.location_id.id,
                'location_dest_id': picking.location_dest_id.id,
                'company_id': jobcost.company_id.id,
            })

        picking.action_confirm()
        picking.action_assign()

        for move_line in picking.move_line_ids:
            move_line.qty_done = move_line.move_id.product_uom_qty

        picking.button_validate()

        jobcost.write({
            'cost_estimate_ids': [(4, estimate.id)],
        })

        action = self.env['ir.actions.act_window']._for_xml_id('job_cost_estimate_customer.action_estimate_job')
        action['domain'] = [('id', '=', estimate.id)]
        return action
