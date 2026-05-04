# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class PartnerCcima(models.Model):
    _inherit = 'res.partner'

    @api.depends('is_company')
    def _compute_company_type(self):
        for record in self:
            if not record.company_type:
                record.company_type = 'person'
            elif record.is_company:
                record.company_type = 'company'
            else:
                record.company_type = 'person'



    _sql_constraints = [
        ('unique_email', 'unique(email)', 'Email already exists, must be unique.'),
    ]

    def _normalize_phone(self, phone):
        return re.sub(r'\D', '', phone or '')  # Elimina todo excepto dígitos

    @api.constrains('phone')
    def _check_unique_phone(self):
        for partner in self:
            if partner.phone:
                normalized_phone = self._normalize_phone(partner.phone)
                partners = self.search([])
                for rec in partners:
                    if rec.phone:
                        if rec.id != partner.id and self._normalize_phone(rec.phone) == normalized_phone:
                            raise ValidationError("El Teléfono ya existe para otro contacto.")

