# -*- coding: utf-8 -*-

from odoo import models, fields


class MailActivityType(models.Model):
    _inherit = 'mail.activity.type'

    background_color = fields.Char(string='Background Color')
    short_name = fields.Char(string='Short name')