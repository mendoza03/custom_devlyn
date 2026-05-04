# -*- coding: utf-8 -*-

from odoo import fields, models, api


class Project(models.Model):
    _inherit = "project.project"

    @api.depends()
    def _compute_job_estimate_count(self):
        estimate_ids = self.env['sale.estimate.job']
        for record in self:
            record.job_estimate_count = estimate_ids.search_count([('project_id', '=', record.id)])

    job_estimate_count = fields.Integer(
        string='Estimate Count',
        compute='_compute_job_estimate_count', 
        readonly=True, 
        default=0,
        copy=False,
    )

    def show_job_estimate(self):
        self.ensure_one()
        res = self.env['ir.actions.act_window']._for_xml_id('job_cost_estimate_customer.action_estimate_job')
        res['domain'] = str([('project_id','=', self.id)])
        return res

# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:
