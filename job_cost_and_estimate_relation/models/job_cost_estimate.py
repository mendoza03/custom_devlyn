# -*- coding: utf-8 -*-

from odoo import models, fields, api

class SaleEstimateJob(models.Model):
    _inherit = 'sale.estimate.job'
    
    jobcost_id = fields.Many2one(
        'job.costing',
        string='Jobcost Sheet',
    )
    
    # @api.multi
    def action_view_job_cost_sheet(self):
        self.ensure_one()
        # action = self.env.ref('odoo_job_costing_management.action_job_costing').sudo().read()[0]
        action = self.env['ir.actions.act_window']._for_xml_id('odoo_job_costing_management.action_job_costing')
        action['domain'] = [('id', 'in', self.jobcost_id.ids)]
        return action
