# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PropertySalesWeekPropertyDetail(models.Model):
    _name = "property.sales.week.property.detail"
    _description = "Property Sales Detail by Week and Property"
    _order = "week_id, property_id"

    week_id = fields.Many2one(
        "property.sales.week.summary",
        string="Semana",
        required=True,
        ondelete="cascade",
    )

    week_name = fields.Char(
        string="Semana",
        related="week_id.name",
        store=True,
    )

    week_number = fields.Integer(
        string="Número de Semana",
        related="week_id.week_number",
        store=True,
    )

    week_number_str = fields.Char(
        string="Semana Nº",
        compute="_compute_week_number_str",
        store=True,
    )

    property_id = fields.Many2one(
        "product.template",
        string="Propiedad",
        required=True,
        ondelete="cascade",
    )

    property_name = fields.Char(
        string="Propiedad",
        related="property_id.name",
        store=True,
    )

    property_ref = fields.Char(
        string="Referencia",
        related="property_id.default_code",
        store=True,
    )

    manager_id = fields.Many2one(
        "hr.employee",
        string="Gerente",
        ondelete="set null",
    )

    manager_name = fields.Char(
        string="Gerente",
        related="manager_id.name",
        store=True,
    )

    cluster_id = fields.Many2one(
        "project.worksite",
        string="Cluster",
        ondelete="set null",
    )

    cluster_name = fields.Char(
        string="Cluster",
        related="cluster_id.name",
        store=True,
    )

    worksite_id = fields.Many2one(
        "project.worksite",
        string="Obra",
        ondelete="set null",
    )

    worksite_name = fields.Char(
        string="Obra",
        related="worksite_id.name",
        store=True,
    )

    calendar_id = fields.Many2one(
        "sale.goal.calendar",
        string="Calendario",
        related="week_id.calendar_id",
        store=True,
    )

    sold_amount = fields.Float(
        string="Importe",
        default=0.0,
    )

    sold_amount_display = fields.Char(
        string="Importe",
        compute="_compute_sold_amount_display",
        store=True,
    )

    state = fields.Selection(
        string="Estado",
        related="property_id.state",
        store=True,
    )

    @api.depends("week_number")
    def _compute_week_number_str(self):
        for record in self:
            record.week_number_str = str(record.week_number) if record.week_number else "0"

    @api.depends("sold_amount")
    def _compute_sold_amount_display(self):
        for record in self:
            record.sold_amount_display = f"${record.sold_amount:,.2f}"