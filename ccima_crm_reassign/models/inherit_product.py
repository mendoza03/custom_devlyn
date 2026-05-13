# -*- coding: utf-8 -*-
import re
from odoo import models, fields, api, _
from odoo.exceptions import UserError, ValidationError
from odoo.tools.translate import _


class ProductCcima(models.Model):
    _inherit = 'product.template'

    lot = fields.Char(string='Lot')
    surface = fields.Float(string='Surface')
    list_price = fields.Float(string='List Price')
    list_amount = fields.Float(
        string='List Amount',
        compute='_compute_list_amount',
        store=True,
    )
    capital_gains = fields.Float(string='Capital Gains')
    discount = fields.Float(string="Discount")
    net_amount = fields.Float(string="Net Amount")
    down_payment_percent = fields.Float(string="Down Payment %")
    down_payment_amount = fields.Float(string="Down Payment Amount")
    early_payment_percent = fields.Float(string="Early Payment %")
    early_payment_amount = fields.Float(string="Early Payment Amount")
    final_down_payment = fields.Float(string="Final Down Payment")
    amount_to_finance = fields.Float(string="Amount to Finance")
    final_amount = fields.Float(string="Final Amount")
    delivery_date = fields.Date(string="Delivery Date")
    msi = fields.Float(string="MSI")
    monthly_percent_m = fields.Float(string="MS 1%")
    monthly_percent = fields.Float(string="MS 1.25%")
    total_paid = fields.Float(string="Total Paid")
    scheme = fields.Char(string="Scheme")
    client_signature_date = fields.Date(string="Client Signature Date")
    physical_delivery_date = fields.Date(string="Physical Delivery Date")
    legal_representative_signature_date = fields.Date(string="Legal Representative Signature Date")
    contract_delivery_to_client_date = fields.Date(string="Contract Delivery to Client Date")
    notarization_date = fields.Date(string="Notarization Date")
    key = fields.Char(string='Key')
    footage = fields.Char(string='Footage')
    price_unit = fields.Float(string="Price unit")
    month_deliver = fields.Integer(string="Month deliver")
    month_financing = fields.Char(string="Month financing")
    date_deliver = fields.Date(string="Date deliver")
    total_ds = fields.Float(string="total paid")
    second_partner_id = fields.Char(string="Property 2")
    asesor = fields.Many2one('hr.employee',string="Asesor")
    gerente = fields.Many2one('hr.employee', string="Gerente")
    dvn = fields.Many2one('hr.employee', string="DVN")
    publici = fields.Many2one('hr.employee', string="Publicidad")
    cco = fields.Many2one('hr.employee', string="CCO")
    lead = fields.Many2one('crm.lead', string="lead")
    month_0 = fields.Integer(string="Months MSI")
    month_1 = fields.Integer(string="Month 1")
    month_125 = fields.Integer(string="Month 1.25")
    cancel_type_id = fields.Many2one(
        'cancel.types',
        string='Cancel Type',
        copy=False
    )
    x_lead_source_id = fields.Many2one("utm.source", string="Lead Source (Import)")
    t_partner_id = fields.Char(string="Property 2")
    third_partner_id = fields.Char(string="Property 3")
    fourth_partner_id = fields.Char(string="Property 4")
    fifth_partner_id = fields.Char(string="Property 5")
    sixth_partner_id = fields.Char(string="Property 6")
    seventh_partner_id = fields.Char(string="Property 7")
    eighth_partner_id = fields.Char(string="Property 8")
    ninth_partner_id = fields.Char(string="Property 9")
    tenth_partner_id = fields.Char(string="Property 10")
    date_delivery = fields.Date(string="Date delivery")
    date_fist_month = fields.Date(string="Date fist month")
    dvrh = fields.Many2one('hr.employee', string="DVNRH")
    date_digital = fields.Date(string="Date digital")
    date_rl = fields.Date(string="Sign RL")
    state_code = fields.Selection(
        selection=[
            ('qro', 'QRO'),
            ('cdmx', 'CDMX'),
            ('slp', 'SLP'),
        ],
        string='Region',
    )
    no_config = fields.Boolean(
        string="No Config",
        default=False,
    )

    precio_unitario_venta = fields.Float(
        string="Precio Unitario Venta",
        compute="_compute_precio_unitario_venta",
        store=False,
    )

    def _sync_lead_source(self):
        for product in self:
            if product.lead:
                product.lead.write({
                    "source_id": product.x_lead_source_id.id or False,
                })

    @api.depends('property_area', 'price_per_m')
    def _compute_list_amount(self):
        for record in self:
            record.list_amount = (
                (record.property_area or 0.0) *
                (record.price_per_m or 0.0)
            )

    def write(self, vals):
        res = super().write(vals)
        if 'name' in vals:
            for rec in self:
                if rec.carpet_id:
                    rec.carpet_id.name = rec.name

        if "x_lead_source_id" in vals:
            self._sync_lead_source()
        return res


    def _compute_precio_unitario_venta(self):
        SaleOrder = self.env["sale.order"]

        for product in self:
            product.precio_unitario_venta = 0.0

            sale = SaleOrder.search([
                ("order_line.product_template_id", "=", product.id),
                ("finance_id", "!=", False),
            ], order="id desc", limit=1)

            if not sale or not sale.finance_id:
                continue

            finance_line = sale.financial_lines.filtered(
                lambda l: l.interest_id and l.interest_id.id == sale.finance_id.id
            )

            if not finance_line:
                finance_line = sale.financial_lines.filtered(
                    lambda l: l.name == sale.finance_id.name
                )

            if not finance_line or not finance_line[0].promotion_id:
                continue

            finance_line = finance_line[0]
            percent = finance_line.promotion_id.porcent or 0.0

            product.precio_unitario_venta = (
                (product.price_per_m or 0.0) * percent
            )