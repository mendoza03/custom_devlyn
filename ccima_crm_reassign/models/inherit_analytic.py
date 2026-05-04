from odoo import models, fields, api, _
from odoo.exceptions import UserError


class AccountAnalyticLine(models.Model):
    _inherit = "account.analytic.line"

    worksite_id = fields.Many2one('project.worksite', string="Worksite")