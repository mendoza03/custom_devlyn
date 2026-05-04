# -*- coding: utf-8 -*-
import re
import html as py_html
import html as _html

from odoo import api, fields, models, _
from odoo.exceptions import UserError

TOKEN_RE = re.compile(r"{{\s*([a-zA-Z_][a-zA-Z0-9_\.\-]*)\s*}}")


BROKEN_OPEN = re.compile(r"(\{|&#123;)\s*(?:<[^>]+>\s*)*(\{|&#123;)")
BROKEN_CLOSE = re.compile(r"(\}|&#125;)\s*(?:<[^>]+>\s*)*(\}|&#125;)")
INNER_TAGS = re.compile(r"({{)(.*?)(}})", re.DOTALL)


def _normalize_token_markup(s: str) -> str:

    s = s or ""

    try:
        s = _html.unescape(s)
    except Exception:
        pass

    s = BROKEN_OPEN.sub("{{", s)
    s = BROKEN_CLOSE.sub("}}", s)

    def _strip_inside(m):
        inside = re.sub(r"<[^>]+>", "", m.group(2) or "")
        return "{{" + inside + "}}"

    s = INNER_TAGS.sub(_strip_inside, s)

    s = s.replace("\u200b", "").replace("\ufeff", "")

    return s


class ContractTemplate(models.Model):
    _name = "mm.contract.template"
    _description = "Contract Template (Header/Body/Footer)"
    _order = "name"

    name = fields.Char(required=True)
    active = fields.Boolean(default=True)

    header_html = fields.Html(string="Header", sanitize=False)
    body_html = fields.Html(string="Body", sanitize=False, required=True)
    footer_html = fields.Html(string="Footer", sanitize=False)

    notes = fields.Text()

    fields_help_origin = fields.Text(
        string="Variables y origen de datos",
        compute="_compute_fields_help_origin",
        store=False,
        readonly=True,
    )

    person_type = fields.Selection(
        selection=[
            ('fisica', 'Física'),
            ('moral', 'Moral'),
            ('copropiedad', 'Copropiedad'),
            ('extranjero', 'Extranjero'),
        ],
        string="Person Type",
    )

    def _compute_fields_help_origin(self):
        for doc in self:
            doc.fields_help_origin = "\n".join([
                "=== GUÍA DE VARIABLES ===",
                "",
                "partner_full_name = REV -> full_name (Nombre completo del cliente)",
                "partner_person_type = REV -> person_type (Tipo de persona)",
                "date_of_birth = REV -> date_of_birth (Fecha de nacimiento raw)",
                "birth_date_text = REV -> date_of_birth (Fecha de nacimiento en texto)",
                "place_of_birth = REV -> place_of_birth (Lugar de nacimiento)",
                "occupation = REV -> occupation (Ocupación)",
                "phone_number = REV -> phone_number (Teléfono)",
                "rfc = REV -> rfc (RFC)",
                "curp = REV -> curp (CURP)",
                "official_id_name = REV -> official_id_name (Nombre de identificación oficial)",
                "official_id_emmisor = REV -> official_id_emmisor (Emisor de la identificación)",
                "ine = REV -> official_id (Número de identificación / INE)",
                "marital_status = REV -> marital_status (Estado civil, mapeado a etiqueta)",
                "full_address = REV -> street_name/external_number/suburb/number/municipality/city_rev/state_rev/zip_code (Dirección compuesta)",
                "surface = REV -> surface (Superficie numérica)",
                "surface_text = REV -> surface (Superficie en texto)",
                "",
                "worksite_name = REV -> worksite_id.name (Nombre del desarrollo)",
                "development_name = REV -> worksite_id.name (Alias de worksite_name)",
                "condominium_name = REV -> condominium_id.name (Nombre del condominio)",
                "property_name = REV -> lot (Nombre de la propiedad/lot limpiado)",
                "lot_last_digit = REV -> lot (Último dígito del lot)",
                "lot_last_digit_text = REV -> lot (Último dígito en texto)",
                "",
                "vendor_name = CRM -> user_id.name (Vendedor)",
                "partner_country = Cliente -> partner_id.country_id.name (País del cliente)",
                "partner_zip = Cliente -> partner_id.zip (CP del cliente)",
                "partner_email = Cliente -> partner_id.email (Correo del cliente)",
                "",
                "term1_end_month = configuracion platilla de pago -> finance_id.payment_term_ids[0].end_month (1er término)",
                "term2_end_month = configuracion platilla de pago -> (2do término, ordenado por end_month)",
                "term3_end_month = configuracion platilla de pago -> (3er término, ordenado por end_month)",
                "",
                "external_initial_maintenance_fee = Producto -> Cuota de mantenimiento externo inicial",
                "external_amenity_maintenance_fee = Producto -> Cuota de mantenimiento externo por amenidad",
                "external_maximum_maintenance_fee = Producto -> Cuota de mantenimiento externo máximo",
                "month_deliver = Producto -> mes de entrega",
                "month_deliver_text = Producto -> mes de entrega texto",
                "",
                "finance_price = REV -> Total a financiar",
                "total_down_payment = REV -> Enganche total",
                "total_price = REV -> Precio final",
                "monthly_payments = REV -> term (meses/plazo)",
                "capital_gain = REV -> Plusvalia",
                "",
                "payments / porcentajes (REV):",
                "cero_percent = REV -> Pagos sin intereses (48 meses)",
                "one_percent = REV -> Pagos con 1% interés (72 meses)",
                "one_percent_t = REV -> Pagos con 1.25% interés (60 meses)",
                "zero_per = Texto fijo '0 %'",
                "one_per = Texto fijo '1 %'",
                "one_t_per = Texto fijo '1.5 %'",
                "",
                "loan_table_html = Contrato -> tabla de contrato",
                "deferred_hitch_table_html = Contrato -> enganche diferido",
                "",
                "current_day_text = Fecha actual (día)",
                "current_month_text = Fecha actual (mes en español)",
                "current_year_text = Fecha actual (año)",
                "current_full_date_text = Fecha actual (formato: 'D de mes de A')",
                "",
                "finance_price_formatted = finance_price con formato moneda (1,234.56)",
                "total_finance_formatted = total_finance con formato moneda",
                "total_down_payment_formatted = total_down_payment con formato moneda",
                "total_price_formatted = total_price con formato moneda",
                "internal_fee_formatted = internal_fee con formato moneda",
                "external_fee_formatted = external_fee con formato moneda",
                "additional_amenities_formatted = additional_amenities con formato moneda",
                "cero_percent_formatted = cero_percent con formato moneda",
                "one_percent_formatted = one_percent con formato moneda",
                "one_percent_t_formatted = one_percent_t con formato moneda",
                "monthly_payments_formatted = monthly_payments con separadores (1,234)",
                "month_deliver_formatted = month_deliver con separadores (1,234)",
                "surface_formatted = surface con formato moneda",
                "external_initial_maintenance_fee_formatted = external_initial_maintenance_fee con formato moneda",
                "external_amenity_maintenance_fee_formatted = external_amenity_maintenance_fee con formato moneda",
                "external_maximum_maintenance_fee_formatted = external_maximum_maintenance_fee con formato moneda",
                "",
                "gender_article = REV -> gender (male => 'EL', female => 'LA')",
                "=== PERSONA 2 ===",
                "person2_full_name = Persona 2 -> Nombre completo",
                "person2_official_id = Persona 2 -> Identificación oficial",
                "person2_address = Persona 2 -> Domicilio completo (texto)",
                "person2_street_name = Persona 2 -> Calle",
                "person2_external_number = Persona 2 -> Número exterior",
                "person2_number = Persona 2 -> Número",
                "person2_internal_number = Persona 2 -> Número interior",
                "person2_suburb = Persona 2 -> Colonia",
                "person2_municipality = Persona 2 -> Municipio / Ciudad",
                "person2_state_name = Persona 2 -> Estado",
                "person2_zip_code = Persona 2 -> Código postal",
                "person2_lives_in_house = Persona 2 -> Vive en casa (bool)",
                "person2_studies = Persona 2 -> Estudios (label)",
                "person2_profession = Persona 2 -> Profesión",
                "person2_marital_status = Persona 2 -> Estado civil (label)",
                "person2_phone_number = Persona 2 -> Teléfono",
                "person2_email = Persona 2 -> Email",
                "person2_nationality = Persona 2 -> Nacionalidad",
                "person2_rfc = Persona 2 -> RFC",
                "person2_curp = Persona 2 -> CURP",
                "person2_occupation = Persona 2 -> Ocupación",
                "person2_job_position = Persona 2 -> Puesto",
                "person2_seniority = Persona 2 -> Antigüedad",
                "person2_employer_name = Persona 2 -> Empresa",
                "person2_employer_phone = Persona 2 -> Teléfono empresa",
                "person2_employer_address = Persona 2 -> Domicilio empresa",
                "person2_place_of_birth = Persona 2 -> Lugar de nacimiento",
                "person2_date_of_birth = Persona 2 -> Fecha de nacimiento",
                "person2_birth_date_text = Persona 2 -> Fecha de nacimiento (texto)",
                "",
                "=== PERSONA 3 ===",
                "person3_full_name = Persona 3 -> Nombre completo",
                "person3_official_id = Persona 3 -> Identificación oficial",
                "person3_address = Persona 3 -> Domicilio completo (texto)",
                "person3_street_name = Persona 3 -> Calle",
                "person3_external_number = Persona 3 -> Número exterior",
                "person3_number = Persona 3 -> Número",
                "person3_internal_number = Persona 3 -> Número interior",
                "person3_suburb = Persona 3 -> Colonia",
                "person3_municipality = Persona 3 -> Municipio / Ciudad",
                "person3_state_name = Persona 3 -> Estado",
                "person3_zip_code = Persona 3 -> Código postal",
                "person3_lives_in_house = Persona 3 -> Vive en casa (bool)",
                "person3_studies = Persona 3 -> Estudios (label)",
                "person3_profession = Persona 3 -> Profesión",
                "person3_marital_status = Persona 3 -> Estado civil (label)",
                "person3_phone_number = Persona 3 -> Teléfono",
                "person3_email = Persona 3 -> Email",
                "person3_nationality = Persona 3 -> Nacionalidad",
                "person3_rfc = Persona 3 -> RFC",
                "person3_curp = Persona 3 -> CURP",
                "person3_occupation = Persona 3 -> Ocupación",
                "person3_job_position = Persona 3 -> Puesto",
                "person3_seniority = Persona 3 -> Antigüedad",
                "person3_employer_name = Persona 3 -> Empresa",
                "person3_employer_phone = Persona 3 -> Teléfono empresa",
                "person3_employer_address = Persona 3 -> Domicilio empresa",
                "person3_place_of_birth = Persona 3 -> Lugar de nacimiento",
                "person3_date_of_birth = Persona 3 -> Fecha de nacimiento",
                "person3_birth_date_text = Persona 3 -> Fecha de nacimiento (texto)",
                "person3_applies_assets = Persona 3 -> Aplica activos (texto/label)",
                "",
                "=== PERSONA 4 ===",
                "person4_full_name = Persona 4 -> Nombre completo",
                "person4_official_id = Persona 4 -> Identificación oficial",
                "person4_address = Persona 4 -> Domicilio completo (texto)",
                "person4_street_name = Persona 4 -> Calle",
                "person4_external_number = Persona 4 -> Número exterior",
                "person4_number = Persona 4 -> Número",
                "person4_internal_number = Persona 4 -> Número interior",
                "person4_suburb = Persona 4 -> Colonia",
                "person4_municipality = Persona 4 -> Municipio / Ciudad",
                "person4_state_name = Persona 4 -> Estado",
                "person4_zip_code = Persona 4 -> Código postal",
                "person4_lives_in_house = Persona 4 -> Vive en casa (bool)",
                "person4_studies = Persona 4 -> Estudios (label)",
                "person4_profession = Persona 4 -> Profesión",
                "person4_marital_status = Persona 4 -> Estado civil (label)",
                "person4_phone_number = Persona 4 -> Teléfono",
                "person4_email = Persona 4 -> Email",
                "person4_nationality = Persona 4 -> Nacionalidad",
                "person4_rfc = Persona 4 -> RFC",
                "person4_rfc_file_name = Persona 4 -> RFC (nombre de archivo)",
                "person4_curp = Persona 4 -> CURP",
                "person4_curp_file_name = Persona 4 -> CURP (nombre de archivo)",
                "person4_occupation = Persona 4 -> Ocupación",
                "person4_job_position = Persona 4 -> Puesto",
                "person4_seniority = Persona 4 -> Antigüedad",
                "person4_employer_name = Persona 4 -> Empresa",
                "person4_employer_phone = Persona 4 -> Teléfono empresa",
                "person4_employer_address = Persona 4 -> Domicilio empresa",
                "person4_place_of_birth = Persona 4 -> Lugar de nacimiento",
                "person4_date_of_birth = Persona 4 -> Fecha de nacimiento",
                "person4_birth_date_text = Persona 4 -> Fecha de nacimiento (texto)",
                "person4_applies_assets = Persona 4 -> Aplica activos (texto/label)",
                "",
                "=== PERSONA 5 ===",
                "person5_full_name = Persona 5 -> Nombre completo",
                "person5_official_id = Persona 5 -> Identificación oficial",
                "person5_address = Persona 5 -> Domicilio completo (texto)",
                "person5_street_name = Persona 5 -> Calle",
                "person5_external_number = Persona 5 -> Número exterior",
                "person5_number = Persona 5 -> Número",
                "person5_internal_number = Persona 5 -> Número interior",
                "person5_suburb = Persona 5 -> Colonia",
                "person5_municipality = Persona 5 -> Municipio / Ciudad",
                "person5_state_name = Persona 5 -> Estado",
                "person5_zip_code = Persona 5 -> Código postal",
                "person5_lives_in_house = Persona 5 -> Vive en casa (bool)",
                "person5_studies = Persona 5 -> Estudios (label)",
                "person5_profession = Persona 5 -> Profesión",
                "person5_marital_status = Persona 5 -> Estado civil (label)",
                "person5_phone_number = Persona 5 -> Teléfono",
                "person5_email = Persona 5 -> Email",
                "person5_nationality = Persona 5 -> Nacionalidad",
                "person5_rfc = Persona 5 -> RFC",
                "person5_rfc_file_name = Persona 5 -> RFC (nombre de archivo)",
                "person5_curp = Persona 5 -> CURP",
                "person5_occupation = Persona 5 -> Ocupación",
                "person5_job_position = Persona 5 -> Puesto",
                "person5_seniority = Persona 5 -> Antigüedad",
                "person5_employer_name = Persona 5 -> Empresa",
                "person5_employer_phone = Persona 5 -> Teléfono empresa",
                "person5_employer_address = Persona 5 -> Domicilio empresa",
                "person5_place_of_birth = Persona 5 -> Lugar de nacimiento",
                "person5_date_of_birth = Persona 5 -> Fecha de nacimiento",
                "person5_birth_date_text = Persona 5 -> Fecha de nacimiento (texto)",
                "person5_applies_assets = Persona 5 -> Aplica activos (texto/label)",

                "datacoopropiedad = Rev -> optine texto de las personas agregadas (texto)",
            ])

    def _get_alias_map(self, record):

        if getattr(record, "_name", "") == "rev.crm.contract.brief":
            brief = record
        else:
            brief = getattr(record, "brief_id", False)

        aliases = {
            "buyer_name": (getattr(brief, "full_name", "") or "") if brief else "",
            "person_type": (getattr(brief, "person_type", "") or "") if brief else "",
            "worksite_name": (getattr(getattr(brief, "worksite_id", False), "name", "") or "") if brief else "",
        }

        return aliases

    def _get_token_value(self, record, token, doc=None):

        if doc:
            obj = doc
            ok = True
            for part in token.split("."):
                if not obj or not hasattr(obj, part):
                    ok = False
                    break
                obj = getattr(obj, part)

            if ok:
                return "" if obj in (False, None) else str(obj)

        alias_map = self._get_alias_map(record)
        if token in alias_map:
            return alias_map[token] or ""

        obj = record
        for part in token.split("."):
            if not obj or not hasattr(obj, part):
                return ""
            obj = getattr(obj, part)

        if obj in (False, None):
            return ""

        if hasattr(obj, "ids") and hasattr(obj, "_name"):
            if not obj:
                return ""
            if len(obj) > 1:
                return ", ".join(obj.mapped("display_name"))
            return obj.display_name or ""

        return str(obj)

    def _render_html_with_tokens(self, html_template, record, doc=None):
        normalized = _normalize_token_markup(html_template or "")
        tokens = TOKEN_RE.findall(normalized or "")

        RAW_TOKENS = {"loan_table_html", "deferred_hitch_table_html"}

        def _repl(match):
            token = (match.group(1) or "").strip()
            val = self._get_token_value(record, token, doc=doc)

            if token in RAW_TOKENS:
                return val or ""

            if token == "datacoopropiedad":
                safe = py_html.escape(val or "")
                return safe.replace("\r\n", "\n").replace("\r", "\n").replace("\n", "<br/>")

            return py_html.escape(val or "")

        result = TOKEN_RE.sub(_repl, normalized or "")
        return result

    def render_all(self, record, doc=None):

        return {
            "header": self._render_html_with_tokens(self.header_html or "", record, doc=doc),
            "body": self._render_html_with_tokens(self.body_html or "", record, doc=doc),
            "footer": self._render_html_with_tokens(self.footer_html or "", record, doc=doc),
        }
