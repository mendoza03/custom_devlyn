# -*- coding: utf-8 -*-

from odoo import models, fields, api, _
from odoo.exceptions import UserError


class PropertySalesManagerSummaryGenerator(models.TransientModel):
    _name = "property.sales.manager.summary.generator"
    _description = "Generate Manager Sales Summary"

    calendar_id = fields.Many2one(
        "sale.goal.calendar",
        string="Calendar",
        required=True,
    )

    def action_generate(self):
        """Generate manager summaries for ALL active employees"""
        self.ensure_one()

        # Limpiar usando SQL directo para evitar problemas de foreign keys
        self.env.cr.execute("""
            DELETE FROM property_sales_manager_week_detail
            WHERE calendar_id = %s
        """, (self.calendar_id.id,))

        self.env.cr.execute("""
            DELETE FROM property_sales_manager_summary
            WHERE calendar_id = %s
        """, (self.calendar_id.id,))

        # Obtener TODOS los empleados activos del sistema
        all_managers = self.env["hr.employee"].search([  # CAMBIADO
            ("active", "=", True),
        ], order="name")

        if not all_managers:
            raise UserError(_(
                "No hay empleados activos en el sistema."
            ))

        # Crear un registro por cada gerente (aunque no tengan ventas)
        count = 0
        for manager in all_managers:
            self.env["property.sales.manager.summary"].create({
                "calendar_id": self.calendar_id.id,
                "manager_id": manager.id,
            })
            count += 1

        # Abrir vista de lista
        return {
            "type": "ir.actions.act_window",
            "name": f"Resumen de Gerentes - {self.calendar_id.name} ({count} gerentes)",
            "res_model": "property.sales.manager.summary",
            "view_mode": "list,form",
            "domain": [("calendar_id", "=", self.calendar_id.id)],
            "context": {"create": False},
            "target": "current",
        }