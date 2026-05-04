# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PropertySalesManagerWeekDetail(models.Model):
    _name = "property.sales.manager.week.detail"
    _description = "Manager Sales Detail by Week"
    _order = "manager_id, week_number"

    manager_summary_id = fields.Many2one(
        "property.sales.manager.summary",
        string="Resumen de Gerente",
        required=True,
        ondelete="cascade",
    )

    manager_id = fields.Many2one(
        "hr.employee",
        string="Gerente",
        related="manager_summary_id.manager_id",
        store=True,
    )

    manager_name = fields.Char(
        string="Gerente",
        related="manager_id.name",
        store=True,
    )

    calendar_id = fields.Many2one(
        "sale.goal.calendar",
        string="Calendario",
        related="manager_summary_id.calendar_id",
        store=True,
    )

    week_number = fields.Integer(
        string="Semana",
        required=True,
    )

    week_name = fields.Char(
        string="Semana",
        compute="_compute_week_name",
        store=True,
    )

    sold_count = fields.Integer(
        string="-",
        default=0,
    )

    sold_amount = fields.Float(
        string="Importe Total",
        default=0.0,
    )

    sold_amount_display = fields.Char(
        string="Importe",
        compute="_compute_amount_display",
        store=True,
    )

    properties_list = fields.Text(
        string="Propiedades",
    )

    company_id = fields.Many2one(
        "res.company",
        string="Company",
        default=lambda self: self.env.company,
    )

    @api.depends("week_number")
    def _compute_week_name(self):
        for record in self:
            if record.week_number:
                record.week_name = f"S{record.week_number}"
            else:
                record.week_name = ""

    @api.depends("sold_amount")
    def _compute_amount_display(self):
        for record in self:
            record.sold_amount_display = f"${record.sold_amount:,.2f}"