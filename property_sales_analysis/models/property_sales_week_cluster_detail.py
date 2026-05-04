# -*- coding: utf-8 -*-

from odoo import models, fields, api


class PropertySalesWeekClusterDetail(models.Model):
    _name = "property.sales.week.cluster.detail"
    _description = "Property Sales Detail by Week, Cluster and Worksite"
    _order = "week_id, cluster_id, worksite_id"

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
        compute="_compute_week_number",
        store=True,
    )

    week_number_str = fields.Char(
        string="Semana Nº",
        compute="_compute_week_number_str",
        store=True,
    )

    cluster_id = fields.Many2one(
        "project.worksite",
        string="Cluster",
        required=True,
    )

    cluster_name = fields.Char(
        string="Cluster",
        related="cluster_id.name",
        store=True,
    )

    worksite_id = fields.Many2one(
        "project.worksite",
        string="Obra",
        required=True,
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
        compute="_compute_sold_amount_display",
        store=True,
    )

    @api.depends("week_id", "week_id.week_number")
    def _compute_week_number(self):
        for record in self:
            record.week_number = record.week_id.week_number if record.week_id else 0

    @api.depends("sold_amount")
    def _compute_sold_amount_display(self):
        for record in self:
            record.sold_amount_display = f"${record.sold_amount:,.2f}"

    @api.depends("week_number")
    def _compute_week_number_str(self):
        for record in self:
            record.week_number_str = str(record.week_number) if record.week_number else "0"