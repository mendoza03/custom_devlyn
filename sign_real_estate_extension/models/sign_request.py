# -*- coding: utf-8 -*-
from odoo import models, fields  # type: ignore
from num2words import num2words


class SignRequestRealEstate(models.Model):
    _inherit = 'sign.request'

    opportunity_id = fields.Many2one('crm.lead', string='Opportunity')
    sale_order_id = fields.Many2one('sale.order', string='Quotation')
    finance_time = fields.Selection(
        [('10', '10'), ('15', '15'), ('20', '20')],
        string='financing modality',
        default='10',
    )
    property_contract_id = fields.Many2one(
        'property.contract',
        string='Property Contract',
    )

    def to_words(self, val):
        return num2words(val or 0, lang='es').replace("coma", "punto")

    def _to_words(self, val):
        return num2words(val or 0, lang='es').replace("coma", "punto")

    def _format_amount_words(self, value):
        if value is None:
            value = 0
        return num2words(value, lang='es').replace("coma", "punto")

    def _write_user_values_from_partner_values(self, values):
        self.ensure_one()
        user = getattr(self.opportunity_id, 'user_id', False)
        if not user or not user.partner_id:
            return
        to_write = {k: v for k, v in values.items() if k in user.partner_id._fields}
        if to_write:
            user.partner_id.write(to_write)

    def _build_loan_lines_text(self, contract):
        if not contract or not hasattr(contract, 'loan_line_ids'):
            return ''

        def _fw(val, width):
            s = '' if val is None else str(val)
            return s[:width].ljust(width)

        lines = []
        header = f"{_fw('No.', 4)} {_fw('Date', 10)} {_fw('Amount', 18)} Name"
        lines.append(header)

        for idx, line in enumerate(contract.loan_line_ids, start=1):
            date_val = getattr(line, 'date', None) or getattr(line, 'due_date', None) or getattr(line, 'payment_date',
                                                                                                 None) or ''

            try:
                date_str = date_val.strftime('%Y-%m-%d')
            except Exception:
                date_str = str(date_val)

            name_val = getattr(line, 'name', None) or getattr(line, 'description', None) or ''
            amount_val = (
                    getattr(line, 'amount', None)
                    or getattr(line, 'amount_total', None)
                    or getattr(line, 'installment_amount', None)
                    or getattr(line, 'move_amount', None)
                    or 0.0
            )
            try:
                amount_num = float(amount_val or 0.0)
            except Exception:
                amount_num = 0.0

            amount_str = f"{amount_num:,.2f} ({self._format_amount_words(amount_num)})"

            row = f"{_fw(idx, 4)} {_fw(date_str, 10)} {_fw(amount_str, 18)} {name_val}"
            lines.append(row)

        return "\n".join(lines)

    def _split_full_name(self, full_name):
        raw = (full_name or '').strip()
        if not raw:
            return '', '', ''
        parts = [p for p in raw.split(' ') if p]
        if len(parts) >= 3:
            paterno = parts[-1]
            materno = parts[-2]
            nombres = ' '.join(parts[:-2])
        elif len(parts) == 2:
            nombres = parts[0]
            materno = ''
            paterno = parts[1]
        else:
            nombres = parts[0]
            materno = ''
            paterno = ''
        return nombres, materno, paterno

    def _to_float(self, val):
        if val in (None, False, ''):
            return 0.0
        if isinstance(val, (int, float)):
            return float(val)
        s = str(val).strip()
        s = s.replace('$', '').replace(',', '').replace(' ', '')
        try:
            return float(s)
        except Exception:
            return 0.0

    def _to_int(self, val):
        if val in (None, False, ''):
            return 0
        if isinstance(val, (int, float)):
            return int(val)
        s = str(val).strip()
        s = s.replace('$', '').replace(',', '').replace(' ', '')
        try:
            return int(float(s))
        except Exception:
            return 0

    def _coerce_partner_values(self, partner, values):
        out = {}
        for k, v in values.items():
            f = partner._fields.get(k)
            if not f:
                continue
            t = getattr(f, 'type', '')
            if t in ('float', 'monetary'):
                out[k] = self._to_float(v)
            elif t == 'integer':
                out[k] = self._to_int(v)
            else:
                out[k] = v
        return out

    def update_partner_id_property_values(self):
        self.ensure_one()

        sale_order = self.sale_order_id
        partner = sale_order.partner_id if sale_order and sale_order.partner_id else getattr(self, 'partner_id', False)
        property_contract = self.property_contract_id
        property_id = getattr(property_contract, 'property_id', False) or getattr(sale_order, 'property_id', False)
        condominium_id = getattr(property_id, 'condominium_id', False)
        finance_id = getattr(self, 'finance_id', False) or getattr(sale_order, 'finance_id', False)
        financial_line_0 = getattr(finance_id, 'financial_line_0', False)

        vat_amount = getattr(sale_order, 'amount_tax', 0.0) if sale_order else 0.0
        #untaxed_amount = getattr(sale_order, 'amount_untaxed', 0.0) if sale_order else 0.0
        maintenance_fee = getattr(property_contract, 'maintenance_fee', 0.0) if property_contract else 0.0

        att_name = False
        att_url = False

        dev_crm = getattr(property_contract, 'developer_crm_id', False) or getattr(sale_order, 'developer_crm_id',
                                                                                   False)

        cb = getattr(self.opportunity_id, "contract_brief_id", False)

        first_names_client, last_name_materno_client, last_name_paterno_client = ('', '', '')
        if cb and getattr(cb, 'full_name', False):
            first_names_client, last_name_materno_client, last_name_paterno_client = self._split_full_name(cb.full_name)
        hitch_num = self._to_float(getattr(cb, 'total_down_payment', 0.0) if cb else 0.0)

        prod = sale_order.order_line[0].product_id
        pricenod = getattr(prod, 'final_amount', 0.0) if prod else 0.0
        paybef = getattr(prod, 'early_payment_amount', 0.0) if prod else 0.0
        if paybef > 0:
            untaxed_amount = pricenod + paybef
        else:
            untaxed_amount = getattr(sale_order, 'amount_untaxed', 0.0) if sale_order else 0.0

        values = {
            'property_name': getattr(cb, 'lot', False) if cb else False,
            'property_lot': (getattr(cb, 'lot', '') or '')[:1],
            'property_footage': getattr(cb, 'surface', False) if cb else False,
            'property_amount': getattr(cb, 'total_price', False) if cb else False,
            'property_internal_code': getattr(property_id, 'default_code', False),
            'condominium_name': (getattr(cb, 'condominium_id', False) and getattr(cb.condominium_id, 'name',
                                                                                  False)) if cb else False,

            'monthly_payments_1_to_48': getattr(cb, 'payments_no_interest', False) if cb else False,
            'monthly_payments_49_to_120': getattr(cb, 'payments_interest_1', False) if cb else False,
            'monthly_payments_121_to_180': getattr(cb, 'payments_interest_1_25', False) if cb else False,
            'monthly_payments_181_to_240': getattr(cb, 'payments_interest_1_25', False) if cb else False,

            'amount_finance': (
                self.sale_order_id.financial_lines[0].amount_finance
                if self.sale_order_id and self.sale_order_id.financial_lines
                else 0.0
            ),
            'hitch': getattr(cb, 'total_down_payment', 0.0) if cb else 0.0,
            'hitch_text':  self._to_words(hitch_num),
            'finance_months': getattr(cb, 'term', 0) if cb else 0,
            'total_sale_amount': getattr(sale_order, 'amount_total', 0.0) if sale_order else 0.0,

            'monthly_payments_1_to_48_text': self._to_words(self._to_float(getattr(cb, 'payments_no_interest', 0.0)) if cb else 0.0),
            'monthly_payments_49_to_120_text': self._to_words(self._to_float(getattr(cb, 'payments_interest_1', 0.0)) if cb else 0.0),
            'monthly_payments_121_to_180_text': self._to_words(self._to_float(getattr(cb, 'payments_interest_1_25', 0.0)) if cb else 0.0),
            'monthly_payments_181_to_240_text': self._to_words(self._to_float(getattr(cb, 'payments_interest_1_25', 0.0)) if cb else 0.0),



            'loan_lines_text': getattr(self, '_build_loan_lines_text', lambda *a, **k: '')(property_contract),

            'property_attachment_1_name': att_name,
            'property_attachment_1_url': att_url,

            'vat_amount': vat_amount,
            'vat_amount_text': self._to_words(vat_amount),
            'total_without_tax': untaxed_amount,
            'total_without_tax_text': self._to_words(untaxed_amount),
            'maintenance_fee': maintenance_fee,
            'maintenance_fee_text': self._to_words(maintenance_fee),

            'property_footage_text': self._to_words(getattr(property_id, 'property_area', 0.0) or 0.0),
            'property_lot_text': self._to_words(
                float(getattr(property_id, 'terrain_type', 0.0)) if str(
                    getattr(property_id, 'terrain_type', 0.0)).replace('.', '', 1).isdigit() else 0.0
            ),

            'property_pricing': getattr(property_contract, 'pricing', 0.0) if property_contract else 0.0,
            'property_pricing_text': self._to_words(
                getattr(property_contract, 'pricing', 0.0) if property_contract else 0.0),

            'related_public_deeds': getattr(dev_crm, 'related_public_deeds', False) if dev_crm else False,
            'recent_public_deed': getattr(dev_crm, 'recent_public_deed', False) if dev_crm else False,
            'otherwise_clause': getattr(dev_crm, 'otherwise_clause', False) if dev_crm else False,
            'compliance_clause': getattr(dev_crm, 'compliance_clause', False) if dev_crm else False,
            'company_legal_name': getattr(dev_crm, 'company_legal_name', False) if dev_crm else False,
            'company_legal_rep': getattr(dev_crm, 'company_legal_rep', False) if dev_crm else False,
            'company_constitutive_act': getattr(dev_crm, 'company_constitutive_act', False) if dev_crm else False,
            'company_notary': getattr(dev_crm, 'company_notary', False) if dev_crm else False,
            'company_address': getattr(dev_crm, 'company_address', False) if dev_crm else False,
            'company_email': getattr(dev_crm, 'company_email', False) if dev_crm else False,

            'partner_related_public_deeds': getattr(dev_crm, 'partner_related_public_deeds',
                                                    False) if dev_crm else False,
            'partner_recent_public_deed': getattr(dev_crm, 'partner_recent_public_deed', False) if dev_crm else False,
            'partner_legal_name': getattr(dev_crm, 'partner_legal_name', False) if dev_crm else False,
            'partner_legal_representative': getattr(dev_crm, 'partner_legal_representative',
                                                    False) if dev_crm else False,
            'partner_constitutive_deed': getattr(dev_crm, 'partner_constitutive_deed', False) if dev_crm else False,
            'partner_current_notary': getattr(dev_crm, 'partner_current_notary', False) if dev_crm else False,
            'partner_registered_address': getattr(dev_crm, 'partner_registered_address', False) if dev_crm else False,
            'partner_contact_email': getattr(dev_crm, 'partner_contact_email', False) if dev_crm else False,
        }

        values.update({
            'person_type_client': getattr(cb, 'person_type', False) if cb else False,
            'full_name_client': getattr(cb, 'full_name', False) if cb else False,
            'curp_client': getattr(cb, 'curp', False) if cb else False,
            'rfc_client': getattr(cb, 'rfc', False) if cb else False,
            'marital_status_client': getattr(cb, 'marital_status', False) if cb else False,
            'nationality_client': getattr(cb, 'nationality', False) if cb else False,
            'address_client': getattr(cb, 'address', False) if cb else False,
            'phone_number_client': getattr(cb, 'phone_number', False) if cb else False,
            'email_client': getattr(cb, 'email', False) if cb else False,
            'official_id_client': getattr(cb, 'official_id', False) if cb else False,
            'lives_in_house_client': getattr(cb, 'lives_in_house', False) if cb else False,
            'studies_client': getattr(cb, 'studies', False) if cb else False,
            'profession_client': getattr(cb, 'profession', False) if cb else False,
            'occupation_client': getattr(cb, 'occupation', False) if cb else False,
            'employer_name_client': getattr(cb, 'employer_name', False) if cb else False,
            'job_position_client': getattr(cb, 'job_position', False) if cb else False,
            'seniority_client': getattr(cb, 'seniority', False) if cb else False,
            'employer_phone_client': getattr(cb, 'employer_phone', False) if cb else False,
            'employer_address_client': getattr(cb, 'employer_address', False) if cb else False,
            'place_of_birth_client': getattr(cb, 'place_of_birth', False) if cb else False,
            'date_of_birth_client': getattr(cb, 'date_of_birth', False) if cb else False,
            'applies_assets_client': getattr(cb, 'applies_assets', False) if cb else False,
            'first_names_client': first_names_client or False,
            'last_name_materno_client': last_name_materno_client or False,
            'last_name_paterno_client': last_name_paterno_client or False,
        })

        stock_fields = [
            'full_name', 'address', 'lives_in_house', 'studies', 'profession',
            'marital_status', 'phone_number', 'email', 'nationality', 'rfc',
            'curp', 'occupation', 'job_position', 'seniority',
            'employer_name', 'employer_phone', 'employer_address',
            'applies_assets', 'shares_percentage'
        ]
        if cb:
            for i in range(1, 11):
                for f in stock_fields:
                    k = f'stockholder_{f}_{i}'
                    values[k] = getattr(cb, k, False)

            rb = cb
            address_fields = [
                'street_name', 'external_number', 'number', 'internal_number',
                'suburb', 'municipality', 'state_name', 'zip_code',
            ]
            for i in range(1, 11):
                for f in address_fields:
                    src_attr = f if i == 1 else f'{f}_{i}'
                    dst_key = f'{f}_{i}'
                    values[dst_key] = getattr(rb, src_attr, False)

            extra_fields = [
                'full_name', 'full_name_file', 'full_name_file_name',
                'official_id', 'official_id_file', 'official_id_file_name',
                'address', 'street_name', 'external_number', 'number', 'internal_number',
                'suburb', 'municipality', 'state_name', 'zip_code',
                'address_file', 'address_file_name',
                'lives_in_house', 'studies', 'profession', 'marital_status',
                'phone_number', 'email', 'nationality', 'rfc', 'rfc_file', 'rfc_file_name',
                'curp', 'curp_file', 'curp_file_name',
                'occupation', 'job_position', 'seniority',
                'employer_name', 'employer_phone', 'employer_address',
                'place_of_birth', 'date_of_birth', 'applies_assets',
            ]
            for i in range(2, 11):
                for f in extra_fields:
                    key = f'{f}_{i}'
                    values[key] = getattr(cb, key, False)


        if self.activity_user_id:
            user_vals = self._coerce_partner_values(self.activity_user_id, values)
            self.activity_user_id.write(user_vals)

            signer_partner = self.activity_user_id.partner_id
            if signer_partner:
                signer_partner_vals = self._coerce_partner_values(signer_partner, values)
                signer_partner.write(signer_partner_vals)
        if partner:
            values = self._coerce_partner_values(partner, values)
            partner.write(values)

        self._write_user_values_from_partner_values(values)
        return values


