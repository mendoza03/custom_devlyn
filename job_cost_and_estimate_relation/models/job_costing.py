# -*- coding: utf-8 -*-

from odoo import models, fields, api


class JobCosting(models.Model):
    _inherit = 'job.costing'
    
    cost_estimate_ids = fields.Many2many(
        'sale.estimate.job',
        string='Estimations',
        # stored=True,
        copy=False,
    )
    
    # @api.multi
    def action_view_job_estimate(self):
        self.ensure_one()
        # action = self.env.ref('job_cost_estimate_customer.action_estimate_job').sudo().read()[0]
        action = self.env['ir.actions.act_window']._for_xml_id('job_cost_estimate_customer.action_estimate_job')
        action['domain'] = [('id', 'in', self.cost_estimate_ids.ids)]
        return action
