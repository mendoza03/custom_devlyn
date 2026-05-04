# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from num2words import num2words
from decimal import Decimal, ROUND_HALF_UP

# Toggle console prints for debugging
DEBUG_N2W = False
def _p(msg):
    if DEBUG_N2W:
        print(msg)

def _two_digit_to_words_es(n, force_two_digits=True):
    """Spanish words for 0..99 as one number (not digit-by-digit)."""
    _p(f"[N2W][2D] n={n}")
    if n < 0 or n > 99:
        raise ValueError("n must be within 0..99")
    units = ["cero","uno","dos","tres","cuatro","cinco","seis","siete","ocho","nueve"]
    tens = {
        10:"diez", 11:"once", 12:"doce", 13:"trece", 14:"catorce", 15:"quince",
        20:"veinte", 30:"treinta", 40:"cuarenta", 50:"cincuenta",
        60:"sesenta", 70:"setenta", 80:"ochenta", 90:"noventa"
    }
    if n < 10:
        return f"cero {units[n]}" if force_two_digits else units[n]
    if n in tens:
        return tens[n]
    if 16 <= n <= 19:
        return "dieci" + units[n - 10]
    if 21 <= n <= 29:
        return "veinti" + units[n - 20]
    d = (n // 10) * 10
    u = n % 10
    return f"{tens[d]} y {units[u]}"

def number_to_words_punto_es(value, decimal_places=2):
    """
    220.85 -> 'DOSCIENTOS VEINTE PUNTO OCHENTA Y CINCO'
    Solo número, sin unidades. Todo en MAYÚSCULAS.
    """
    _p(f"[N2W] raw={value!r}, dp={decimal_places}")
    if value is None:
        return ""
    from decimal import Decimal, ROUND_HALF_UP
    from num2words import num2words

    fmt = f"1.{'0'*decimal_places}"
    dec = Decimal(str(value)).quantize(Decimal(fmt), rounding=ROUND_HALF_UP)
    sign = "MENOS " if dec < 0 else ""
    dec = abs(dec)

    int_part = int(dec)
    scale = 10 ** decimal_places
    frac_part = int((dec - Decimal(int_part)) * scale)

    int_words = num2words(int_part, lang="es").upper()
    _p(f"[N2W] int_part={int_part} -> {int_words}; frac_part={frac_part}")

    if frac_part == 0:
        res = f"{sign}{int_words}"
        return res.upper()

    # Convertir el decimal completo como número (evita 'ocho cinco')
    if decimal_places == 2 and 0 <= frac_part <= 99:
        frac_words = _two_digit_to_words_es(frac_part, force_two_digits=True)
    else:
        frac_words = num2words(frac_part, lang="es").lower()
        if decimal_places == 2 and frac_part < 10:
            frac_words = "cero " + frac_words

    res = f"{sign}{int_words} punto {frac_words}"
    return res.upper()



class InheritContract(models.Model):
    _inherit = "property.contract"

    # === KEEPING your existing field ===
    property_area_words = fields.Char(
        string="Property Area (m²) Words",
        compute="_compute_numbers_in_words",
    )

    # === New *_words fields ===
    price_per_m_words = fields.Char(string="Price per m (in words)", compute="_compute_numbers_in_words")
    pricing_words = fields.Char(string="Pricing (in words)", compute="_compute_numbers_in_words")
    advance_payment_words = fields.Char(string="Advance Payment (in words)", compute="_compute_numbers_in_words")
    extra_down_payment_words = fields.Char(string="Extra Down Payment (in words)", compute="_compute_numbers_in_words")
    total_amount_to_pay_words = fields.Char(string="Total Amount to Pay (in words)", compute="_compute_numbers_in_words")
    amount_total_words = fields.Char(string="Amount Total (in words)", compute="_compute_numbers_in_words")
    total_interests_to_pay_words = fields.Char(string="Total Interests to Pay (in words)", compute="_compute_numbers_in_words")
    static_total_paid_interests_words = fields.Char(string="Static Total Paid Interests (in words)", compute="_compute_numbers_in_words")
    paid_words = fields.Char(string="Paid (in words)", compute="_compute_numbers_in_words")
    total_paid_interests_words = fields.Char(string="Total Paid Interests (in words)", compute="_compute_numbers_in_words")
    balance_words = fields.Char(string="Balance (in words)", compute="_compute_numbers_in_words")

    cancel_folder_id = fields.Many2one(
        "documents.document",
        string="Cancel Folder",
        help="Documents folder where cancellation evidence is stored."
    )

    cancel_doc_count = fields.Integer(
        compute="_compute_cancel_doc_count",
        string="Cancel Docs",
    )

    currency_id = fields.Many2one(
        "res.currency",
        string="Currency",
        compute="_compute_currency_id",
        store=True,
        readonly=True,
    )

    real_total = fields.Monetary(
        string="Discount Total",
        currency_field="currency_id",
    )

    discount_total = fields.Monetary(
        string="Discount Total",
        compute="_compute_financial_from_sale",
        store=True,
        currency_field="currency_id",
    )
    amount_finance = fields.Monetary(
        string="Amount Finance",
        compute="_compute_financial_from_sale",
        store=True,
        currency_field="currency_id",
    )
    finance_months = fields.Integer(
        string="Finance Months",
        compute="_compute_financial_from_sale",
        store=True,
    )

    documents_count = fields.Integer(
        string="Documents",
        compute="_compute_documents_count",
        store=False,
    )

    def _compute_documents_count(self):
        Doc = self.env['documents.document'].sudo()
        for rec in self:
            rec.documents_count = Doc.search_count([
                ('res_model', '=', 'property.contract'),
                ('res_id', '=', rec.id),
            ])

    def action_open_contract_documents(self):
        self.ensure_one()

        Doc = self.env['documents.document'].sudo()
        docs = Doc.search([('res_model', '=', 'property.contract'), ('res_id', '=', self.id)])

        # Detect folder model
        use_folder_model = True
        try:
            Folder = self.env['documents.folder'].sudo()
        except KeyError:
            use_folder_model = False
            Folder = self.env['documents.document'].sudo()

        contract_folder = False
        folder_name = f"Contract {self.id}"

        if use_folder_model:
            contract_folder = Folder.search([('name', '=', folder_name)], limit=1)
        else:
            contract_folder = Folder.search([('type', '=', 'folder'), ('name', '=', folder_name)], limit=1)


        ctx = dict(self.env.context or {})
        ctx.update({
            'search_default_my_documents': 0,
            'search_default_recent': 0,
            'search_default_is_favorited': 0,
        })
        if contract_folder:
            ctx.update({
                'default_folder_id': contract_folder.id,
                'searchpanel_default_folder_id': contract_folder.id,
            })

        return {
            'type': 'ir.actions.act_window',
            'name': 'Documents',
            'res_model': 'documents.document',
            'view_mode': 'kanban,form',
            'domain': [('res_model', '=', 'property.contract'), ('res_id', '=', self.id)],
            'context': ctx,
        }

    @api.depends("order_id.currency_id")
    def _compute_currency_id(self):
        for rec in self:
            rec.currency_id = rec.order_id.currency_id or rec.env.company.currency_id

    @api.depends(
        "order_id",
        "order_id.finance_id",
        "order_id.finance_id.name",
        "order_id.financial_lines",
        "order_id.financial_lines.name",
        "order_id.financial_lines.discount_total",
        "order_id.financial_lines.amount_finance",
        "order_id.financial_lines.finance_months",
    )
    def _compute_financial_from_sale(self):
        for rec in self:
            rec.discount_total = 0.0
            rec.amount_finance = 0.0
            rec.finance_months = 0

            sale = rec.order_id
            if not sale or not sale.finance_id:
                continue

            target_name = (sale.finance_id.name or "").strip()
            if not target_name:
                continue

            line = sale.financial_lines.filtered(
                lambda l: (l.name or "").strip() == target_name
            )[:1]

            if not line:
                continue

            rec.discount_total = line.discount_total or 0.0
            rec.amount_finance = line.amount_finance or 0.0
            rec.finance_months = int(line.finance_months or 0)



    def _compute_cancel_doc_count(self):
        Doc = self.env["documents.document"].sudo()
        for rec in self:
            if rec.cancel_folder_id:
                rec.cancel_doc_count = Doc.search_count([("folder_id", "=", rec.cancel_folder_id.id)])
            else:
                rec.cancel_doc_count = 0

    def action_open_cancel_documents(self):
        self.ensure_one()

        if not self.cancel_folder_id:
            return {"type": "ir.actions.act_window_close"}

        return {
            "type": "ir.actions.act_window",
            "name": "Cancelaciones",
            "res_model": "documents.document",
            "view_mode": "kanban,list,form",
            "domain": [("folder_id", "=", self.cancel_folder_id.id)],
            "context": {
                "default_folder_id": self.cancel_folder_id.id,
                "searchpanel_default_folder_id": self.cancel_folder_id.id,
            },
            "target": "current",
        }

    def _compute_numbers_in_words(self):
        field_map = [
            ("property_area", "property_area_words"),
            ("price_per_m", "price_per_m_words"),
            ("pricing", "pricing_words"),
            ("advance_payment", "advance_payment_words"),
            ("extra_down_payment", "extra_down_payment_words"),
            ("total_amount_to_pay", "total_amount_to_pay_words"),
            ("amount_total", "amount_total_words"),
            ("total_interests_to_pay", "total_interests_to_pay_words"),
            ("static_total_paid_interests", "static_total_paid_interests_words"),
            ("paid", "paid_words"),
            ("total_paid_interests", "total_paid_interests_words"),
            ("balance", "balance_words"),
        ]
        for rec in self:
            _p(f"[N2W][COMPUTE] rec.id={rec.id}")
            for src, dst in field_map:
                val = getattr(rec, src, None)
                text = number_to_words_punto_es(val, decimal_places=2) if val is not None else ""
                setattr(rec, dst, text)
                _p(f"[N2W][COMPUTE] {src}={val!r} -> {dst}='{text}'")
