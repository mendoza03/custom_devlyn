# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo import models, fields


class RentTerm(models.Model):
    """Rent Term"""
    _name = 'rent.term'
    _description = __doc__
    _rec_name = 'name'

    name = fields.Char(string="Name", required=True)
    description = fields.Html(string="Description")
