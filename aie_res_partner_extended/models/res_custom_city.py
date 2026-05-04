## -*- coding: utf-8 -*-
from odoo import models, fields

class ResCustomCity(models.Model):
    _name = 'res.custom.city'
    _description = 'Model containing the cities of Mexico'

    name = fields.Char(string='name')
    country_id = fields.Many2one('res.country', string='country')
    state_id = fields.Many2one('res.country.state', string='state')