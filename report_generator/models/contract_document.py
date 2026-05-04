# -*- coding: utf-8 -*-
from odoo import api, fields, models, _
from odoo.exceptions import UserError
from datetime import date
import re


def _int_to_words_es(n: int) -> str:
    """Simple Spanish number-to-words (0..999,999,999)."""
    n = int(n or 0)

    units = {
        0: "cero", 1: "uno", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco",
        6: "seis", 7: "siete", 8: "ocho", 9: "nueve"
    }
    teens = {
        10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce",
        15: "quince", 16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve"
    }
    tens = {
        20: "veinte", 30: "treinta", 40: "cuarenta", 50: "cincuenta",
        60: "sesenta", 70: "setenta", 80: "ochenta", 90: "noventa"
    }
    hundreds = {
        100: "cien", 200: "doscientos", 300: "trescientos", 400: "cuatrocientos",
        500: "quinientos", 600: "seiscientos", 700: "setecientos", 800: "ochocientos", 900: "novecientos"
    }

    def _0_99(x: int) -> str:
        if x < 10:
            return units[x]
        if 10 <= x <= 19:
            return teens[x]
        if 20 <= x <= 29:
            if x == 20:
                return "veinte"
            map_21_29 = {
                21: "veintiuno", 22: "veintidós", 23: "veintitrés", 24: "veinticuatro",
                25: "veinticinco", 26: "veintiséis", 27: "veintisiete", 28: "veintiocho", 29: "veintinueve",
            }
            return map_21_29[x]
        t = (x // 10) * 10
        u = x % 10
        if u == 0:
            return tens[t]
        return f"{tens[t]} y {units[u]}"

    def _0_999(x: int) -> str:
        if x < 100:
            return _0_99(x)
        if x == 100:
            return "cien"
        h = (x // 100) * 100
        r = x % 100
        if h == 100:
            head = "ciento"
        else:
            head = hundreds[h]
        if r == 0:
            return head
        return f"{head} {_0_99(r)}"

    if n < 1000:
        return _0_999(n)

    if n < 1_000_000:
        k = n // 1000
        r = n % 1000
        if k == 1:
            head = "mil"
        else:
            head = f"{_0_999(k)} mil"
        return head if r == 0 else f"{head} {_0_999(r)}"

    if n < 1_000_000_000:
        m = n // 1_000_000
        r = n % 1_000_000
        if m == 1:
            head = "un millón"
        else:
            head = f"{_int_to_words_es(m)} millones"
        return head if r == 0 else f"{head} {_int_to_words_es(r)}"

    return str(n)


def _float_to_words_es(amount) -> str:
    """Float to Spanish words with 2 decimals like '... con 25/100'."""
    if amount is None or amount is False or amount == "":
        return ""
    try:
        val = float(amount)
    except Exception:
        return ""
    sign = "menos " if val < 0 else ""
    val = abs(val)
    integer_part = int(val)
    cents = int(round((val - integer_part) * 100)) % 100
    words = _int_to_words_es(integer_part)
    return f"{sign}{words} con {cents:02d}/100"



def _fmt_money(amount, decimals=2) -> str:
    """Format number with thousand separators: 1,234,567.89"""
    if amount is None or amount is False or amount == "":
        return ""
    try:
        val = float(amount)
    except Exception:
        return ""
    return f"{val:,.{decimals}f}"



def _fmt_int(amount) -> str:
    """Format integer with thousand separators: 1,234,567"""
    if amount is None or amount is False or amount == "":
        return ""
    try:
        val = int(float(amount))
    except Exception:
        return ""
    return f"{val:,d}"




class ContractDocument(models.Model):
    _name = 'mm.contract.document'
    _description = 'Contract Document (Rendered)'
    _order = 'create_date desc'

    name = fields.Char(required=True, default=lambda self: _("New Contract"))
    template_id = fields.Many2one('mm.contract.template', required=True)
    res_model = fields.Char(required=True)
    res_id = fields.Integer(required=True)

    rendered_header = fields.Html(sanitize=False, readonly=True)
    rendered_body = fields.Html(sanitize=False, readonly=True)
    rendered_footer = fields.Html(sanitize=False, readonly=True)

    # Existing vars
    partner_full_name = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    partner_person_type = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    worksite_name = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    # New vars
    lot_last_digit = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    lot_last_digit_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    property_name = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    lot_prefix_number = fields.Integer(compute="_compute_report_vars", store=False, readonly=True)
    lot_prefix_number_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    surface = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    surface_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    partner_country = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    partner_zip = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    partner_email = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    ine = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    total_finance = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    total_finance_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    total_down_payment = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    total_down_payment_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    total_price = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    total_price_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    monthly_payments = fields.Integer(compute="_compute_report_vars", store=False, readonly=True)
    capital_gain = fields.Float(compute="_compute_report_vars", store=False, readonly=True)

    development_name = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    condominium_name = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )
    vendor_name = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    finance_price = fields.Float(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    finance_price_text = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    cero_percent = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    cero_percent_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    one_percent = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    one_percent_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    one_percent_t = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    one_percent_t_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    zero_per = fields.Char()
    one_per = fields.Char()
    one_t_per = fields.Char()

    current_day_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    current_month_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    current_year_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    current_full_date_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    loan_table_html = fields.Html(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
        sanitize=False,
    )

    internal_fee = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    internal_fee_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    external_fee = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    external_fee_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    additional_amenities = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    additional_amenities_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    month_deliver = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    month_deliver_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    external_initial_maintenance_fee = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    external_initial_maintenance_fee_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    external_amenity_maintenance_fee = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    external_amenity_maintenance_fee_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    external_maximum_maintenance_fee = fields.Float(compute="_compute_report_vars", store=False, readonly=True)
    external_maximum_maintenance_fee_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    date_of_birth = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    place_of_birth = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    occupation = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    phone_number = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    rfc = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    curp = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    official_id_name = fields.Char(compute="_compute_report_vars", store=False, readonly=True)
    official_id_emmisor = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    birth_date_text = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    full_address = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    marital_status = fields.Char(compute="_compute_report_vars", store=False, readonly=True)

    finance_price_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    total_finance_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    total_down_payment_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    total_price_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    internal_fee_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    external_fee_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    additional_amenities_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    cero_percent_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    one_percent_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    one_percent_t_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    monthly_payments_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    month_deliver_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    surface_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    external_initial_maintenance_fee_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    external_amenity_maintenance_fee_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    external_maximum_maintenance_fee_formatted = fields.Char(
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    gender_article = fields.Char(
        string="Gender Article",
        compute="_compute_report_vars",
        store=False,
    )

    gender_label = fields.Char(
        string="Gender label",
        compute="_compute_report_vars",
        store=False,
    )

    deferred_hitch_table_html = fields.Html(
        string="Deferred Hitch Table",
        compute="_compute_report_vars",
        store=False,
    )

    term1_end_month = fields.Char(compute="_compute_report_vars", store=False)
    term2_end_month = fields.Char(compute="_compute_report_vars", store=False)
    term3_end_month = fields.Char(compute="_compute_report_vars", store=False)

    payment_terms_paragraph = fields.Text(
        string="Payment Terms Paragraph",
        compute="_compute_report_vars",
        store=False,
        readonly=True,
    )

    person2_full_name = fields.Char(string="Persona 2 - Nombre completo", compute="_compute_report_vars", store=False)
    person2_official_id = fields.Char(string="Persona 2 - Identificación oficial", compute="_compute_report_vars",
                                      store=False)

    person2_address = fields.Text(string="Persona 2 - Domicilio", compute="_compute_report_vars", store=False)
    person2_street_name = fields.Char(string="Persona 2 - Calle", compute="_compute_report_vars", store=False)
    person2_external_number = fields.Char(string="Persona 2 - Número exterior", compute="_compute_report_vars",
                                          store=False)
    person2_number = fields.Char(string="Persona 2 - Número", compute="_compute_report_vars", store=False)
    person2_internal_number = fields.Char(string="Persona 2 - Número interior", compute="_compute_report_vars",
                                          store=False)
    person2_suburb = fields.Char(string="Persona 2 - Colonia", compute="_compute_report_vars", store=False)
    person2_municipality = fields.Char(string="Persona 2 - Municipio / Ciudad", compute="_compute_report_vars",
                                       store=False)
    person2_state_name = fields.Char(string="Persona 2 - Estado", compute="_compute_report_vars", store=False)
    person2_zip_code = fields.Char(string="Persona 2 - Código postal", compute="_compute_report_vars", store=False)

    person2_lives_in_house = fields.Boolean(string="Persona 2 - Vive en casa", compute="_compute_report_vars",
                                            store=False)
    person2_studies = fields.Char(string="Persona 2 - Estudios", compute="_compute_report_vars", store=False)  # label
    person2_profession = fields.Char(string="Persona 2 - Profesión", compute="_compute_report_vars", store=False)
    person2_marital_status = fields.Char(string="Persona 2 - Estado civil", compute="_compute_report_vars",
                                         store=False)  # label
    person2_phone_number = fields.Char(string="Persona 2 - Teléfono", compute="_compute_report_vars", store=False)
    person2_email = fields.Char(string="Persona 2 - Email", compute="_compute_report_vars", store=False)
    person2_nationality = fields.Char(string="Persona 2 - Nacionalidad", compute="_compute_report_vars", store=False)
    person2_rfc = fields.Char(string="Persona 2 - RFC", compute="_compute_report_vars", store=False)
    person2_curp = fields.Char(string="Persona 2 - CURP", compute="_compute_report_vars", store=False)

    person2_occupation = fields.Char(string="Persona 2 - Ocupación", compute="_compute_report_vars", store=False)
    person2_job_position = fields.Char(string="Persona 2 - Puesto", compute="_compute_report_vars", store=False)
    person2_seniority = fields.Char(string="Persona 2 - Antigüedad", compute="_compute_report_vars", store=False)
    person2_employer_name = fields.Char(string="Persona 2 - Empresa", compute="_compute_report_vars", store=False)
    person2_employer_phone = fields.Char(string="Persona 2 - Teléfono empresa", compute="_compute_report_vars",
                                         store=False)
    person2_employer_address = fields.Char(string="Persona 2 - Domicilio empresa", compute="_compute_report_vars",
                                           store=False)

    person2_place_of_birth = fields.Char(string="Persona 2 - Lugar de nacimiento", compute="_compute_report_vars",
                                         store=False)
    person2_date_of_birth = fields.Date(string="Persona 2 - Fecha de nacimiento", compute="_compute_report_vars",
                                        store=False)
    person2_birth_date_text = fields.Char(string="Persona 2 - Fecha de nacimiento (texto)",
                                          compute="_compute_report_vars", store=False)

    # ------------------------------------------------------------
    # PERSON 3 (ALL COMPUTED BY _compute_report_vars)
    # ------------------------------------------------------------
    person3_full_name = fields.Char(string="Persona 3 - Nombre completo", compute="_compute_report_vars", store=False)
    person3_official_id = fields.Char(string="Persona 3 - Identificación oficial", compute="_compute_report_vars",
                                      store=False)

    person3_address = fields.Text(string="Persona 3 - Domicilio", compute="_compute_report_vars", store=False)
    person3_street_name = fields.Char(string="Persona 3 - Calle", compute="_compute_report_vars", store=False)
    person3_external_number = fields.Char(string="Persona 3 - Número exterior", compute="_compute_report_vars",
                                          store=False)
    person3_number = fields.Char(string="Persona 3 - Número", compute="_compute_report_vars", store=False)
    person3_internal_number = fields.Char(string="Persona 3 - Número interior", compute="_compute_report_vars",
                                          store=False)
    person3_suburb = fields.Char(string="Persona 3 - Colonia", compute="_compute_report_vars", store=False)
    person3_municipality = fields.Char(string="Persona 3 - Municipio / Ciudad", compute="_compute_report_vars",
                                       store=False)
    person3_state_name = fields.Char(string="Persona 3 - Estado", compute="_compute_report_vars", store=False)
    person3_zip_code = fields.Char(string="Persona 3 - Código postal", compute="_compute_report_vars", store=False)

    person3_lives_in_house = fields.Boolean(string="Persona 3 - Vive en casa", compute="_compute_report_vars",
                                            store=False)
    person3_studies = fields.Char(string="Persona 3 - Estudios", compute="_compute_report_vars", store=False)  # label
    person3_profession = fields.Char(string="Persona 3 - Profesión", compute="_compute_report_vars", store=False)
    person3_marital_status = fields.Char(string="Persona 3 - Estado civil", compute="_compute_report_vars",
                                         store=False)  # label
    person3_phone_number = fields.Char(string="Persona 3 - Teléfono", compute="_compute_report_vars", store=False)
    person3_email = fields.Char(string="Persona 3 - Email", compute="_compute_report_vars", store=False)
    person3_nationality = fields.Char(string="Persona 3 - Nacionalidad", compute="_compute_report_vars", store=False)
    person3_rfc = fields.Char(string="Persona 3 - RFC", compute="_compute_report_vars", store=False)
    person3_curp = fields.Char(string="Persona 3 - CURP", compute="_compute_report_vars", store=False)

    person3_occupation = fields.Char(string="Persona 3 - Ocupación", compute="_compute_report_vars", store=False)
    person3_job_position = fields.Char(string="Persona 3 - Puesto", compute="_compute_report_vars", store=False)
    person3_seniority = fields.Char(string="Persona 3 - Antigüedad", compute="_compute_report_vars", store=False)
    person3_employer_name = fields.Char(string="Persona 3 - Empresa", compute="_compute_report_vars", store=False)
    person3_employer_phone = fields.Char(string="Persona 3 - Teléfono empresa", compute="_compute_report_vars",
                                         store=False)
    person3_employer_address = fields.Char(string="Persona 3 - Domicilio empresa", compute="_compute_report_vars",
                                           store=False)

    person3_place_of_birth = fields.Char(string="Persona 3 - Lugar de nacimiento", compute="_compute_report_vars",
                                         store=False)
    person3_date_of_birth = fields.Date(string="Persona 3 - Fecha de nacimiento", compute="_compute_report_vars",
                                        store=False)
    person3_birth_date_text = fields.Char(string="Persona 3 - Fecha de nacimiento (texto)",
                                          compute="_compute_report_vars", store=False)

    person3_applies_assets = fields.Char(string="Persona 3 - Aplica activos", compute="_compute_report_vars",
                                         store=False)

    # ------------------------------------------------------------
    # PERSON 4 (ALL COMPUTED BY _compute_report_vars)
    # ------------------------------------------------------------
    person4_full_name = fields.Char(string="Persona 4 - Nombre completo", compute="_compute_report_vars", store=False)
    person4_official_id = fields.Char(string="Persona 4 - Identificación oficial", compute="_compute_report_vars",
                                      store=False)

    person4_address = fields.Text(string="Persona 4 - Domicilio", compute="_compute_report_vars", store=False)
    person4_street_name = fields.Char(string="Persona 4 - Calle", compute="_compute_report_vars", store=False)
    person4_external_number = fields.Char(string="Persona 4 - Número exterior", compute="_compute_report_vars",
                                          store=False)
    person4_number = fields.Char(string="Persona 4 - Número", compute="_compute_report_vars", store=False)
    person4_internal_number = fields.Char(string="Persona 4 - Número interior", compute="_compute_report_vars",
                                          store=False)
    person4_suburb = fields.Char(string="Persona 4 - Colonia", compute="_compute_report_vars", store=False)
    person4_municipality = fields.Char(string="Persona 4 - Municipio / Ciudad", compute="_compute_report_vars",
                                       store=False)
    person4_state_name = fields.Char(string="Persona 4 - Estado", compute="_compute_report_vars", store=False)
    person4_zip_code = fields.Char(string="Persona 4 - Código postal", compute="_compute_report_vars", store=False)

    person4_lives_in_house = fields.Boolean(string="Persona 4 - Vive en casa", compute="_compute_report_vars",
                                            store=False)
    person4_studies = fields.Char(string="Persona 4 - Estudios", compute="_compute_report_vars", store=False)  # label
    person4_profession = fields.Char(string="Persona 4 - Profesión", compute="_compute_report_vars", store=False)
    person4_marital_status = fields.Char(string="Persona 4 - Estado civil", compute="_compute_report_vars",
                                         store=False)  # label
    person4_phone_number = fields.Char(string="Persona 4 - Teléfono", compute="_compute_report_vars", store=False)
    person4_email = fields.Char(string="Persona 4 - Email", compute="_compute_report_vars", store=False)
    person4_nationality = fields.Char(string="Persona 4 - Nacionalidad", compute="_compute_report_vars", store=False)
    person4_rfc = fields.Char(string="Persona 4 - RFC", compute="_compute_report_vars", store=False)
    person4_rfc_file_name = fields.Char(string="Persona 4 - RFC (archivo nombre)", compute="_compute_report_vars",
                                        store=False)
    person4_curp = fields.Char(string="Persona 4 - CURP", compute="_compute_report_vars", store=False)
    person4_curp_file_name = fields.Char(string="Persona 4 - CURP (archivo nombre)", compute="_compute_report_vars",
                                         store=False)

    person4_occupation = fields.Char(string="Persona 4 - Ocupación", compute="_compute_report_vars", store=False)
    person4_job_position = fields.Char(string="Persona 4 - Puesto", compute="_compute_report_vars", store=False)
    person4_seniority = fields.Char(string="Persona 4 - Antigüedad", compute="_compute_report_vars", store=False)
    person4_employer_name = fields.Char(string="Persona 4 - Empresa", compute="_compute_report_vars", store=False)
    person4_employer_phone = fields.Char(string="Persona 4 - Teléfono empresa", compute="_compute_report_vars",
                                         store=False)
    person4_employer_address = fields.Char(string="Persona 4 - Domicilio empresa", compute="_compute_report_vars",
                                           store=False)

    person4_place_of_birth = fields.Char(string="Persona 4 - Lugar de nacimiento", compute="_compute_report_vars",
                                         store=False)
    person4_date_of_birth = fields.Date(string="Persona 4 - Fecha de nacimiento", compute="_compute_report_vars",
                                        store=False)
    person4_birth_date_text = fields.Char(string="Persona 4 - Fecha de nacimiento (texto)",
                                          compute="_compute_report_vars", store=False)

    person4_applies_assets = fields.Char(string="Persona 4 - Aplica activos", compute="_compute_report_vars",
                                         store=False)

    # ------------------------------------------------------------
    # PERSON 5 (ALL COMPUTED BY _compute_report_vars)
    # ------------------------------------------------------------
    person5_full_name = fields.Char(string="Persona 5 - Nombre completo", compute="_compute_report_vars", store=False)
    person5_official_id = fields.Char(string="Persona 5 - Identificación oficial", compute="_compute_report_vars",
                                      store=False)

    person5_address = fields.Text(string="Persona 5 - Domicilio", compute="_compute_report_vars", store=False)
    person5_street_name = fields.Char(string="Persona 5 - Calle", compute="_compute_report_vars", store=False)
    person5_external_number = fields.Char(string="Persona 5 - Número exterior", compute="_compute_report_vars",
                                          store=False)
    person5_number = fields.Char(string="Persona 5 - Número", compute="_compute_report_vars", store=False)
    person5_internal_number = fields.Char(string="Persona 5 - Número interior", compute="_compute_report_vars",
                                          store=False)
    person5_suburb = fields.Char(string="Persona 5 - Colonia", compute="_compute_report_vars", store=False)
    person5_municipality = fields.Char(string="Persona 5 - Municipio / Ciudad", compute="_compute_report_vars",
                                       store=False)
    person5_state_name = fields.Char(string="Persona 5 - Estado", compute="_compute_report_vars", store=False)
    person5_zip_code = fields.Char(string="Persona 5 - Código postal", compute="_compute_report_vars", store=False)

    person5_lives_in_house = fields.Boolean(string="Persona 5 - Vive en casa", compute="_compute_report_vars",
                                            store=False)
    person5_studies = fields.Char(string="Persona 5 - Estudios", compute="_compute_report_vars", store=False)  # label
    person5_profession = fields.Char(string="Persona 5 - Profesión", compute="_compute_report_vars", store=False)
    person5_marital_status = fields.Char(string="Persona 5 - Estado civil", compute="_compute_report_vars",
                                         store=False)  # label
    person5_phone_number = fields.Char(string="Persona 5 - Teléfono", compute="_compute_report_vars", store=False)
    person5_email = fields.Char(string="Persona 5 - Email", compute="_compute_report_vars", store=False)
    person5_nationality = fields.Char(string="Persona 5 - Nacionalidad", compute="_compute_report_vars", store=False)
    person5_rfc = fields.Char(string="Persona 5 - RFC", compute="_compute_report_vars", store=False)
    person5_rfc_file_name = fields.Char(string="Persona 5 - RFC (archivo nombre)", compute="_compute_report_vars",
                                        store=False)
    person5_curp = fields.Char(string="Persona 5 - CURP", compute="_compute_report_vars", store=False)

    person5_occupation = fields.Char(string="Persona 5 - Ocupación", compute="_compute_report_vars", store=False)
    person5_job_position = fields.Char(string="Persona 5 - Puesto", compute="_compute_report_vars", store=False)
    person5_seniority = fields.Char(string="Persona 5 - Antigüedad", compute="_compute_report_vars", store=False)
    person5_employer_name = fields.Char(string="Persona 5 - Empresa", compute="_compute_report_vars", store=False)
    person5_employer_phone = fields.Char(string="Persona 5 - Teléfono empresa", compute="_compute_report_vars",
                                         store=False)
    person5_employer_address = fields.Char(string="Persona 5 - Domicilio empresa", compute="_compute_report_vars",
                                           store=False)

    person5_place_of_birth = fields.Char(string="Persona 5 - Lugar de nacimiento", compute="_compute_report_vars",
                                         store=False)
    person5_date_of_birth = fields.Date(string="Persona 5 - Fecha de nacimiento", compute="_compute_report_vars",
                                        store=False)
    person5_birth_date_text = fields.Char(string="Persona 5 - Fecha de nacimiento (texto)",
                                          compute="_compute_report_vars", store=False)

    person5_applies_assets = fields.Char(string="Persona 5 - Aplica activos", compute="_compute_report_vars",
                                         store=False)

    datacoopropiedad = fields.Text(
        string="Datos Copropiedad",
        compute="_compute_report_vars",
        store=False,
    )

    official_id_2 = fields.Char(string="Official id")
    official_id_3 = fields.Char(string="Official id")
    official_id_4 = fields.Char(string="Official id")
    official_id_5 = fields.Char(string="Official id")


    @staticmethod
    def _safe_float(val, default=0.0):
        if val in (None, False, ''):
            return float(default)
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        if not s:
            return float(default)
        s = re.sub(r'[^0-9\-,\.]', '', s)
        if ',' in s and '.' in s:
            s = s.replace(',', '')
        else:
            if ',' in s and '.' not in s:
                s = s.replace(',', '.')
        if s.count('.') > 1:
            parts = s.split('.')
            s = parts[0] + '.' + ''.join(parts[1:])
        try:
            return float(s)
        except Exception:
            return float(default)

    def _get_record(self):
        self.ensure_one()
        return self.env[self.res_model].browse(self.res_id).exists()

    @api.depends('res_model', 'res_id')
    def _compute_report_vars(self):
        def _fmt_money(amount, decimals=2) -> str:
            """Format number with thousand separators: 1,234,567.89"""
            if amount in (None, False, ""):
                return ""
            try:
                val = float(amount)
            except Exception:
                return ""
            return f"{val:,.{decimals}f}"

        def _fmt_int(amount) -> str:
            """Format integer with thousand separators: 1,234,567"""
            if amount in (None, False, ""):
                return ""
            try:
                val = int(float(amount))
            except Exception:
                return ""
            return f"{val:,d}"

        def _selection_label(record, field_name, value) -> str:
            """Return selection label for a field/value (or empty string)."""
            if not value:
                return ""
            fld = record._fields.get(field_name)
            if not fld or not getattr(fld, "selection", None):
                return str(value)
            sel = fld.selection(record.env) if callable(fld.selection) else fld.selection
            return dict(sel).get(value, str(value))

        def _build_address(street_name, external_number, suburb, number, municipality, state_name, zip_code,
                           internal_number=None):
            parts = []
            line1 = " ".join([p for p in [street_name, external_number] if p])
            if line1:
                parts.append(line1)

            if internal_number:
                if parts:
                    parts[-1] = f"{parts[-1]} Int. {internal_number}"
                else:
                    parts.append(f"Int. {internal_number}")

            line2 = ", ".join([p for p in [suburb, number] if p])
            if line2:
                parts.append(line2)

            line3 = ", ".join([p for p in [municipality, state_name] if p])
            if line3:
                parts.append(line3)

            if zip_code:
                parts.append(f"C.P. {zip_code}")

            return " - ".join([p for p in parts if p])

        def _dob_to_text(dob_val):
            if not dob_val:
                return ''
            try:
                d = dob_val
                if isinstance(d, str):
                    d = fields.Date.from_string(d)
                if not d:
                    return ''
                return f"{d.day} de {MONTHS_ES.get(d.month, '')} de {d.year}"
            except Exception:
                return ''

        def _build_person_address(street_name, external_number, suburb, number, municipality, state_name, zip_code,
                                  internal_number=''):
            parts = []

            line1 = " ".join([p for p in [street_name, external_number] if p]).strip()
            if line1:
                if internal_number:
                    line1 = f"{line1} Int. {internal_number}"
                parts.append(line1)

            line2 = ", ".join([p for p in [suburb, number] if p]).strip()
            if line2:
                parts.append(line2)

            line3 = ", ".join([p for p in [municipality, state_name] if p]).strip()
            if line3:
                parts.append(line3)

            if zip_code:
                parts.append(f"C.P. {zip_code}")

            return " - ".join([p for p in parts if p])

        def _date_to_text(date_val):
            if not date_val:
                return ""
            try:
                d = date_val
                if isinstance(d, str):
                    d = fields.Date.from_string(d)
                if not d:
                    return ""
                MONTHS_ES = {
                    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
                    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
                    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
                }
                return f"{d.day} de {MONTHS_ES.get(d.month, '')} de {d.year}"
            except Exception:
                return ""

        def _get_char(rec, fname):
            return str(getattr(rec, fname, "") or "").strip()

        def _get_bool(rec, fname):
            return bool(getattr(rec, fname, False))

        def _fill_person_vars(doc, brief, n: int):
            """
            Fill computed vars for person N (2..5) reading from brief fields:
            full_name_N, official_id_N, street_name_N, external_number_N, number_N,
            internal_number_N, suburb_N, municipality_N, state_name_N, zip_code_N, etc.
            """
            suf = f"_{n}"

            full_name = _get_char(brief, f"full_name{suf}")
            official_id = _get_char(brief, f"official_id{suf}")

            street_name = _get_char(brief, f"street_name{suf}")
            external_number = _get_char(brief, f"external_number{suf}")
            number = _get_char(brief, f"number{suf}")
            internal_number = _get_char(brief, f"internal_number{suf}")
            suburb = _get_char(brief, f"suburb{suf}")
            municipality = _get_char(brief, f"municipality{suf}")
            state_name = _get_char(brief, f"state_name{suf}")
            zip_code = _get_char(brief, f"zip_code{suf}")

            # address_N exists for 2/4/5, but for 3 it doesn't (based on your fields)
            address_raw = _get_char(brief, f"address{suf}")
            address_built = _build_address(
                street_name=street_name,
                external_number=external_number,
                suburb=suburb,
                number=number,
                municipality=municipality,
                state_name=state_name,
                zip_code=zip_code,
                internal_number=internal_number,
            )
            address = address_raw or address_built

            lives_in_house = _get_bool(brief, f"lives_in_house{suf}")

            studies_val = getattr(brief, f"studies{suf}", "") or ""
            studies_label = _selection_label(brief, f"studies{suf}", studies_val)

            profession = _get_char(brief, f"profession{suf}")

            marital_val = getattr(brief, f"marital_status{suf}", "") or ""
            marital_label = _selection_label(brief, f"marital_status{suf}", marital_val)

            phone_number = _get_char(brief, f"phone_number{suf}")
            email = _get_char(brief, f"email{suf}")
            nationality = _get_char(brief, f"nationality{suf}")
            rfc = _get_char(brief, f"rfc{suf}")
            curp = _get_char(brief, f"curp{suf}")

            occupation = _get_char(brief, f"occupation{suf}")
            job_position = _get_char(brief, f"job_position{suf}")
            seniority = _get_char(brief, f"seniority{suf}")
            employer_name = _get_char(brief, f"employer_name{suf}")
            employer_phone = _get_char(brief, f"employer_phone{suf}")
            employer_address = _get_char(brief, f"employer_address{suf}")

            place_of_birth = _get_char(brief, f"place_of_birth{suf}")
            dob = getattr(brief, f"date_of_birth{suf}", False) or False
            dob_text = _date_to_text(dob)

            applies_assets = _get_char(brief, f"applies_assets{suf}")  # only meaningful for 3/4/5

            # file name fields (only for 3/4/5 as per your fields)
            address_file_name_3 = _get_char(brief, "address_file_name_3") if n == 3 else ""
            address_file_name_5 = _get_char(brief, "address_file_name_5") if n == 5 else ""
            rfc_file_name_4 = _get_char(brief, "rfc_file_name_4") if n == 4 else ""
            curp_file_name_4 = _get_char(brief, "curp_file_name_4") if n == 4 else ""
            rfc_file_name_5 = _get_char(brief, "rfc_file_name_5") if n == 5 else ""

            # Write to doc fields (you said you already created them)
            setattr(doc, f"person{n}_full_name", full_name)
            setattr(doc, f"person{n}_official_id", official_id)
            setattr(doc, f"person{n}_address", address)

            setattr(doc, f"person{n}_street_name", street_name)
            setattr(doc, f"person{n}_external_number", external_number)
            setattr(doc, f"person{n}_number", number)
            setattr(doc, f"person{n}_internal_number", internal_number)
            setattr(doc, f"person{n}_suburb", suburb)
            setattr(doc, f"person{n}_municipality", municipality)
            setattr(doc, f"person{n}_state_name", state_name)
            setattr(doc, f"person{n}_zip_code", zip_code)

            setattr(doc, f"person{n}_lives_in_house", lives_in_house)
            setattr(doc, f"person{n}_studies", studies_label)
            setattr(doc, f"person{n}_profession", profession)
            setattr(doc, f"person{n}_marital_status", marital_label)
            setattr(doc, f"person{n}_phone_number", phone_number)
            setattr(doc, f"person{n}_email", email)
            setattr(doc, f"person{n}_nationality", nationality)
            setattr(doc, f"person{n}_rfc", rfc)
            setattr(doc, f"person{n}_curp", curp)

            setattr(doc, f"person{n}_occupation", occupation)
            setattr(doc, f"person{n}_job_position", job_position)
            setattr(doc, f"person{n}_seniority", seniority)
            setattr(doc, f"person{n}_employer_name", employer_name)
            setattr(doc, f"person{n}_employer_phone", employer_phone)
            setattr(doc, f"person{n}_employer_address", employer_address)

            setattr(doc, f"person{n}_place_of_birth", place_of_birth)
            setattr(doc, f"person{n}_date_of_birth", dob)
            setattr(doc, f"person{n}_birth_date_text", dob_text)

            # extras (only if your doc has these fields)
            if hasattr(doc, f"person{n}_applies_assets"):
                setattr(doc, f"person{n}_applies_assets", applies_assets)

            # file-name extras (only if your doc has these fields)
            if n == 4 and hasattr(doc, "person4_rfc_file_name"):
                doc.person4_rfc_file_name = rfc_file_name_4
            if n == 4 and hasattr(doc, "person4_curp_file_name"):
                doc.person4_curp_file_name = curp_file_name_4
            if n == 5 and hasattr(doc, "person5_rfc_file_name"):
                doc.person5_rfc_file_name = rfc_file_name_5

        def _fmt_money(amount, decimals=2) -> str:
            """Format number with thousand separators: 1,234,567.89"""
            if amount in (None, False, ""):
                return ""
            try:
                val = float(amount)
            except Exception:
                return ""
            return f"{val:,.{decimals}f}"

        def _fmt_int(amount) -> str:
            """Format integer with thousand separators: 1,234,567"""
            if amount in (None, False, ""):
                return ""
            try:
                val = int(float(amount))
            except Exception:
                return ""
            return f"{val:,d}"

        for doc in self:
            partner_full_name = ''
            partner_person_type = ''
            worksite_name = ''

            lot_last_digit = ''
            lot_last_digit_text = ''
            property_name = ''

            surface = 0.0
            surface_text = ''
            surface_formatted = ''

            partner_country = ''
            partner_zip = ''
            partner_email = ''

            ine = ''

            total_finance = 0.0
            total_finance_text = ''
            total_finance_formatted = ''

            total_down_payment = 0.0
            total_down_payment_text = ''
            total_down_payment_formatted = ''

            total_price = 0.0
            total_price_text = ''
            total_price_formatted = ''

            monthly_payments = 0
            monthly_payments_formatted = ''

            capital_gain = 0.0

            development_name = ''
            condominium_name = ''
            vendor_name = ''

            finance_price = 0.0
            finance_price_text = ''
            finance_price_formatted = ''

            cero_percent = 0.0
            cero_percent_text = ''
            cero_percent_formatted = ''

            one_percent = 0.0
            one_percent_text = ''
            one_percent_formatted = ''

            one_percent_t = 0.0
            one_percent_t_text = ''
            one_percent_t_formatted = ''

            zero_per = '0 %'
            one_per = '1 %'
            one_t_per = '1.5 %'

            current_day_text = ''
            current_month_text = ''
            current_year_text = ''
            current_full_date_text = ''

            loan_table_html = ''
            deferred_hitch_table_html = ''

            internal_fee = 0.0
            internal_fee_text = ''
            internal_fee_formatted = ''

            external_fee = 0.0
            external_fee_text = ''
            external_fee_formatted = ''

            additional_amenities = 0.0
            additional_amenities_text = ''
            additional_amenities_formatted = ''

            month_deliver = ''
            month_deliver_text = ''
            month_deliver_formatted = ''

            external_initial_maintenance_fee = 0.0
            external_initial_maintenance_fee_text = ''
            external_initial_maintenance_fee_formatted = ''

            external_amenity_maintenance_fee = 0.0
            external_amenity_maintenance_fee_text = ''
            external_amenity_maintenance_fee_formatted = ''

            external_maximum_maintenance_fee = 0.0
            external_maximum_maintenance_fee_text = ''
            external_maximum_maintenance_fee_formatted = ''

            date_of_birth = ''
            place_of_birth = ''
            occupation = ''
            phone_number = ''
            rfc = ''
            curp = ''
            official_id_name = ''
            official_id_emmisor = ''

            birth_date_text = ''

            full_address = ''
            marital_status = ''

            gender_article = ''
            gender_label = ''

            term1_end_month = ''
            term2_end_month = ''
            term3_end_month = ''

            payment_terms_paragraph = ''

            # Person 2 defaults
            p2_full_name = ''
            p2_official_id = ''
            p2_address = ''
            p2_street_name = ''
            p2_external_number = ''
            p2_number = ''
            p2_internal_number = ''
            p2_suburb = ''
            p2_municipality = ''
            p2_state_name = ''
            p2_zip_code = ''
            p2_lives_in_house = False
            p2_studies = ''
            p2_profession = ''
            p2_marital_status = ''
            p2_phone_number = ''
            p2_email = ''
            p2_nationality = ''
            p2_rfc = ''
            p2_curp = ''
            p2_occupation = ''
            p2_job_position = ''
            p2_seniority = ''
            p2_employer_name = ''
            p2_employer_phone = ''
            p2_employer_address = ''
            p2_place_of_birth = ''
            p2_date_of_birth = False
            p2_birth_date_text = ''

            # Person 3 defaults
            p3_full_name = ''
            p3_official_id = ''
            p3_address = ''  # (aunque no exista address_3, lo puedes construir)
            p3_street_name = ''
            p3_external_number = ''
            p3_number = ''
            p3_internal_number = ''
            p3_suburb = ''
            p3_municipality = ''
            p3_state_name = ''
            p3_zip_code = ''
            p3_lives_in_house = False
            p3_studies = ''
            p3_profession = ''
            p3_marital_status = ''
            p3_phone_number = ''
            p3_email = ''
            p3_nationality = ''
            p3_rfc = ''
            p3_curp = ''
            p3_occupation = ''
            p3_job_position = ''
            p3_seniority = ''
            p3_employer_name = ''
            p3_employer_phone = ''
            p3_employer_address = ''
            p3_place_of_birth = ''
            p3_date_of_birth = False
            p3_birth_date_text = ''
            p3_applies_assets = ''
            p3_address_file_name = ''

            # Person 4 defaults
            p4_full_name = ''
            p4_official_id = ''
            p4_address = ''
            p4_street_name = ''
            p4_external_number = ''
            p4_number = ''
            p4_internal_number = ''
            p4_suburb = ''
            p4_municipality = ''
            p4_state_name = ''
            p4_zip_code = ''
            p4_lives_in_house = False
            p4_studies = ''
            p4_profession = ''
            p4_marital_status = ''
            p4_phone_number = ''
            p4_email = ''
            p4_nationality = ''
            p4_rfc = ''
            p4_curp = ''
            p4_occupation = ''
            p4_job_position = ''
            p4_seniority = ''
            p4_employer_name = ''
            p4_employer_phone = ''
            p4_employer_address = ''
            p4_place_of_birth = ''
            p4_date_of_birth = False
            p4_birth_date_text = ''
            p4_applies_assets = ''
            p4_rfc_file_name = ''
            p4_curp_file_name = ''

            # Person 5 defaults
            p5_full_name = ''
            p5_official_id = ''
            p5_address = ''
            p5_street_name = ''
            p5_external_number = ''
            p5_number = ''
            p5_internal_number = ''
            p5_suburb = ''
            p5_municipality = ''
            p5_state_name = ''
            p5_zip_code = ''
            p5_lives_in_house = False
            p5_studies = ''
            p5_profession = ''
            p5_marital_status = ''
            p5_phone_number = ''
            p5_email = ''
            p5_nationality = ''
            p5_rfc = ''
            p5_curp = ''
            p5_occupation = ''
            p5_job_position = ''
            p5_seniority = ''
            p5_employer_name = ''
            p5_employer_phone = ''
            p5_employer_address = ''
            p5_place_of_birth = ''
            p5_date_of_birth = False
            p5_birth_date_text = ''
            p5_applies_assets = ''
            p5_address_file_name = ''
            p5_rfc_file_name = ''

            datacoopropiedad = ""
            lot_prefix_number = ""
            lot_prefix_number_text = ""

            def _build_person_text(full_name: str, marital: str, ine_doc: str, ine_number: str) -> str:
                full_name = (full_name or "").strip()
                marital = (marital or "").strip()
                ine_doc = (ine_doc or "").strip()
                ine_number = (ine_number or "").strip()

                if not full_name:
                    return ""

                base = (
                    f"Llamarse {full_name}, ser de nacionalidad mexicana, {marital}, "
                    f"se identifica con documento de identificación personal {ine_doc}"
                )

                if ine_number:
                    base += f" número {ine_number}."
                else:
                    base += "."

                return base

            today = fields.Date.context_today(self)
            if today:
                day = today.day
                month = today.month
                year = today.year

                MONTHS_ES = {
                    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
                    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
                    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
                }

                current_day_text = str(day)
                current_month_text = MONTHS_ES.get(month, '')
                current_year_text = str(year)
                current_full_date_text = f"{day} de {current_month_text} de {year}"

            record = doc._get_record()
            if record:
                if getattr(record, '_name', '') == 'rev.crm.contract.brief':
                    brief = record
                else:
                    brief = getattr(record, 'brief_id', False)

                if brief:
                    partner_full_name = getattr(brief, 'full_name', '') or ''
                    partner_person_type = getattr(brief, 'person_type', '') or ''

                    worksite = getattr(brief, 'worksite_id', False)
                    worksite_name = (getattr(worksite, 'name', '') or '') if worksite else ''
                    development_name = worksite_name

                    condominium = getattr(brief, 'condominium_id', False)
                    condominium_name = (getattr(condominium, 'name', '') or '') if condominium else ''

                    finance_price = doc._safe_float(getattr(brief, 'finance_price', 0.0), default=0.0)
                    finance_price_text = _float_to_words_es(finance_price)
                    finance_price_formatted = _fmt_money(finance_price)

                    cero_percent = doc._safe_float(getattr(brief, 'payments_no_interest', 0.0), default=0.0)
                    cero_percent_text = _float_to_words_es(cero_percent)
                    cero_percent_formatted = _fmt_money(cero_percent)

                    one_percent = doc._safe_float(getattr(brief, 'payments_interest_1', 0.0), default=0.0)
                    one_percent_text = _float_to_words_es(one_percent)
                    one_percent_formatted = _fmt_money(one_percent)

                    one_percent_t = doc._safe_float(getattr(brief, 'payments_interest_1_25', 0.0), default=0.0)
                    one_percent_t_text = _float_to_words_es(one_percent_t)
                    one_percent_t_formatted = _fmt_money(one_percent_t)

                    internal_fee = doc._safe_float(getattr(brief, 'internal_fee', 0.0), default=0.0)
                    internal_fee_text = _float_to_words_es(internal_fee)
                    internal_fee_formatted = _fmt_money(internal_fee)

                    external_fee = doc._safe_float(getattr(brief, 'external_fee', 0.0), default=0.0)
                    external_fee_text = _float_to_words_es(external_fee)
                    external_fee_formatted = _fmt_money(external_fee)

                    additional_amenities = doc._safe_float(getattr(brief, 'additional_amenities', 0.0), default=0.0)
                    additional_amenities_text = _float_to_words_es(additional_amenities)
                    additional_amenities_formatted = _fmt_money(additional_amenities)

                    date_of_birth_val = getattr(brief, 'date_of_birth', False)
                    date_of_birth = str(date_of_birth_val or '').strip()

                    gender_val = getattr(brief, 'gender', '') or ''

                    if gender_val == 'male':
                        gender_article = 'EL'
                        gender_label = 'ÉL'
                    elif gender_val == 'female':
                        gender_article = 'LA'
                        gender_label = 'ELLA'
                    else:
                        gender_article = ''
                        gender_label = ''

                    birth_date_text = ''
                    if date_of_birth_val:
                        try:
                            dob = date_of_birth_val
                            if isinstance(dob, str):
                                dob = fields.Date.from_string(dob)
                            if dob:
                                MONTHS_ES = {
                                    1: 'enero', 2: 'febrero', 3: 'marzo', 4: 'abril',
                                    5: 'mayo', 6: 'junio', 7: 'julio', 8: 'agosto',
                                    9: 'septiembre', 10: 'octubre', 11: 'noviembre', 12: 'diciembre',
                                }
                                birth_date_text = f"{dob.day} de {MONTHS_ES.get(dob.month, '')} de {dob.year}"
                        except Exception:
                            birth_date_text = ''

                    place_of_birth = str(getattr(brief, 'place_of_birth', '') or '').strip()
                    occupation = str(getattr(brief, 'occupation', '') or '').strip()
                    phone_number = str(getattr(brief, 'phone_number', '') or '').strip()
                    rfc = str(getattr(brief, 'rfc', '') or '').strip()
                    curp = str(getattr(brief, 'curp', '') or '').strip()

                    official_id_name = str(getattr(brief, 'official_id_name', '') or '').strip()
                    official_id_emmisor = str(getattr(brief, 'official_id_emmisor', '') or '').strip()

                    street_name = str(getattr(brief, 'street_name', '') or '').strip()
                    external_number = str(getattr(brief, 'external_number', '') or '').strip()
                    suburb = str(getattr(brief, 'suburb', '') or '').strip()
                    number = str(getattr(brief, 'number', '') or '').strip()
                    municipality = str(getattr(brief, 'municipality', '') or '').strip()
                    state_obj = getattr(brief, 'state_rev', False)
                    state_rev = state_obj.name if state_obj else ''
                    city_rev = str(getattr(brief, 'city_rev', '') or '').strip()
                    zip_code = str(getattr(brief, 'zip_code', '') or '').strip()

                    parts = []
                    line1 = " ".join([p for p in [street_name, external_number] if p])
                    if line1:
                        parts.append(line1)

                    line2 = ", ".join([p for p in [suburb, number] if p])
                    if line2:
                        parts.append(line2)

                    line3 = ", ".join([p for p in [municipality, city_rev, state_rev] if p])
                    if line3:
                        parts.append(line3)

                    if zip_code:
                        parts.append(f"C.P. {zip_code}")

                    full_address = " - ".join(parts)

                    lot_raw = getattr(brief, 'lot', '') or ''
                    lot_raw = str(lot_raw).strip()
                    if lot_raw:
                        property_name = re.sub(r'\s*\[.*?\]\s*', '', lot_raw).strip()

                        prefix_match = re.match(r'^(\d{1,3})', property_name)
                        if prefix_match:
                            lot_prefix_number = prefix_match.group(1)
                            lot_prefix_number_text = _int_to_words_es(int(lot_prefix_number))
                        else:
                            lot_prefix_number = False
                            lot_prefix_number_text = False

                    marital_status_val = getattr(brief, 'marital_status', '') or ''
                    MARITAL_MAP = {
                        'soltero': 'SOLTERO',
                        'casado_bienes_separados': 'CASADO BIENES SEPARADOS',
                        'casado_sociedad_conyugal': 'CASADO SOCIEDAD CONYUGAL',
                        'soltera': 'SOLTERA',
                        'casada_bienes_separados': 'CASADA BIENES SEPARADOS',
                        'casada_sociedad_conyugal': 'CASADA SOCIEDAD CONYUGAL',
                    }
                    marital_status = MARITAL_MAP.get(marital_status_val, marital_status_val)

                    surface = self._safe_float(getattr(brief, 'surface', 0.0), default=0.0)
                    surface_text = _float_to_words_es(surface)
                    surface_formatted = _fmt_money(surface)

                    lead = getattr(brief, 'lead_id', False)
                    lead_partner = getattr(lead, 'partner_id', False) if lead else False
                    country = getattr(lead_partner, 'country_id', False) if lead_partner else False
                    partner_country = (getattr(country, 'name', '') or '') if country else ''
                    partner_zip = (getattr(lead_partner, 'zip', '') or '') if lead_partner else ''
                    partner_email = (getattr(lead_partner, 'email', '') or '') if lead_partner else ''
                    vendor_user = getattr(lead, 'user_id', False) if lead else False
                    vendor_name = (getattr(vendor_user, 'name', '') or '') if vendor_user else ''

                    ine_val = getattr(brief, 'official_id', '') or ''
                    ine = str(ine_val).strip() if ine_val not in (False, None) else ''

                    total_finance = doc._safe_float(getattr(brief, 'finance_price', 0.0), default=0.0)
                    total_finance_text = _float_to_words_es(total_finance)
                    total_finance_formatted = _fmt_money(total_finance)

                    total_down_payment = doc._safe_float(getattr(brief, 'total_down_payment', 0.0), default=0.0)
                    total_down_payment_text = _float_to_words_es(total_down_payment)
                    total_down_payment_formatted = _fmt_money(total_down_payment)

                    total_price = doc._safe_float(getattr(brief, 'total_price', 0.0), default=0.0)
                    total_price_text = _float_to_words_es(total_price)
                    total_price_formatted = _fmt_money(total_price)

                    try:
                        monthly_payments = int(getattr(brief, 'term', 0) or 0)
                    except Exception:
                        monthly_payments = 0
                    monthly_payments_formatted = _fmt_int(monthly_payments)

                    capital_gain = self._safe_float(getattr(brief, 'capital_gain', 0.0), default=0.0)

                    sale_order = getattr(brief, 'sale_order_id', False) or getattr(brief, 'sale_oder_id', False)
                    sale_order_id = sale_order.id if sale_order else False

                    term1_end_month = ''
                    term2_end_month = ''
                    term3_end_month = ''

                    if sale_order and sale_order.finance_id:
                        terms = sale_order.finance_id.payment_term_ids or self.env['your.payment.term.model'].browse()
                        terms = terms.sorted(lambda t: (t.end_month is False, t.end_month or 0))

                        def _format_percent(value):
                            if value in (None, False):
                                return None

                            value = float(value) * 100

                            return f"{int(value) if value.is_integer() else value} %"

                        zero_per = '0 %'
                        one_per = '1 %'
                        one_t_per = '1.5 %'

                        if len(terms) > 0:
                            formatted = _format_percent(terms[0].interest)
                            if formatted:
                                zero_per = formatted

                        if len(terms) > 1:
                            formatted = _format_percent(terms[1].interest)
                            if formatted:
                                one_per = formatted

                        if len(terms) > 2:
                            formatted = _format_percent(terms[2].interest)
                            if formatted:
                                one_t_per = formatted

                        top3 = terms[:3]
                        end_months = []
                        for t in top3:
                            v = t.end_month
                            if v in (None, False, ''):
                                end_months.append('')
                            else:
                                try:
                                    end_months.append(str(int(v)))
                                except Exception:
                                    end_months.append(str(v))

                        t1 = 0
                        t2 = 0
                        t3 = 0

                        if sale_order and sale_order.finance_id:
                            terms = sale_order.finance_id.payment_term_ids or self.env[
                                'your.payment.term.model'].browse()
                            terms = terms.sorted(lambda t: (t.end_month is False, t.end_month or 0))

                            top3 = terms[:3]
                            end_months = []
                            for t in top3:
                                v = t.end_month
                                if v in (None, False, ''):
                                    end_months.append('')
                                else:
                                    try:
                                        end_months.append(str(int(v)))
                                    except Exception:
                                        end_months.append(str(v))

                            def _to_int(v):
                                try:
                                    return int(str(v).strip())
                                except Exception:
                                    return 0

                            t1_raw = _to_int(end_months[0]) if len(end_months) > 0 else 0
                            t2_raw = _to_int(end_months[1]) if len(end_months) > 1 else 0
                            t3_raw = _to_int(end_months[2]) if len(end_months) > 2 else 0

                            t1 = max(t1_raw, 0)
                            t2 = max(t2_raw - t1_raw, 0) if t2_raw else 0
                            t3 = max(t3_raw - t2_raw, 0) if t3_raw else 0

                        term1_end_month = str(t1) if t1 else ''
                        term2_end_month = str(t2) if t2 else ''
                        term3_end_month = str(t3) if t3 else ''

                    has_t1 = bool(t1)
                    has_t2 = bool(t2)
                    has_t3 = bool(t3)

                    finance_amount_str = finance_price_formatted or _fmt_money(finance_price)
                    cero_amount_str = cero_percent_formatted or _fmt_money(cero_percent)
                    one_amount_str = one_percent_formatted or _fmt_money(one_percent)
                    one_t_amount_str = one_percent_t_formatted or _fmt_money(one_percent_t)

                    monthly_payments_str = str(monthly_payments or 0)

                    if has_t1 and not has_t2 and not has_t3:
                        payment_terms_paragraph = (
                            f"El Saldo por la cantidad de $ {finance_amount_str} ( {finance_price_text} PESOS XX/100 M.N.), "
                            f"será cubierto en {monthly_payments_str} mensualidades consecutivas, de las cuales las primeras {t1} serán sin intereses, "
                            f"siendo cada una por la cantidad de $ {cero_amount_str} ( {cero_percent_text} PESOS XX/100 M.N.), "
                            f"acordando las partes que “EL COMPRADOR” tendrá que realizar el pago correspondiente a cada mensualidad los primeros 5 días de cada mes, "
                            f"siendo el día 5 la fecha límite para hacer su depósito tal y como se marca en el ANEXO I que forma parte integrante del presente contrato."
                        )

                    elif has_t1 and has_t2 and not has_t3:
                        payment_terms_paragraph = (
                            f"El Saldo por la cantidad de $ {finance_amount_str} ( {finance_price_text} PESOS XX/100 M.N.), "
                            f"será cubierto en {monthly_payments_str} mensualidades consecutivas, de las cuales las primeras {t1} serán sin intereses, "
                            f"siendo cada una por la cantidad de $ {cero_amount_str} ( {cero_percent_text} PESOS XX/100 M.N.), "
                            f"las {t2} siguientes generarán un interés ordinario mensual fijo del {one_per} sobre saldos insolutos siendo cada una por la cantidad de "
                            f"$ {one_amount_str} ( {one_percent_text} PESOS XX/100 M.N.), acordando las partes que “EL COMPRADOR” tendrá que realizar el pago correspondiente "
                            f"a cada mensualidad los primeros 5 días de cada mes, siendo el día 5 la fecha límite para hacer su depósito tal y como se marca en el ANEXO I "
                            f"que forma parte integrante del presente contrato."
                        )

                    elif has_t1 and has_t2 and has_t3:
                        payment_terms_paragraph = (
                            f"El Saldo por la cantidad de $ {finance_amount_str} ( {finance_price_text} PESOS XX/100 M.N.), "
                            f"será cubierto en {monthly_payments_str} mensualidades consecutivas, de las cuales las primeras {t1} serán sin intereses, "
                            f"siendo cada una por la cantidad de $ {cero_amount_str} ( {cero_percent_text} PESOS XX/100 M.N.), "
                            f"las {t2} siguientes generarán un interés ordinario mensual fijo del {one_per} sobre saldos insolutos siendo cada una por la cantidad de "
                            f"$ {one_amount_str} ( {one_percent_text} PESOS XX/100 M.N.), las {t3} siguientes generaran un interés ordinario mensual fijo del {one_t_per} "
                            f"sobre saldos insolutos siendo cada una por la cantidad de $ {one_t_amount_str} ( {one_percent_t_text} PESOS XX/100 M.N.), acordando las partes "
                            f"que “EL COMPRADOR” tendrá que realizar el pago correspondiente a cada mensualidad los primeros 5 días de cada mes, siendo el día 5 la fecha límite "
                            f"para hacer su depósito tal y como se marca en el ANEXO I que forma parte integrante del presente contrato."
                        )
                    else:
                        payment_terms_paragraph = ''



                    tmpl = False
                    if sale_order and sale_order.order_line:
                        first_line = sale_order.order_line[:1]
                        tmpl = first_line.product_template_id if first_line else False

                    if tmpl:
                        external_initial_maintenance_fee = doc._safe_float(
                            getattr(tmpl, 'external_initial_maintenance_fee', 0.0),
                            default=0.0
                        )
                        external_initial_maintenance_fee_text = _float_to_words_es(external_initial_maintenance_fee)
                        external_initial_maintenance_fee_formatted = _fmt_money(external_initial_maintenance_fee)

                        external_amenity_maintenance_fee = doc._safe_float(
                            getattr(tmpl, 'external_amenity_maintenance_fee', 0.0),
                            default=0.0
                        )
                        external_amenity_maintenance_fee_text = _float_to_words_es(external_amenity_maintenance_fee)
                        external_amenity_maintenance_fee_formatted = _fmt_money(external_amenity_maintenance_fee)

                        external_maximum_maintenance_fee = doc._safe_float(
                            getattr(tmpl, 'external_maximum_maintenance_fee', 0.0),
                            default=0.0
                        )
                        external_maximum_maintenance_fee_text = _float_to_words_es(external_maximum_maintenance_fee)
                        external_maximum_maintenance_fee_formatted = _fmt_money(external_maximum_maintenance_fee)

                        month_deliver_val = getattr(tmpl, 'month_deliver', False)
                        month_deliver_num = doc._safe_float(month_deliver_val, default=0.0)
                        if month_deliver_num:
                            month_deliver = int(month_deliver_num)
                            month_deliver_text = _int_to_words_es(int(month_deliver_num))
                            month_deliver_formatted = _fmt_int(month_deliver)
                        else:
                            month_deliver = ''
                            month_deliver_text = ''
                            month_deliver_formatted = ''

                    contract = False
                    if sale_order_id:
                        Contract = self.env['property.contract'].sudo()
                        contract = Contract.search([('order_id', '=', sale_order_id)], limit=1)

                    if contract and contract.loan_line_ids:
                        lines = contract.loan_line_ids.sorted(
                            lambda l: (l.date or fields.Date.from_string('1900-01-01'))
                        )

                        loan_table_html = """
                        <table style="width:100%; border-collapse:collapse; font-size:12px;">
                          <thead>
                            <tr>
                              <th style="border:1px solid #d7d7d7; padding:6px; text-align:center; background:#f3f4f6;">Periodo</th>
                              <th style="border:1px solid #d7d7d7; padding:6px; text-align:left; background:#f3f4f6;">Fecha</th>
                              <th style="border:1px solid #d7d7d7; padding:6px; text-align:right; background:#f3f4f6;">Saldo inicial</th>
                              <th style="border:1px solid #d7d7d7; padding:6px; text-align:right; background:#f3f4f6;">Mensualidad</th>
                              <th style="border:1px solid #d7d7d7; padding:6px; text-align:right; background:#f3f4f6;">Interés</th>
                              <th style="border:1px solid #d7d7d7; padding:6px; text-align:right; background:#f3f4f6;">Abono a capital</th>
                              <th style="border:1px solid #d7d7d7; padding:6px; text-align:right; background:#f3f4f6;">Saldo final</th>
                            </tr>
                          </thead>
                          <tbody>
                        """

                        for ln in lines:
                            periodo = getattr(ln, 'count_line', False)
                            try:
                                periodo = int(periodo) if periodo not in (None, False, '') else ''
                            except Exception:
                                periodo = str(periodo or '').strip()

                            ln_date = getattr(ln, 'date', False)
                            if ln_date:
                                try:
                                    date_str = ln_date.strftime('%d/%m/%Y')
                                except Exception:
                                    date_str = str(ln_date)
                            else:
                                date_str = ''

                            initial_balance = doc._safe_float(getattr(ln, 'initial_balance', 0.0), default=0.0)
                            amount = doc._safe_float(getattr(ln, 'amount', 0.0), default=0.0)
                            interest = doc._safe_float(getattr(ln, 'interest', 0.0), default=0.0)
                            amount_capital = doc._safe_float(getattr(ln, 'amount_capital', 0.0), default=0.0)
                            final_balance = doc._safe_float(getattr(ln, 'final_balance', 0.0), default=0.0)

                            loan_table_html += f"""
                            <tr>
                              <td style="border:1px solid #e5e7eb; padding:6px; text-align:center;">{periodo}</td>
                              <td style="border:1px solid #e5e7eb; padding:6px; text-align:left;">{date_str}</td>
                              <td style="border:1px solid #e5e7eb; padding:6px; text-align:right;">${initial_balance:,.2f}</td>
                              <td style="border:1px solid #e5e7eb; padding:6px; text-align:right;">${amount:,.2f}</td>
                              <td style="border:1px solid #e5e7eb; padding:6px; text-align:right;">${interest:,.2f}</td>
                              <td style="border:1px solid #e5e7eb; padding:6px; text-align:right;">${amount_capital:,.2f}</td>
                              <td style="border:1px solid #e5e7eb; padding:6px; text-align:right;">${final_balance:,.2f}</td>
                            </tr>
                            """

                        loan_table_html += """
                          </tbody>
                        </table>
                        """
                    else:
                        loan_table_html = ''

                    if contract and contract.loan_line_ids:
                        lines = contract.loan_line_ids.sorted(
                            lambda l: (l.date or fields.Date.from_string('1900-01-01')))

                        dh_lines = []
                        for ln in lines:
                            dh = doc._safe_float(getattr(ln, 'difered_hitch', 0.0), default=0.0)
                            if dh > 0:
                                ln_date = getattr(ln, 'date', False)
                                if ln_date:
                                    try:
                                        date_str = ln_date.strftime('%d/%m/%Y')
                                    except Exception:
                                        date_str = str(ln_date)
                                else:
                                    date_str = ''
                                dh_lines.append((date_str, dh))

                        if len(dh_lines) == 1:
                            total_dh = dh_lines[0][1]
                            try:
                                n_months = int(getattr(brief, 'term', 0) or 0)
                            except Exception:
                                n_months = 0

                            if not n_months:
                                n_months = len(lines)

                            if n_months > 1 and total_dh > 0:
                                base_date = getattr(lines[0], 'date', False) or fields.Date.context_today(self)
                                per_month = total_dh / n_months

                                dh_lines = []
                                for i in range(n_months):
                                    d = base_date + relativedelta(months=i)
                                    dh_lines.append((d.strftime('%d/%m/%Y'), per_month))

                        if contract and contract.loan_line_ids:
                            lines = contract.loan_line_ids.sorted(
                                lambda l: (l.date or fields.Date.from_string('1900-01-01'))
                            )

                            dh_lines = []
                            for ln in lines:
                                dh = doc._safe_float(getattr(ln, 'difered_hitch', 0.0), default=0.0)
                                if dh > 0:
                                    ln_date = getattr(ln, 'date', False)
                                    if ln_date:
                                        try:
                                            date_str = ln_date.strftime('%d/%m/%Y')
                                        except Exception:
                                            date_str = str(ln_date)
                                    else:
                                        date_str = ''
                                    dh_lines.append((date_str, dh))

                            if dh_lines:
                                parts = []
                                parts.append('<div style="font-size:12px; line-height:1.4;">')
                                for date_str, amount in dh_lines:
                                    parts.append(
                                        f'<p style="margin:0 0 6px 0;">'
                                        f'La fecha del pago es <strong>{date_str}</strong> por la cantidad de '
                                        f'<strong>${amount:,.2f}</strong>.'
                                        f'</p>'
                                    )
                                parts.append('</div>')
                                deferred_hitch_table_html = ''.join(parts)
                            else:
                                deferred_hitch_table_html = ''
                        else:
                            deferred_hitch_table_html = ''

                    # -----------------------------
                    # PERSON 2
                    # -----------------------------
                    p2_full_name = str(getattr(brief, 'full_name_2', '') or '').strip()
                    p2_official_id = str(getattr(brief, 'official_id_2', '') or '').strip()

                    p2_street_name = str(getattr(brief, 'street_name_2', '') or '').strip()
                    p2_external_number = str(getattr(brief, 'external_number_2', '') or '').strip()
                    p2_number = str(getattr(brief, 'number_2', '') or '').strip()
                    p2_internal_number = str(getattr(brief, 'internal_number_2', '') or '').strip()
                    p2_suburb = str(getattr(brief, 'suburb_2', '') or '').strip()
                    p2_municipality = str(getattr(brief, 'municipality_2', '') or '').strip()
                    p2_state_name = str(getattr(brief, 'state_name_2', '') or '').strip()
                    p2_zip_code = str(getattr(brief, 'zip_code_2', '') or '').strip()

                    p2_address_raw = str(getattr(brief, 'address_2', '') or '').strip()
                    p2_address = p2_address_raw or _build_person_address(
                        p2_street_name, p2_external_number, p2_suburb, p2_number, p2_municipality, p2_state_name,
                        p2_zip_code, p2_internal_number
                    )

                    p2_lives_in_house = bool(getattr(brief, 'lives_in_house_2', False))
                    p2_studies = getattr(brief, 'studies_2', '') or ''
                    p2_profession = str(getattr(brief, 'profession_2', '') or '').strip()
                    p2_marital_status = getattr(brief, 'marital_status_2', '') or ''
                    p2_phone_number = str(getattr(brief, 'phone_number_2', '') or '').strip()
                    p2_email = str(getattr(brief, 'email_2', '') or '').strip()
                    p2_nationality = str(getattr(brief, 'nationality_2', '') or '').strip()
                    p2_rfc = str(getattr(brief, 'rfc_2', '') or '').strip()
                    p2_curp = str(getattr(brief, 'curp_2', '') or '').strip()
                    p2_occupation = str(getattr(brief, 'occupation_2', '') or '').strip()
                    p2_job_position = str(getattr(brief, 'job_position_2', '') or '').strip()
                    p2_seniority = str(getattr(brief, 'seniority_2', '') or '').strip()
                    p2_employer_name = str(getattr(brief, 'employer_name_2', '') or '').strip()
                    p2_employer_phone = str(getattr(brief, 'employer_phone_2', '') or '').strip()
                    p2_employer_address = str(getattr(brief, 'employer_address_2', '') or '').strip()
                    p2_place_of_birth = str(getattr(brief, 'place_of_birth_2', '') or '').strip()
                    p2_date_of_birth = getattr(brief, 'date_of_birth_2', False)
                    p2_birth_date_text = _dob_to_text(p2_date_of_birth)

                    # -----------------------------
                    # PERSON 3
                    # -----------------------------
                    p3_full_name = str(getattr(brief, 'full_name_3', '') or '').strip()
                    p3_official_id = str(getattr(brief, 'official_id_3', '') or '').strip()

                    p3_street_name = str(getattr(brief, 'street_name_3', '') or '').strip()
                    p3_external_number = str(getattr(brief, 'external_number_3', '') or '').strip()
                    p3_number = str(getattr(brief, 'number_3', '') or '').strip()
                    p3_internal_number = str(getattr(brief, 'internal_number_3', '') or '').strip()
                    p3_suburb = str(getattr(brief, 'suburb_3', '') or '').strip()
                    p3_municipality = str(getattr(brief, 'municipality_3', '') or '').strip()
                    p3_state_name = str(getattr(brief, 'state_name_3', '') or '').strip()
                    p3_zip_code = str(getattr(brief, 'zip_code_3', '') or '').strip()

                    # No address_3 in your field list -> build it
                    p3_address = _build_person_address(
                        p3_street_name, p3_external_number, p3_suburb, p3_number, p3_municipality, p3_state_name,
                        p3_zip_code, p3_internal_number
                    )

                    p3_address_file_name = str(getattr(brief, 'address_file_name_3', '') or '').strip()
                    p3_lives_in_house = bool(getattr(brief, 'lives_in_house_3', False))
                    p3_studies = getattr(brief, 'studies_3', '') or ''
                    p3_profession = str(getattr(brief, 'profession_3', '') or '').strip()
                    p3_marital_status = getattr(brief, 'marital_status_3', '') or ''
                    p3_phone_number = str(getattr(brief, 'phone_number_3', '') or '').strip()
                    p3_email = str(getattr(brief, 'email_3', '') or '').strip()
                    p3_nationality = str(getattr(brief, 'nationality_3', '') or '').strip()
                    p3_rfc = str(getattr(brief, 'rfc_3', '') or '').strip()
                    p3_curp = str(getattr(brief, 'curp_3', '') or '').strip()
                    p3_occupation = str(getattr(brief, 'occupation_3', '') or '').strip()
                    p3_job_position = str(getattr(brief, 'job_position_3', '') or '').strip()
                    p3_seniority = str(getattr(brief, 'seniority_3', '') or '').strip()
                    p3_employer_name = str(getattr(brief, 'employer_name_3', '') or '').strip()
                    p3_employer_phone = str(getattr(brief, 'employer_phone_3', '') or '').strip()
                    p3_employer_address = str(getattr(brief, 'employer_address_3', '') or '').strip()
                    p3_place_of_birth = str(getattr(brief, 'place_of_birth_3', '') or '').strip()
                    p3_date_of_birth = getattr(brief, 'date_of_birth_3', False)
                    p3_birth_date_text = _dob_to_text(p3_date_of_birth)
                    p3_applies_assets = str(getattr(brief, 'applies_assets_3', '') or '').strip()

                    # -----------------------------
                    # PERSON 4
                    # -----------------------------
                    p4_full_name = str(getattr(brief, 'full_name_4', '') or '').strip()
                    p4_official_id = str(getattr(brief, 'official_id_4', '') or '').strip()

                    p4_street_name = str(getattr(brief, 'street_name_4', '') or '').strip()
                    p4_external_number = str(getattr(brief, 'external_number_4', '') or '').strip()
                    p4_number = str(getattr(brief, 'number_4', '') or '').strip()
                    p4_internal_number = str(getattr(brief, 'internal_number_4', '') or '').strip()
                    p4_suburb = str(getattr(brief, 'suburb_4', '') or '').strip()
                    p4_municipality = str(getattr(brief, 'municipality_4', '') or '').strip()
                    p4_state_name = str(getattr(brief, 'state_name_4', '') or '').strip()
                    p4_zip_code = str(getattr(brief, 'zip_code_4', '') or '').strip()

                    p4_address_raw = str(getattr(brief, 'address_4', '') or '').strip()
                    p4_address = p4_address_raw or _build_person_address(
                        p4_street_name, p4_external_number, p4_suburb, p4_number, p4_municipality, p4_state_name,
                        p4_zip_code, p4_internal_number
                    )

                    p4_lives_in_house = bool(getattr(brief, 'lives_in_house_4', False))
                    p4_studies = getattr(brief, 'studies_4', '') or ''
                    p4_profession = str(getattr(brief, 'profession_4', '') or '').strip()
                    p4_marital_status = getattr(brief, 'marital_status_4', '') or ''
                    p4_phone_number = str(getattr(brief, 'phone_number_4', '') or '').strip()
                    p4_email = str(getattr(brief, 'email_4', '') or '').strip()
                    p4_nationality = str(getattr(brief, 'nationality_4', '') or '').strip()
                    p4_rfc = str(getattr(brief, 'rfc_4', '') or '').strip()
                    p4_curp = str(getattr(brief, 'curp_4', '') or '').strip()
                    p4_occupation = str(getattr(brief, 'occupation_4', '') or '').strip()
                    p4_job_position = str(getattr(brief, 'job_position_4', '') or '').strip()
                    p4_seniority = str(getattr(brief, 'seniority_4', '') or '').strip()
                    p4_employer_name = str(getattr(brief, 'employer_name_4', '') or '').strip()
                    p4_employer_phone = str(getattr(brief, 'employer_phone_4', '') or '').strip()
                    p4_employer_address = str(getattr(brief, 'employer_address_4', '') or '').strip()
                    p4_place_of_birth = str(getattr(brief, 'place_of_birth_4', '') or '').strip()
                    p4_date_of_birth = getattr(brief, 'date_of_birth_4', False)
                    p4_birth_date_text = _dob_to_text(p4_date_of_birth)
                    p4_applies_assets = str(getattr(brief, 'applies_assets_4', '') or '').strip()

                    p4_rfc_file_name = str(getattr(brief, 'rfc_file_name_4', '') or '').strip()
                    p4_curp_file_name = str(getattr(brief, 'curp_file_name_4', '') or '').strip()

                    # -----------------------------
                    # PERSON 5
                    # -----------------------------
                    p5_full_name = str(getattr(brief, 'full_name_5', '') or '').strip()
                    p5_official_id = str(getattr(brief, 'official_id_5', '') or '').strip()

                    p5_street_name = str(getattr(brief, 'street_name_5', '') or '').strip()
                    p5_external_number = str(getattr(brief, 'external_number_5', '') or '').strip()
                    p5_number = str(getattr(brief, 'number_5', '') or '').strip()
                    p5_internal_number = str(getattr(brief, 'internal_number_5', '') or '').strip()
                    p5_suburb = str(getattr(brief, 'suburb_5', '') or '').strip()
                    p5_municipality = str(getattr(brief, 'municipality_5', '') or '').strip()
                    p5_state_name = str(getattr(brief, 'state_name_5', '') or '').strip()
                    p5_zip_code = str(getattr(brief, 'zip_code_5', '') or '').strip()

                    p5_address_raw = str(getattr(brief, 'address_5', '') or '').strip()
                    p5_address = p5_address_raw or _build_person_address(
                        p5_street_name, p5_external_number, p5_suburb, p5_number, p5_municipality, p5_state_name,
                        p5_zip_code, p5_internal_number
                    )

                    p5_address_file_name = str(getattr(brief, 'address_file_name_5', '') or '').strip()
                    p5_lives_in_house = bool(getattr(brief, 'lives_in_house_5', False))
                    p5_studies = getattr(brief, 'studies_5', '') or ''
                    p5_profession = str(getattr(brief, 'profession_5', '') or '').strip()
                    p5_marital_status = getattr(brief, 'marital_status_5', '') or ''
                    p5_phone_number = str(getattr(brief, 'phone_number_5', '') or '').strip()
                    p5_email = str(getattr(brief, 'email_5', '') or '').strip()
                    p5_nationality = str(getattr(brief, 'nationality_5', '') or '').strip()
                    p5_rfc = str(getattr(brief, 'rfc_5', '') or '').strip()
                    p5_curp = str(getattr(brief, 'curp_5', '') or '').strip()
                    p5_occupation = str(getattr(brief, 'occupation_5', '') or '').strip()
                    p5_job_position = str(getattr(brief, 'job_position_5', '') or '').strip()
                    p5_seniority = str(getattr(brief, 'seniority_5', '') or '').strip()
                    p5_employer_name = str(getattr(brief, 'employer_name_5', '') or '').strip()
                    p5_employer_phone = str(getattr(brief, 'employer_phone_5', '') or '').strip()
                    p5_employer_address = str(getattr(brief, 'employer_address_5', '') or '').strip()
                    p5_place_of_birth = str(getattr(brief, 'place_of_birth_5', '') or '').strip()
                    p5_date_of_birth = getattr(brief, 'date_of_birth_5', False)
                    p5_birth_date_text = _dob_to_text(p5_date_of_birth)
                    p5_applies_assets = str(getattr(brief, 'applies_assets_5', '') or '').strip()

                    p5_rfc_file_name = str(getattr(brief, 'rfc_file_name_5', '') or '').strip()

                    persons_txt = []
                    p1_txt = _build_person_text(
                        full_name=partner_full_name,
                        marital=marital_status,
                        ine_doc=ine,
                        ine_number=official_id_name
                    )
                    if p1_txt:
                        persons_txt.append(p1_txt)

                    if p2_full_name:
                        persons_txt.append(_build_person_text(p2_full_name, p2_marital_status, p2_official_id, ""))
                    if p3_full_name:
                        persons_txt.append(_build_person_text(p3_full_name, p3_marital_status, p3_official_id, ""))
                    if p4_full_name:
                        persons_txt.append(_build_person_text(p4_full_name, p4_marital_status, p4_official_id, ""))
                    if p5_full_name:
                        persons_txt.append(_build_person_text(p5_full_name, p5_marital_status, p5_official_id, ""))

                    datacoopropiedad = "\n\n".join([t for t in persons_txt if t])

            doc.partner_full_name = partner_full_name
            doc.partner_person_type = partner_person_type
            doc.worksite_name = worksite_name

            doc.lot_last_digit = lot_last_digit
            doc.lot_last_digit_text = lot_last_digit_text
            doc.property_name = property_name

            doc.surface = surface
            doc.surface_text = surface_text

            doc.partner_country = partner_country
            doc.partner_zip = partner_zip
            doc.partner_email = partner_email

            doc.ine = ine
            doc.datacoopropiedad = datacoopropiedad

            doc.total_finance = total_finance
            doc.total_finance_text = total_finance_text

            doc.total_down_payment = total_down_payment
            doc.total_down_payment_text = total_down_payment_text

            doc.total_price = total_price
            doc.total_price_text = total_price_text

            doc.monthly_payments = monthly_payments
            doc.capital_gain = capital_gain

            doc.development_name = development_name
            doc.condominium_name = condominium_name

            doc.vendor_name = vendor_name

            doc.finance_price = finance_price
            doc.finance_price_text = finance_price_text

            doc.cero_percent = cero_percent
            doc.cero_percent_text = cero_percent_text

            doc.one_percent = one_percent
            doc.one_percent_text = one_percent_text

            doc.one_percent_t = one_percent_t
            doc.one_percent_t_text = one_percent_t_text

            doc.zero_per = zero_per
            doc.one_per = one_per
            doc.one_t_per = one_t_per

            doc.current_day_text = current_day_text
            doc.current_month_text = current_month_text
            doc.current_year_text = current_year_text
            doc.current_full_date_text = current_full_date_text

            doc.loan_table_html = loan_table_html
            doc.internal_fee = internal_fee
            doc.internal_fee_text = internal_fee_text

            doc.external_fee = external_fee
            doc.external_fee_text = external_fee_text

            doc.additional_amenities = additional_amenities
            doc.additional_amenities_text = additional_amenities_text

            doc.month_deliver = month_deliver
            doc.month_deliver_text = month_deliver_text

            doc.external_initial_maintenance_fee = external_initial_maintenance_fee
            doc.external_initial_maintenance_fee_text = external_initial_maintenance_fee_text

            doc.external_amenity_maintenance_fee = external_amenity_maintenance_fee
            doc.external_amenity_maintenance_fee_text = external_amenity_maintenance_fee_text

            doc.external_maximum_maintenance_fee = external_maximum_maintenance_fee
            doc.external_maximum_maintenance_fee_text = external_maximum_maintenance_fee_text

            doc.date_of_birth = date_of_birth
            doc.place_of_birth = place_of_birth
            doc.occupation = occupation
            doc.phone_number = phone_number
            doc.rfc = rfc
            doc.curp = curp
            doc.official_id_name = official_id_name
            doc.official_id_emmisor = official_id_emmisor

            doc.birth_date_text = birth_date_text

            doc.full_address = full_address
            doc.marital_status = marital_status

            doc.finance_price_formatted = finance_price_formatted
            doc.total_finance_formatted = total_finance_formatted
            doc.total_down_payment_formatted = total_down_payment_formatted
            doc.total_price_formatted = total_price_formatted

            doc.internal_fee_formatted = internal_fee_formatted
            doc.external_fee_formatted = external_fee_formatted
            doc.additional_amenities_formatted = additional_amenities_formatted

            doc.cero_percent_formatted = cero_percent_formatted
            doc.one_percent_formatted = one_percent_formatted
            doc.one_percent_t_formatted = one_percent_t_formatted

            doc.monthly_payments_formatted = monthly_payments_formatted
            doc.month_deliver_formatted = month_deliver_formatted

            doc.surface_formatted = surface_formatted

            doc.external_initial_maintenance_fee_formatted = external_initial_maintenance_fee_formatted
            doc.external_amenity_maintenance_fee_formatted = external_amenity_maintenance_fee_formatted
            doc.external_maximum_maintenance_fee_formatted = external_maximum_maintenance_fee_formatted

            doc.gender_article = gender_article
            doc.gender_label = gender_label

            doc.deferred_hitch_table_html = deferred_hitch_table_html

            doc.term1_end_month = term1_end_month
            doc.term2_end_month = term2_end_month
            doc.term3_end_month = term3_end_month

            doc.payment_terms_paragraph = payment_terms_paragraph

            # PERSON 2
            doc.person2_full_name = p2_full_name
            doc.person2_official_id = p2_official_id
            doc.person2_address = p2_address
            doc.person2_street_name = p2_street_name
            doc.person2_external_number = p2_external_number
            doc.person2_number = p2_number
            doc.person2_internal_number = p2_internal_number
            doc.person2_suburb = p2_suburb
            doc.person2_municipality = p2_municipality
            doc.person2_state_name = p2_state_name
            doc.person2_zip_code = p2_zip_code
            doc.person2_lives_in_house = p2_lives_in_house
            doc.person2_studies = p2_studies
            doc.person2_profession = p2_profession
            doc.person2_marital_status = p2_marital_status
            doc.person2_phone_number = p2_phone_number
            doc.person2_email = p2_email
            doc.person2_nationality = p2_nationality
            doc.person2_rfc = p2_rfc
            doc.person2_curp = p2_curp
            doc.person2_occupation = p2_occupation
            doc.person2_job_position = p2_job_position
            doc.person2_seniority = p2_seniority
            doc.person2_employer_name = p2_employer_name
            doc.person2_employer_phone = p2_employer_phone
            doc.person2_employer_address = p2_employer_address
            doc.person2_place_of_birth = p2_place_of_birth
            doc.person2_date_of_birth = p2_date_of_birth
            doc.person2_birth_date_text = p2_birth_date_text

            # PERSON 3
            doc.person3_full_name = p3_full_name
            doc.person3_official_id = p3_official_id
            doc.person3_address = p3_address
            doc.person3_street_name = p3_street_name
            doc.person3_external_number = p3_external_number
            doc.person3_number = p3_number
            doc.person3_internal_number = p3_internal_number
            doc.person3_suburb = p3_suburb
            doc.person3_municipality = p3_municipality
            doc.person3_state_name = p3_state_name
            doc.person3_zip_code = p3_zip_code
            doc.person3_lives_in_house = p3_lives_in_house
            doc.person3_studies = p3_studies
            doc.person3_profession = p3_profession
            doc.person3_marital_status = p3_marital_status
            doc.person3_phone_number = p3_phone_number
            doc.person3_email = p3_email
            doc.person3_nationality = p3_nationality
            doc.person3_rfc = p3_rfc
            doc.person3_curp = p3_curp
            doc.person3_occupation = p3_occupation
            doc.person3_job_position = p3_job_position
            doc.person3_seniority = p3_seniority
            doc.person3_employer_name = p3_employer_name
            doc.person3_employer_phone = p3_employer_phone
            doc.person3_employer_address = p3_employer_address
            doc.person3_place_of_birth = p3_place_of_birth
            doc.person3_date_of_birth = p3_date_of_birth
            doc.person3_birth_date_text = p3_birth_date_text
            doc.person3_applies_assets = p3_applies_assets

            # PERSON 4
            doc.person4_full_name = p4_full_name
            doc.person4_official_id = p4_official_id
            doc.person4_address = p4_address
            doc.person4_street_name = p4_street_name
            doc.person4_external_number = p4_external_number
            doc.person4_number = p4_number
            doc.person4_internal_number = p4_internal_number
            doc.person4_suburb = p4_suburb
            doc.person4_municipality = p4_municipality
            doc.person4_state_name = p4_state_name
            doc.person4_zip_code = p4_zip_code
            doc.person4_lives_in_house = p4_lives_in_house
            doc.person4_studies = p4_studies
            doc.person4_profession = p4_profession
            doc.person4_marital_status = p4_marital_status
            doc.person4_phone_number = p4_phone_number
            doc.person4_email = p4_email
            doc.person4_nationality = p4_nationality
            doc.person4_rfc = p4_rfc
            doc.person4_rfc_file_name = p4_rfc_file_name
            doc.person4_curp = p4_curp
            doc.person4_curp_file_name = p4_curp_file_name
            doc.person4_occupation = p4_occupation
            doc.person4_job_position = p4_job_position
            doc.person4_seniority = p4_seniority
            doc.person4_employer_name = p4_employer_name
            doc.person4_employer_phone = p4_employer_phone
            doc.person4_employer_address = p4_employer_address
            doc.person4_place_of_birth = p4_place_of_birth
            doc.person4_date_of_birth = p4_date_of_birth
            doc.person4_birth_date_text = p4_birth_date_text
            doc.person4_applies_assets = p4_applies_assets

            # PERSON 5
            doc.person5_full_name = p5_full_name
            doc.person5_official_id = p5_official_id
            doc.person5_address = p5_address
            doc.person5_street_name = p5_street_name
            doc.person5_external_number = p5_external_number
            doc.person5_number = p5_number
            doc.person5_internal_number = p5_internal_number
            doc.person5_suburb = p5_suburb
            doc.person5_municipality = p5_municipality
            doc.person5_state_name = p5_state_name
            doc.person5_zip_code = p5_zip_code
            doc.person5_lives_in_house = p5_lives_in_house
            doc.person5_studies = p5_studies
            doc.person5_profession = p5_profession
            doc.person5_marital_status = p5_marital_status
            doc.person5_phone_number = p5_phone_number
            doc.person5_email = p5_email
            doc.person5_nationality = p5_nationality
            doc.person5_rfc = p5_rfc
            doc.person5_rfc_file_name = p5_rfc_file_name
            doc.person5_curp = p5_curp
            doc.person5_occupation = p5_occupation
            doc.person5_job_position = p5_job_position
            doc.person5_seniority = p5_seniority
            doc.person5_employer_name = p5_employer_name
            doc.person5_employer_phone = p5_employer_phone
            doc.person5_employer_address = p5_employer_address
            doc.person5_place_of_birth = p5_place_of_birth
            doc.person5_date_of_birth = p5_date_of_birth
            doc.person5_birth_date_text = p5_birth_date_text
            doc.person5_applies_assets = p5_applies_assets

            doc.lot_prefix_number = lot_prefix_number
            doc.lot_prefix_number_text = lot_prefix_number_text

    def action_render(self):
        for doc in self:
            record = doc._get_record()
            if not record:
                raise UserError(_("Source record not found."))

            doc._compute_report_vars()
            rendered = doc.template_id.render_all(record, doc=doc)


            doc.write({
                'rendered_header': rendered['header'],
                'rendered_body': rendered['body'],
                'rendered_footer': rendered['footer'],
            })

    def action_print_pdf(self):
        self.ensure_one()
        if not self.rendered_body:
            self.action_render()
        return self.env.ref('report_generator.report_mm_contract_document').report_action(self)
