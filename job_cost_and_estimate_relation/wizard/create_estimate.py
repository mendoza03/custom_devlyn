# -*- coding: utf-8 -*-

from odoo import models, fields, api

class JobCostEstimate(models.TransientModel):
    _name = 'job.cost.estimate'
    _description = 'Job Cost Estimate'
    
    partner_id = fields.Many2one(
        'res.partner',
        required = True,
        string='Customer',
    )
    price_list_id = fields.Many2one(
        'product.pricelist',
        'Price List',
        required = True,
    )
    
    @api.model
    def default_get(self, fields):
        rec = super(JobCostEstimate, self).default_get(fields)
        active_id = self.env['job.costing'].browse(self._context.get('active_id'))
        partner = active_id.partner_id
        pricelist = partner.property_product_pricelist
        rec.update({
                'partner_id' : partner.id,
                'price_list_id' : pricelist.id,
        })
        return rec
    
    
    # @api.multi
    def _prepare_estimate_lines(self, estimate, active_id):
        line_obj = self.env['sale.estimate.line.job']
        job_type_obj = self.env['estimate.job.type']
        code_lst = []

        from_currency = active_id.currency_id
        to_currency = self.price_list_id.currency_id

        for line in active_id.job_cost_line_ids:
            code_lst += job_type_obj.search([('code','=',line.job_type_id.code)]).ids
            if not line.uom_id:
                uom_id = line.product_id.uom_id.id
            else:
                uom_id = line.uom_id.id

            cost_price = line.cost_price#unused?
            if from_currency != to_currency:#unused?
                # cost_price = from_currency.compute(cost_price, to_currency) #unused?
                cost_price = from_currency._convert(cost_price, to_currency) #unused?

            sale_price = line.product_id.lst_price
            if from_currency != to_currency:
                # sale_price = from_currency.compute(sale_price, to_currency)
                sale_price = from_currency._convert(sale_price, to_currency)

            mat_vals = {
                'job_type':line.job_type_id.job_type,
                'product_id':line.product_id.id,
                'product_description':line.description,
                'product_uom_qty':line.product_qty,
                'product_uom':uom_id,
                'price_unit': sale_price, #line.cost_price, # 8may2020
                #'price_unit':cost_price, # 8may2020
                'estimate_id':estimate.id,
            }
            line_obj.create(mat_vals)

        for labour_line in active_id.job_labour_line_ids:
            code_lst += job_type_obj.search([('code','=',labour_line.job_type_id.code)]).ids

            cost_price = labour_line.cost_price#unused?
            if from_currency != to_currency:#unused?
                # cost_price = from_currency.compute(cost_price, to_currency)#unused?
                cost_price = from_currency._convert(cost_price, to_currency)#unused?

            sale_price = labour_line.product_id.lst_price
            if from_currency != to_currency:
                # sale_price = from_currency.compute(sale_price, to_currency)
                sale_price = from_currency._convert(sale_price, to_currency)

            labour_vals = {
                'job_type':labour_line.job_type_id.job_type,
                'product_id':labour_line.product_id.id,
                'product_description':labour_line.description,
                'product_uom_qty':labour_line.hours,
                'product_uom':labour_line.product_id.uom_id.id,
#                 'price_unit':labour_line.cost_price,
                'price_unit': sale_price, #cost_price,  # 8may2020
                'estimate_id':estimate.id,
            }
            line_obj.create(labour_vals)
            
        for overhead_line in active_id.job_overhead_line_ids:
            code_lst += job_type_obj.search([('code','=',overhead_line.job_type_id.code)]).ids
            if not overhead_line.uom_id:
                uom_id = overhead_line.product_id.uom_id.id
            else:
                uom_id = line.uom_id.id

            cost_price = overhead_line.cost_price#unused?
            if from_currency != to_currency:#unused?
                # cost_price = from_currency.compute(cost_price, to_currency)#unused?
                cost_price = from_currency._convert(cost_price, to_currency)#unused?

            sale_price = overhead_line.product_id.lst_price
            if from_currency != to_currency:
                # sale_price = from_currency.compute(sale_price, to_currency)
                sale_price = from_currency._convert(sale_price, to_currency)

            overhead_vals = {
                'job_type':overhead_line.job_type_id.job_type,
                'product_id':overhead_line.product_id.id,
                'product_description':overhead_line.description,
                'product_uom_qty':overhead_line.product_qty,
                'product_uom':overhead_line.uom_id.id,
#                 'price_unit':overhead_line.cost_price,
                'price_unit':sale_price, #cost_price, # 8may2020
                'estimate_id':estimate.id,
            }
            line_obj.create(overhead_vals)
        estimate.write({
            'job_type_ids':[(6, 0, code_lst)],
        })
    
    # @api.multi
    def create_estimation(self):
        self.ensure_one()
        active_id = self.env['job.costing'].browse(self._context.get('active_id'))
        job_estimate_obj = self.env['sale.estimate.job']
        partner_id = self.partner_id
        pricelist_id = self.price_list_id
        company_id = active_id.company_id.id
        currency_id = active_id.currency_id.id
        project_id = active_id.project_id.id
        
        for rec in self:
            vals = {
                'partner_id':partner_id.id,
                'pricelist_id':pricelist_id.id,
                'estimate_date':fields.Date.today(),
                'company_id':company_id,
                'currency_id':currency_id,
                'project_id':project_id,
                'jobcost_id':active_id.id,
            }
            estimate = job_estimate_obj.create(vals)
            rec._prepare_estimate_lines(estimate, active_id)
            estimate_lst = active_id.cost_estimate_ids.ids
            estimate_lst.append(estimate.id)
            active_id.write({
                'cost_estimate_ids': [(6, 0, estimate_lst)],
            })
        # action = self.env.ref('job_cost_estimate_customer.action_estimate_job').sudo().read()[0]
        action = self.env['ir.actions.act_window']._for_xml_id('job_cost_estimate_customer.action_estimate_job')
        # action['domain'] = [('jobcost_id', 'in', active_id.cost_estimate_ids.ids)]
        action['domain'] = [('id', '=', estimate.id)]
        return action