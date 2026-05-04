# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import ValidationError


class MmRefundRequest(models.Model):
    _name = "mm.refund.request"
    _description = "Refund Request"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    # CUSTOMER
    partner_name = fields.Char(string="Customer Full Name", required=True, tracking=True)
    contact_after = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Contact me later",
        default="no",
        required=True,
        tracking=True,
    )

    # UNIT DATA
    development_name = fields.Char(string="Development", tracking=True)

    reference = fields.Char(string="Reference", tracking=True)
    unit_type = fields.Selection(
        [("ppc", "PPC"), ("pbb", "PBB"), ("lpb", "LPB"), ("cluster", "Cluster"), ("lote", "Lote")],
        string="Unit Type",
        required=True,
        tracking=True,
    )
    meters2 = fields.Float(string="m²", digits=(16, 2), tracking=True)
    unit_amount = fields.Monetary(string="Unit Amount", currency_field="currency_id", tracking=True)
    contract_signed = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Contract Signed",
        default="no",
        required=True,
        tracking=True,
    )

    # REFUND
    apartado_amount = fields.Monetary(string="Apartado", currency_field="currency_id", tracking=True)
    enganche_amount = fields.Monetary(string="Enganche", currency_field="currency_id", tracking=True)

    apartado_payment_date = fields.Date(string="Apartado Payment Date", tracking=True)
    enganche_payment_date = fields.Date(string="Enganche Payment Date", tracking=True)

    apartado_payment_method = fields.Selection(
        [("cash", "Cash"), ("transfer", "Transfer"), ("card", "Card"), ("other", "Other")],
        string="Apartado Payment Method",
        tracking=True,
    )
    enganche_payment_method = fields.Selection(
        [("cash", "Cash"), ("transfer", "Transfer"), ("card", "Card"), ("other", "Other")],
        string="Enganche Payment Method",
        tracking=True,
    )

    apartado_discount = fields.Monetary(string="Apartado Discount", currency_field="currency_id", tracking=True)
    enganche_discount = fields.Monetary(string="Enganche Discount", currency_field="currency_id", tracking=True)

    apartado_real_refund = fields.Monetary(string="Apartado Real Refund", currency_field="currency_id", tracking=True)
    enganche_real_refund = fields.Monetary(string="Enganche Real Refund", currency_field="currency_id", tracking=True)

    total_refund = fields.Monetary(string="Total Refund", currency_field="currency_id", compute="_compute_total", store=True)

    # DOCUMENTATION
    doc_request_signed = fields.Boolean(string="Request signed by customer")
    doc_official_id = fields.Boolean(string="Official ID (INE/Passport/Professional ID w/photo)")
    doc_clabe = fields.Boolean(string="CLABE proof / bank statement cover")
    doc_vouchers = fields.Boolean(string="Deposit receipts (VOUCHER)")
    note = fields.Text(string="Note")
    refund_reason = fields.Text(string="Refund Reason")

    currency_id = fields.Many2one("res.currency", default=lambda self: self.env.company.currency_id.id)

    @api.depends("apartado_real_refund", "enganche_real_refund")
    def _compute_total(self):
        for r in self:
            r.total_refund = (r.apartado_real_refund or 0.0) + (r.enganche_real_refund or 0.0)

    @api.constrains("contract_signed")
    def _check_contract_signed(self):
        for r in self:
            # si quieres bloquear desde el backend
            if r.contract_signed == "no":
                # Comenta si NO quieres bloquear, solo advertir
                pass
