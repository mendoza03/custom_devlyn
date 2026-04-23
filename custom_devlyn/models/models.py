# -*- coding: utf-8 -*-
from odoo import models, api, fields
from odoo.fields import Domain

class HrEmployee(models.Model):
    _inherit = 'hr.employee'

    employee_number = fields.Integer(
        string='Employee Number',
        help='Internal numeric identifier for the employee'
    )

    def _employee_display_label(self, fallback_name=None):
        self.ensure_one()
        base_name = (self.name or fallback_name or "").strip()
        if self.employee_number not in (False, None, ""):
            if base_name:
                return f"{self.employee_number} - {base_name}"
            return str(self.employee_number)
        return base_name

    @api.depends("name", "employee_number")
    def _compute_display_name(self):
        for record in self:
            record.display_name = record._employee_display_label()

    @api.model
    def name_search(self, name="", domain=None, operator="ilike", limit=100):
        domain = Domain(domain or Domain.TRUE)

        if not name:
            return super().name_search(name=name, domain=domain, operator=operator, limit=limit)

        term = (name or "").strip()
        if term.isdigit():
            search_domain = domain & Domain("employee_number", "=", int(term))
            records = self.search_fetch(search_domain, ["name", "employee_number"], limit=limit)
            if records:
                return [(record.id, record._employee_display_label()) for record in records.sudo()]

        results = super().name_search(name=name, domain=domain, operator=operator, limit=limit)
        if not results:
            return results

        employees = self.search_fetch(
            Domain("id", "in", [record_id for record_id, _label in results]),
            ["name", "employee_number"],
        )
        employees_by_id = {employee.id: employee for employee in employees.sudo()}
        return [
            (
                record_id,
                employees_by_id[record_id]._employee_display_label(fallback_name=label)
                if record_id in employees_by_id
                else label,
            )
            for record_id, label in results
        ]
