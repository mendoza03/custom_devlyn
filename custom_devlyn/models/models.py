# -*- coding: utf-8 -*-
from odoo import models, api, fields

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Integer(
        string='Employee Number',
        help='Internal numeric identifier for the employee'
    )

    @api.model
    def name_search(self, name="", args=None, operator="ilike", limit=100):
        args = args or []

        if not name:
            return super().name_search(name=name, args=args, operator=operator, limit=limit)

        term = (name or "").strip()
        extra_domain = []

        if term.isdigit():
            extra_domain = expression.OR([
                [("employee_number", "=", term)],
                [("employee_number", "=", int(term))],
            ])

        extra_domain = expression.OR([
            extra_domain,
            [("employee_number", operator, term)],
        ])

        domain = expression.AND([args, extra_domain])

        recs = self.search(domain, limit=limit)
        if recs:
            return recs.name_get()

        return super().name_search(name=name, args=args, operator=operator, limit=limit)