# -*- coding: utf-8 -*-
# Part of Probuse Consulting Service Pvt Ltd. See LICENSE file for full copyright and licensing details.

from odoo import models, fields, api

class ResPartner(models.Model):
    _inherit = 'res.partner'

    @api.depends()
    def _compute_job_estimate_count(self):
        estimate_ids = self.env['sale.estimate.job']
        for record in self:
            record.job_estimate_count = estimate_ids.search_count([('partner_id', '=', record.id)])

    job_estimate_count = fields.Integer(
        string='Estimate Count',
        compute='_compute_job_estimate_count', 
        readonly=True, 
        default=0,
        copy=False,
    )

    def show_job_estimate_partner(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('job_cost_estimate_customer.action_estimate_job')
        res['domain'] = str([('partner_id','=', self.id)])
        return res