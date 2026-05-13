# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, timedelta
from odoo.tools.translate import _
from odoo import fields as odoo_fields
from datetime import date
from dateutil.relativedelta import relativedelta
import base64

class CrmLeadCcima(models.Model):
    _inherit = "crm.lead"

    development_crm = fields.Many2one('project.worksite', string='Development')
    condominium_crm = fields.Many2one('condominium.worksite', string='Condominium')
    condominium_crm_domain_ids = fields.Many2many('condominium.worksite', compute='_compute_condominium_domain_ids')
    folder_creation_log = fields.Text(
        string='Bitacora de carpeta/expediente',
        readonly=True,
        copy=False,
    )
    new_expediente_creation_note = fields.Text(
        string='Nuevo expediente debug',
        readonly=True,
        copy=False,
    )

    documents_master = fields.One2many('crm.lead.document', compute='_compute_documents_master')
    documents_rules = fields.One2many('crm.lead.document', compute='_compute_documents_rules')
    documents_sunning = fields.One2many('crm.lead.document', compute='_compute_documents_sunning')
    documents_location = fields.One2many('crm.lead.document', compute='_compute_documents_location')
    documents_procedure = fields.One2many('crm.lead.document', compute='_compute_documents_procedure')
    documents_presentation = fields.One2many('crm.lead.document', compute='_compute_documents_presentation')
    documents_flyers = fields.One2many('crm.lead.document', compute='_compute_documents_flyers')
    documents_amenities = fields.One2many('crm.lead.document', compute='_compute_documents_amenities')
    documents_tour = fields.One2many('crm.lead.document', compute='_compute_documents_tour')
    documents_videos = fields.One2many('crm.lead.document', compute='_compute_documents_videos')
    documents_work = fields.One2many('crm.lead.document', compute='_compute_documents_work')
    documents_contract = fields.One2many('crm.lead.document', compute='_compute_documents_contract')
    documents_availability = fields.One2many('crm.lead.document', compute='_compute_documents_availability')

    url = fields.Char(string="URL")
    amortization_id = fields.Many2one('amortization.calculator', string='Amortization')
    contract_brief_id = fields.Many2one('rev.crm.contract.brief', string='Contract Brief', compute='_compute_contract_brief')
    has_contract_brief = fields.Boolean(string='Has Contract Brief', compute='_compute_contract_brief')
    brief_id = fields.Many2one('rev.crm.contract.brief', string='Contract Brief' )

    finance_amount = fields.Float(
        string='Finance Amount',
        compute='_compute_finance_amount',
        store=False
    )

    contract_brief_count = fields.Integer(
        string="Contract Briefs",
        compute="_compute_contract_brief_count",
        store=False,
    )

    def _persist_folder_creation_log(self, lines):
        for lead in self:
            log_text = '\n'.join([line for line in lines if line])
            self.env.cr.execute(
                "UPDATE crm_lead SET folder_creation_log = %s WHERE id = %s",
                (log_text, lead.id),
            )
            lead.invalidate_recordset(['folder_creation_log'])

    def _persist_new_expediente_creation_note(self, note):
        for lead in self:
            self.env.cr.execute(
                "UPDATE crm_lead SET new_expediente_creation_note = %s WHERE id = %s",
                (note, lead.id),
            )
            lead.invalidate_recordset(['new_expediente_creation_note'])

    def _compute_finance_amount(self):
        for lead in self:
            amount = 0.0

            sale = self.env['sale.order'].search([
                ('opportunity_id', '=', lead.id)
            ], limit=1)

            if sale and sale.finance_id:
                financial_line = sale.financial_lines.filtered(
                    lambda l: l.name == sale.finance_id.name
                )

                if financial_line:
                    amount = financial_line[0].amount_finance + financial_line[0].hitch

            lead.finance_amount = amount
            lead.update({
                'expected_revenue': amount,
                'sale_amount_total': amount,
            })

    def _compute_sale_data(self):
        for lead in self:
            sale_amount_total = 0.0
            quotation_count = 0
            sale_count = 0

            orders = self.env['sale.order'].search([
                ('opportunity_id', '=', lead.id)
            ])

            quotation_count = len(orders.filtered(lambda o: o.state in ['draft', 'sent']))
            sale_count = len(orders.filtered(lambda o: o.state in ['sale', 'done']))

            sale = self.env['sale.order'].search([
                ('opportunity_id', '=', lead.id)
            ], limit=1)

            if sale and sale.finance_id:
                financial_line = sale.financial_lines.filtered(
                    lambda l: l.name == sale.finance_id.name
                )
                if financial_line:
                    sale_amount_total = financial_line[0].amount_finance + financial_line[0].hitch

            lead.sale_amount_total = sale_amount_total
            lead.quotation_count = quotation_count
            lead.sale_order_count = sale_count



    def _compute_contract_brief_count(self):
        Brief = self.env['rev.crm.contract.brief'].sudo()
        for lead in self:
            lead.contract_brief_count = Brief.search_count([('lead_id', '=', lead.id)])

    def action_my_mark_lost(self):
        for lead in self:
            if lead.property_id:
                lead.property_id.state = 'free'

        lead.action_archive()
        action = self.env.ref("crm.crm_lead_lost_action").read()[0]
        action["context"] = dict(self.env.context, active_ids=self.ids, active_model="crm.lead")
        return action

    def action_view_contract_briefs(self):
        self.ensure_one()
        Brief = self.env['rev.crm.contract.brief'].sudo()
        briefs = Brief.search([('lead_id', '=', self.id)])

        action = self.env.ref('ccima_crm_reassign.action_rev_crm_contract_brief_from_lead').read()[0]
        action['domain'] = [('lead_id', '=', self.id)]
        action['context'] = {
            'default_lead_id': self.id,
            'search_default_lead_id': self.id,
        }

        if len(briefs) == 1:
            action.update({
                'view_mode': 'form',
                'res_id': briefs.id,
            })
        else:
            action['view_mode'] = 'list,form'
        return action

    def _compute_contract_brief(self):
        Contract = self.env['rev.crm.contract.brief'].sudo()

        def _fmt_currency(val):
            try:
                if val in (None, False, ''):
                    return ''
                return f"${float(val):,.2f}"
            except Exception:
                return ''

        def _is_set(v):
            return v not in (None, False, '')

        for lead in self:
            brief = Contract.search([('lead_id', '=', lead.id)], limit=1)
            process_log = [
                f"{fields.Datetime.now()}: Inicio de validacion de carpeta/expediente.",
            ]



            so = False
            if lead.order_ids:
                so = lead.order_ids.sorted(key=lambda r: (r.date_order or r.create_date))[:1]
                so = so and so[0] or False

            partner = lead.partner_id
            company = self.env.company

            curp = getattr(partner, 'l10n_mx_edi_curp', '') or ''
            rfc = partner.vat or ''
            marital_status = getattr(partner, 'individual_marital_status', '') or ''
            nationality = (getattr(partner, 'individual_nationality', False) and getattr(partner.individual_nationality,
                                                                                         'name', '')) or ''
            address_parts = [
                partner.street or '',
                partner.city or '',
                (partner.state_id and partner.state_id.name) or '',
                partner.zip or '',
                (partner.country_id and partner.country_id.name) or '',
            ]
            address = ' '.join([p for p in address_parts if p]).strip()
            email = partner.email or ''
            phone_number = partner.phone or ''

            pt = False
            line = False
            hitch_per = 0
            date_deliver = False
            date_f_m = False
            if so and so.order_line:
                line = so.order_line.sorted(key=lambda l: (l.sequence, l.id))[:1]
                line = line and line[0] or False
                hitch_per = so.hitch_porcent
                date_deliver = so.date_order.date() if so.date_order else False
                pt = getattr(line, 'product_template_id', False)

            prop = pt

            surface_val = ''
            if prop:
                if hasattr(prop, 'property_area') and prop.property_area:
                    surface_val = f"{prop.property_area} m²"
                elif hasattr(prop, 'property_id') and prop.property_id:
                    surface_val = f"{prop.property_id} m²"

            internal_fee = ''
            external_fee = ''
            main_amenities = ''
            additional_amenities = ''
            capital_gain = ''

            if prop:
                internal_fee = _fmt_currency(getattr(prop, 'maintenance_charges', False))
                external_fee = _fmt_currency(getattr(prop, 'external_initial_maintenance_fee', False))
                main_amenities = _fmt_currency(getattr(prop, 'external_amenity_maintenance_fee', False))
                additional_amenities = _fmt_currency(getattr(prop, 'external_maximum_maintenance_fee', False))
                capital_gain = _fmt_currency(getattr(prop, 'capital_gains', False))

            lot = (pt and pt.display_name) or ''
            worksite = (pt and getattr(pt, 'worksite_id', False)) or False
            condominium = (pt and getattr(pt, 'condominium_worksite_id', False)) or False

            ws_related_public_deeds = (worksite and getattr(worksite, 'related_public_deeds', '') or '') or ''
            ws_recent_public_deed = (worksite and getattr(worksite, 'recent_public_deed', '') or '') or ''
            ws_otherwise_clause = (worksite and getattr(worksite, 'otherwise_clause', '') or '') or ''
            ws_compliance_clause = (worksite and getattr(worksite, 'compliance_clause', '') or '') or ''
            ws_company_legal_name = (worksite and getattr(worksite, 'company_legal_name', '') or '') or ''
            ws_company_legal_rep = (worksite and getattr(worksite, 'company_legal_rep', '') or '') or ''
            ws_company_constitutive_act = (worksite and getattr(worksite, 'company_constitutive_act', '') or '') or ''
            ws_company_notary = (worksite and getattr(worksite, 'company_notary', '') or '') or ''
            ws_company_address = (worksite and getattr(worksite, 'company_address', '') or '') or ''
            ws_company_email = (worksite and getattr(worksite, 'company_email', '') or '') or ''

            total_price = ''
            finance_price = ''
            total_down_payment = ''
            financing = ''
            term = ''
            payments_no_interest = ''
            payments_interest_1 = ''
            payments_interest_1_25 = ''
            payments_no_interest_pt = 0
            payments_interest_1_pt = 0
            payments_interest_1_25_pt = 0

            contract_date = ''
            raw_dt = False
            if prop:
                for fname in ['property_date', 'reservation_date', 'reserved_date', 'booking_date', 'hold_date',
                              'apartado_date']:
                    val = getattr(prop, fname, False)
                    if val:
                        raw_dt = val
                        break
            if raw_dt:
                d = None
                if isinstance(raw_dt, date) and not isinstance(raw_dt, datetime):
                    d = raw_dt
                elif isinstance(raw_dt, datetime):
                    d = raw_dt.date()
                else:
                    d = odoo_fields.Date.to_date(raw_dt) or (
                        odoo_fields.Datetime.to_datetime(raw_dt).date() if raw_dt else None)
                if d:
                    contract_date = f"{d.day}/{d.month}/{d.year}"

            total_discount = 0.0
            total_price_finance = 0.0
            total_down_payment_pt = 0
            total_price_pt = 0.0
            priceperm=0
            earlypaymentper=0
            earlypaymentamo=0
            finalhitch=0
            total_ds = 0
            total_price = ''
            total_price_am = 0
            if so:
                total_price = _fmt_currency(so.amount_total) if so.amount_total is not False else ''
                total_price_am = so.amount_total if so.amount_total is not False else 0

                if hasattr(so, 'finance_id') and so.finance_id:
                    term = str(getattr(so.finance_id, 'duration_month', '') or '')
                    financing = getattr(so.finance_id, 'name', '') or ''
                fl = False

                if hasattr(so, 'financial_lines') and so.financial_lines:
                    finance_id = getattr(so, 'finance_id', False)
                    target_id = finance_id.id if finance_id else False
                    matches = so.financial_lines.filtered(
                        lambda l: getattr(l, 'interest_id', False) and l.interest_id.id == target_id)
                    fl = matches and matches[0] or False
                if fl:
                    total_price_finance = fl.amount_finance
                    total_ds = fl.discount_total
                    if fl.promotion_id:
                        total_discount = fl.promotion_id.porcent * 100
                    else:
                        total_discount = 0
                    total_price_pt = fl.amount_finance + fl.hitch
                    payments_no_interest = _fmt_currency(fl.financial_line_1)
                    payments_interest_1 = _fmt_currency(fl.financial_line_2)
                    payments_interest_1_25 = _fmt_currency(fl.financial_line_3)
                    payments_no_interest_pt = msi_months
                    payments_interest_1_pt = fl.financial_line_2
                    payments_interest_1_25_pt = fl.financial_line_3
                    priceperm = (fl.amount_finance + fl.hitch) / pt.property_area
                    if fl.promotion_id:
                        earlypaymentper = fl.promotion_id.porcent_financial
                    else:
                        earlypaymentper = 0
                    finalhitch = fl.hitch


                    if hasattr(fl, 'hitch') and fl.hitch not in (None, False):
                        total_down_payment = _fmt_currency(fl.hitch)
                        if fl.promotion_id:
                            total_down_payment_pt = (pt.net_price  - (pt.net_price - (pt.net_price - (fl.promotion_id.porcent * pt.net_price) )) ) * (0.1)
                        else:
                            total_down_payment_pt = 0
                        earlypaymentamo =  total_down_payment_pt - fl.hitch

            netamount = 0
            if pt:
                netamount= pt.net_price
            total_pay = 0
            if so:
                reservation = self.env['property.reservation'].search([('order_id','=',so.id)])
                if reservation:
                    pr_contract_bus = self.env['property.contract'].search([('reservation_id', '=', reservation.id)])
                    if pr_contract_bus:
                        pr_contract = pr_contract_bus[0]
                        if pr_contract.loan_line_ids:
                            total_pay += pr_contract.advance_payment
                            total_pay += pr_contract.extra_down_payment
                            for line in pr_contract.loan_line_ids:
                                total_pay += line.amount_to_capital
                                total_pay += line.amount_paid

                        pr_line = self.env['loan.line'].search([('contract_id', '=', pr_contract.id),('count_line', '=', 1)])
                        if pr_line:
                            date_del = pr_line.date
                            month_qty = (pt.month_deliver or 0) - 1
                            date_deliver = pr_line.date + relativedelta(months=month_qty)
                            date_f_m = pr_line.date



            m0 = 0
            m1 = 0
            m125 = 0
            msi_months = 0

            if getattr(so, 'finance_id', False):
                fina = so.finance_id
                mf = fina.name or ''

                if fina.payment_term_ids:
                    terms = fina.payment_term_ids.sorted(key=lambda t: t.end_month or 0)
                    msi_months = terms[0].end_month if len(terms) > 0 else 0

                    m0 = terms[0].end_month if len(terms) > 0 else 0

                    m1 = (
                        (terms[1].end_month or 0) - (terms[0].end_month or 0)
                        if len(terms) > 1 else 0
                    )
                    m125 = fina.duration_month or 0
            else:
                mf = ''

            Employee = self.env['hr.employee']

            advisor_employee = Employee.search(
                [('user_id', '=', lead.user_id.id)],
                limit=1
            ) if lead and lead.user_id else False

            manager_employee = False
            dvn_employee = False
            cco_employee = False

            if advisor_employee:
                manager_employee = advisor_employee.parent_id or False

                if manager_employee:
                    dvn_employee = manager_employee.parent_id or False

                    if dvn_employee:
                        cco_employee = dvn_employee.parent_id or False

            vals_pt = {
                'discount': total_discount,
                'down_payment_percent': hitch_per,
                'down_payment_amount':total_down_payment_pt,
                'amount_to_finance': total_price_finance,
                'final_amount': total_price_pt,
                'date_deliver': date_deliver,
                'date_fist_month': date_f_m,
                'msi': payments_no_interest_pt,
                'monthly_percent_m': payments_interest_1_pt,
                'monthly_percent': payments_interest_1_25_pt,
                'price_unit': priceperm,
                'net_amount': netamount,
                'early_payment_percent': earlypaymentper,
                'early_payment_amount': earlypaymentamo,
                'final_down_payment': finalhitch,
                'month_financing': mf,
                'total_paid': total_pay,
                'total_ds': total_ds,
                'lead': lead.id,
                'asesor': advisor_employee.id if advisor_employee else False,
                'gerente': manager_employee.id if manager_employee else False,
                'dvn': dvn_employee.id if dvn_employee else False,
                'cco': cco_employee.id if cco_employee else False,
                'month_0': m0,
                'month_1': m1,
                'month_125': m125,


            }

            total_price = total_price_am - total_ds

            vals_brief = {
                'lead_id': lead.id,
                'sale_order_id': so.id if so else False,
                'company_id': company.id,
                'full_name': partner.name or lead.contact_name or lead.name or 'Unnamed',
                'curp': curp,
                'rfc': rfc,
                'nationality': nationality,
                'address': address,
                'phone_number': phone_number,
                'email': email,
                'worksite_id': worksite.id if worksite else False,
                'municipality': (worksite and getattr(worksite, 'city', '') or ''),
                'lot': lot,
                'condominium_id': condominium.id if condominium else False,
                'surface': surface_val,
                'total_price': total_price,
                'finance_price': _fmt_currency(total_price_finance),
                'total_down_payment': total_down_payment,
                'financing': financing,
                'term': term,
                'payments_no_interest': payments_no_interest,
                'payments_interest_1': payments_interest_1,
                'payments_interest_1_25': payments_interest_1_25,
                'contract_date': contract_date,
                'internal_fee': internal_fee,
                'external_fee': external_fee,
                'main_amenities': main_amenities,
                'additional_amenities': additional_amenities,
                'related_public_deeds': ws_related_public_deeds,
                'recent_public_deed': ws_recent_public_deed,
                'appreciation_late': ws_otherwise_clause,
                'appreciation_on_time': ws_compliance_clause,
                'company_legal_name': ws_company_legal_name,
                'company_legal_rep': ws_company_legal_rep,
                'company_constitutive_act': ws_company_constitutive_act,
                'company_notary': ws_company_notary,
                'company_address': ws_company_address,
                'company_email': ws_company_email,
                'capital_gain': capital_gain + '%',
            }

            stage_name = getattr(getattr(lead, 'stage_id', False), 'name', '') or ''
            process_log.append(f"Etapa actual: {stage_name or 'Sin etapa'}")
            current_step = "inicio"

            try:
                if brief:
                    process_log.append(f"Ya existia Contract Brief con ID {brief.id}.")
                    process_log.append(
                        "No se creo el registro de expediente nuevo porque ya existe un Contract Brief ligado a este lead."
                    )
                    lead._persist_new_expediente_creation_note(
                        f"{fields.Datetime.now()}: No se creo el registro de expediente nuevo porque ya existe un Contract Brief ligado a este lead (ID {brief.id})."
                    )
                    print('briefbrief')
                    merged_vals = {}
                    for k, v in vals_brief.items():
                        existing = getattr(brief, k, False)
                        merged_vals[k] = existing if _is_set(existing) else v

                    merged_vals['sale_order_id'] = so.id if so else False
                    if brief.state == 'draft':
                        process_log.append("El Contract Brief estaba en borrador y se actualizo.")
                        brief.write(merged_vals)
                        pt.write(vals_pt)
                    else:
                        process_log.append(f"El Contract Brief no se actualizo porque su estado es '{brief.state}'.")

                    print('ptpt',pt)

                    if brief.full_name_2 or brief.full_name_3 or brief.full_name_4 or brief.full_name_5 or brief.full_name_6 or brief.full_name_7 or brief.full_name_8 or brief.full_name_9 or brief.full_name_10:
                        process_log.append("Se actualizaron compradores adicionales en la propiedad.")
                        pt.write({
                            'partner_id': lead.partner_id.id,
                            'second_partner_id': brief.full_name_2,
                            'third_partner_id': brief.full_name_3,
                            'fourth_partner_id': brief.full_name_4,
                            'fifth_partner_id': brief.full_name_5,
                            'sixth_partner_id': brief.full_name_6,
                            'seventh_partner_id': brief.full_name_7,
                            'eighth_partner_id': brief.full_name_8,
                            'ninth_partner_id': brief.full_name_9,
                            'tenth_partner_id': brief.full_name_10,
                            'lead': lead.id,
                            'asesor': advisor_employee.id,
                            'gerente': manager_employee.id,
                            'dvn': dvn_employee.id,
                            'cco': cco_employee.id,
                            'month_0': m0,
                            'month_1': m1,
                            'month_125': m125,
                        })

                        print('pt.write')
                else:
                    process_log.append("No existia Contract Brief previo.")
                    if stage_name == 'Apartado':
                        process_log.append("Se ejecuto flujo de etapa Apartado.")
                        process_log.append(f"Producto detectado: {pt.display_name if pt else 'Sin producto'}")
                        process_log.append(f"Cliente detectado: {lead.partner_id.name if lead.partner_id else 'Sin cliente'}")
                        current_step = "crear_contract_brief"
                        brief = Contract.create(vals_brief)
                        process_log.append(f"Se creo Contract Brief con ID {brief.id}.")
                        lead._persist_folder_creation_log(process_log)

                        if not pt:
                            process_log.append("No existe producto relacionado para aplicar vals_pt.")
                            lead._persist_folder_creation_log(process_log)
                        current_step = "actualizar_producto_vals_pt"
                        pt.write(vals_pt)
                        process_log.append("Se actualizaron datos del producto.")
                        lead._persist_folder_creation_log(process_log)

                        hitch_amount = 0.0
                        if so and 'fl' in locals() and fl and getattr(fl, 'hitch', False):
                            try:
                                hitch_amount = float(fl.hitch)
                            except Exception:
                                hitch_amount = 0.0
                        hitch_text = f"${hitch_amount:,.2f}"

                        current_step = "enviar_recibo_pdf"
                        self.action_send_receipt_pdf_direct()
                        process_log.append("Se envio el recibo PDF al cliente.")
                        lead._persist_folder_creation_log(process_log)

                        folder = False
                        folder_doc = False
                        folder_con = False
                        if pt and getattr(pt, 'carpet_id', False) and pt.carpet_id.id:
                            process_log.append(f"Se encontro carpeta padre en la propiedad: {pt.carpet_id.id}.")
                            lead._persist_folder_creation_log(process_log)
                            current_step = "crear_carpetas_expediente"
                            folder = self.env['documents.document'].create({
                                'name': pt.name + ' ' + self.partner_id.name or 'Unnamed',
                                'owner_id': self.env.ref('base.user_root').id,
                                'type': 'folder',
                                'access_internal': 'view',
                                'folder_id': pt.carpet_id.id,
                            })
                            folder_doc = self.env['documents.document'].create({
                                'name': 'Documentos',
                                'owner_id': self.env.ref('base.user_root').id,
                                'type': 'folder',
                                'access_internal': 'view',
                                'folder_id': folder.id,
                            })
                            folder_con = self.env['documents.document'].create({
                                'name': 'Contratos',
                                'owner_id': self.env.ref('base.user_root').id,
                                'type': 'folder',
                                'access_internal': 'view',
                                'folder_id': folder.id,
                            })
                            process_log.append(
                                f"Se crearon carpetas: principal {folder.id}, Documentos {folder_doc.id}, Contratos {folder_con.id}."
                            )
                            lead._persist_folder_creation_log(process_log)
                        else:
                            process_log.append(
                                "No se crearon carpetas porque la propiedad no tiene carpet_id o no existe producto relacionado."
                            )
                            lead._persist_folder_creation_log(process_log)

                        nombre_desarrollo = worksite.name
                        nombre_unidad = pt.name
                        nombre_cliente = lead.partner_id.name
                        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
                        link_upload = f"{base_url}/contract/upload?rev_id={brief.id}"
                        image_url = f"{base_url}/ccima_crm_reassign/static/src/img/pasos_proceso.png"

                        if folder_doc and folder_con:
                            current_step = "asignar_carpetas_a_contract_brief"
                            brief.write({'brief_folder_id': folder_doc.id})
                            brief.write({'contract_folder_id': folder_con.id})
                            process_log.append("Se asignaron carpetas al Contract Brief.")
                            lead._persist_folder_creation_log(process_log)
                        else:
                            process_log.append(
                                "No se asignaron carpetas al Contract Brief porque no se pudieron crear las carpetas Documentos/Contratos."
                            )
                            lead._persist_folder_creation_log(process_log)

                        subject = f"¡Felicidades {nombre_cliente}! Tu apartado en Portto Blanco ha sido confirmado 🎉"

                        body_html = f"""
                        <p>Inversion: <b>{nombre_unidad}</b><br/>
                        Desarrollo: <b>{nombre_desarrollo}</b></p>

                        <p>
                        Más de 2,000 aliados ya disfrutan de los beneficios de su inversión y del crecimiento de su patrimonio en Portto Blanco,
                        y hoy tú también formas parte de esta comunidad que apuesta por proyectos con visión, certeza y valor a largo plazo.
                        </p>

                        <p>
                        Mi nombre es <b>Martha Alicia Rivera</b>, y estaré acompañándote personalmente durante todo el proceso.
                        Desde la integración de tu expediente hasta la firma del contrato, estaré en contacto contigo junto con tu asesor comercial
                        para asegurar que cada paso sea claro, rápido y sin complicaciones.
                        </p>

                        <p>
                        Queremos que sepas que este proceso es más sencillo de lo que imaginas.
                        Lo hemos diseñado para que sea lo más ágil posible y juntos lo completaremos en un máximo de
                        <b>10 días hábiles</b>, siempre con el respaldo de nuestro equipo.
                        </p>

                        <p>
                        Para facilitar este camino, te comparto los cinco pasos que seguiremos:
                        </p>

                        <p>
                        <img src="{image_url}" style="max-width:100%; height:auto; display:block; margin:16px 0;"/>
                        </p>
                        
                        
                        <p>Sube tus archivos aquí: <a href="{link_upload}">{link_upload}</a></p>

                        <p>
                        Estaré disponible en todo momento para resolver tus dudas, brindarte seguimiento y asegurar que tu experiencia
                        sea ágil, clara y satisfactoria.
                        </p>
                        """

                        current_step = "enviar_correo_bienvenida_expediente"
                        mail = self.env["mail.mail"].create({
                            "subject": subject,
                            "body_html": body_html,
                            "email_to": partner.email,
                            "author_id": self.env.user.partner_id.id,
                        })
                        mail.send()
                        process_log.append("Se envio correo de bienvenida del expediente.")
                        lead._persist_folder_creation_log(process_log)

                        excluded_fields = {
                            'id',
                            'create_uid',
                            'create_date',
                            'write_uid',
                            'write_date',
                            '__last_update',
                            'message_follower_ids',
                            'message_ids',
                            'activity_ids',
                        }

                        field_names = [
                            name for name in self._fields
                            if name not in excluded_fields
                        ]


                        data = lead.copy_data()[0]
                        data.pop('id', None)
                        data['name'] = lead.name
                        data['brief_id'] = brief.id

                        current_step = "buscar_etapa_nuevo_expediente"
                        stage = self.env['crm.stage'].search([('name', '=', 'Nuevo Expediente')], limit=1)
                        if stage:
                            process_log.append(f"Se encontro la etapa 'Nuevo Expediente' con ID {stage.id}.")
                            data['stage_id'] = stage.id
                        else:
                            process_log.append(
                                "No se encontro la etapa 'Nuevo Expediente'; se intentara crear el expediente nuevo sin forzar esa etapa."
                            )
                        lead._persist_folder_creation_log(process_log)

                        current_step = "crear_registro_expediente_nuevo"
                        new_lead = self.env['crm.lead'].with_context(skip_duplicate_check=True).create(data)
                        process_log.append(f"Se creo el nuevo expediente con ID {new_lead.id}.")
                        stage_result = stage.name if stage else 'Sin etapa asignada'
                        lead._persist_new_expediente_creation_note(
                            f"{fields.Datetime.now()}: Se creo el registro de expediente nuevo con ID {new_lead.id}. Etapa asignada: {stage_result}."
                        )
                        lead._persist_folder_creation_log(process_log)
                    else:
                        process_log.append(
                            "No se ejecuto la creacion de carpeta/expediente porque la etapa actual no es 'Apartado'."
                        )
                        process_log.append(
                            f"No se creo el registro de expediente nuevo porque el lead esta en etapa '{stage_name or 'Sin etapa'}' y se requiere 'Apartado'."
                        )
                        lead._persist_new_expediente_creation_note(
                            f"{fields.Datetime.now()}: No se creo el registro de expediente nuevo porque el lead esta en etapa '{stage_name or 'Sin etapa'}' y se requiere 'Apartado'."
                        )
            except Exception as exc:
                process_log.append(
                    f"No se pudo crear el registro de expediente nuevo. Paso con error: {current_step}. Detalle: {repr(exc)}"
                )
                process_log.append(f"Error detectado durante el proceso: {repr(exc)}")
                lead._persist_new_expediente_creation_note(
                    f"{fields.Datetime.now()}: No se pudo crear el registro de expediente nuevo. Paso con error: {current_step}. Detalle: {repr(exc)}"
                )
                lead._persist_folder_creation_log(process_log)
                raise
            lead._persist_folder_creation_log(process_log)
            lead.contract_brief_id = brief.id if brief else False
            lead.has_contract_brief = bool(brief)

            brief.action_create_commission()

    def action_send_receipt_pdf_direct(self):
        self.ensure_one()

        if not self.partner_id or not self.partner_id.email:
            raise UserError(_("The customer has no email defined."))

        # ---- 1) report_ref (QWeb template name)
        report_ref = 'ccima_crm_reassign.report_payment_receipt_document'

        # ---- 2) Render PDF (enterprise-compatible signature)
        report_service = self.env['ir.actions.report']
        pdf_content, _content_type = report_service._render_qweb_pdf(
            report_ref,
            res_ids=[self.id],
        )

        # ---- 3) Attachment
        attachment = self.env['ir.attachment'].create({
            'name': f'Receipt - {self.display_name}.pdf',
            'type': 'binary',
            'datas': base64.b64encode(pdf_content),
            'res_model': self._name,
            'res_id': self.id,
            'mimetype': 'application/pdf',
        })

        # ---- 4) Send email direct (no template)
        mail = self.env['mail.mail'].sudo().create({
            'subject': f'Receipt - {self.display_name}',
            'body_html': """
                <div>
                    <p>Hello,</p>
                    <p>Please find attached your payment receipt.</p>
                    <p>Regards.</p>
                </div>
            """,
            'email_to': self.partner_id.email,
            'attachment_ids': [(4, attachment.id)],
        })
        mail.send()


    def action_open_amortization(self):
        self.ensure_one()
        amort = self.amortization_id
        if not amort:
            amort = self.env['amortization.calculator'].create({})
            self.amortization_id = amort.id
        return {
            'name': 'Amortization',
            'type': 'ir.actions.act_window',
            'res_model': 'amortization.calculator',
            'view_mode': 'form',
            'res_id': amort.id,
            'target': 'current',
            'context': dict(self.env.context, allowed_company_ids=self.env.user.company_ids.ids),
        }

    @api.onchange('development_crm')
    def _compute_condominium_domain_ids(self):
        if self.development_crm:
            condos = self.env['condominium.worksite'].search([])
            self.condominium_crm_domain_ids = condos.filtered(
                lambda c: c.parent_id and c.parent_id.parent_id and c.parent_id.parent_id.id == self.development_crm.id
            )
        else:
            self.condominium_crm_domain_ids = False

    def _compute_documents(self, doc_type, field_name):
        Doc = self.env['crm.lead.document']
        for rec in self:
            docs = Doc.browse()

            domain = [('document_type', '=', doc_type)]
            cond_parts = []
            if rec.condominium_crm:
                cond_parts.append(('condominium_id', '=', rec.condominium_crm.id))
            if rec.development_crm:
                cond_parts.append(('project_id', '=', rec.development_crm.id))

            if cond_parts:
                if len(cond_parts) == 2:
                    search_domain = ['|'] + cond_parts + domain
                else:
                    search_domain = cond_parts + domain
                docs |= Doc.search(search_domain)

            parent = rec.condominium_crm.parent_id if rec.condominium_crm else False
            if parent:
                docs |= parent.documents_master.filtered(lambda d: d.document_type == doc_type)

            rec[field_name] = docs

    @api.onchange('condominium_crm')
    def _onchange_condominium_crm(self):
        if not self.condominium_crm:
            self.property_id = False
        return {
            'domain': {
                'property_id': [
                    ('condominium_worksite_id', '=', self.condominium_crm.id)
                ] if self.condominium_crm else []
            }
        }

    @api.depends('condominium_crm')
    def _compute_documents_master(self):
        self._compute_documents('master', 'documents_master')

    @api.depends('condominium_crm')
    def _compute_documents_rules(self):
        self._compute_documents('rules', 'documents_rules')

    @api.depends('condominium_crm')
    def _compute_documents_sunning(self):
        self._compute_documents('sunning', 'documents_sunning')

    @api.depends('condominium_crm')
    def _compute_documents_location(self):
        self._compute_documents('location', 'documents_location')

    @api.depends('condominium_crm')
    def _compute_documents_procedure(self):
        self._compute_documents('procedure', 'documents_procedure')

    @api.depends('condominium_crm')
    def _compute_documents_presentation(self):
        self._compute_documents('presentation', 'documents_presentation')

    @api.depends('condominium_crm')
    def _compute_documents_flyers(self):
        self._compute_documents('flyers', 'documents_flyers')

    @api.depends('condominium_crm')
    def _compute_documents_amenities(self):
        self._compute_documents('amenities', 'documents_amenities')

    @api.depends('condominium_crm')
    def _compute_documents_tour(self):
        self._compute_documents('tour', 'documents_tour')

    @api.depends('condominium_crm')
    def _compute_documents_videos(self):
        self._compute_documents('videos', 'documents_videos')

    @api.depends('condominium_crm')
    def _compute_documents_work(self):
        self._compute_documents('work', 'documents_work')

    @api.depends('condominium_crm')
    def _compute_documents_contract(self):
        self._compute_documents('contract', 'documents_contract')

    @api.depends('condominium_crm')
    def _compute_documents_availability(self):
        self._compute_documents('availability', 'documents_availability')

    def send_noti(self):
        notification = {
            'type': 'ir.actions.client',
            'tag': 'display_notification',
            'params': {
                'message': 'Se reasigno el lead',
                'type': None,
                'sticky': False,
            },
        }
        return notification

    def write(self, vals):
        for record in self:
            if 'condominium_crm' in vals:
                condo = self.env['condominium.worksite'].browse(vals['condominium_crm'])
                vals['url'] = condo.url
            elif 'development_crm' in vals and not record.condominium_crm and 'condominium_crm' not in vals:
                dev = self.env['project.worksite'].browse(vals['development_crm'])
                vals['url'] = dev.url
        return super().write(vals)

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('condominium_crm'):
                condo = self.env['condominium.worksite'].browse(vals['condominium_crm'])
                vals['url'] = condo[0].url
            elif vals.get('development_crm'):
                dev = self.env['project.worksite'].browse(vals['development_crm'])
                vals['url'] = dev.url

            if 'partner_id' in vals and 'email_from' in vals and 'phone' in vals:
                existing_lead = self.env['crm.lead'].search([
                    ('partner_id', '=', vals['partner_id']),
                    ('email_from', '=', vals['email_from']),
                    ('phone', '=', vals['phone']),
                ], limit=1)

                if existing_lead:
                    if vals.get('user_id') and existing_lead.user_id.id == vals['user_id']:
                        continue

                    txtid = '[' + str(existing_lead.id) + ']'
                    lastact = self.env['mail.activity.schedule'].search([
                        ('res_model', '=', 'crm.lead'),
                        ('res_ids', '=', txtid),
                    ], order='id desc', limit=1)

                    if lastact:
                        datecom = datetime.now() + timedelta(days=-30)
                        if lastact.create_date < datecom:
                            self.env['mail.activity'].sudo().create({
                                'res_model_id': self.env['ir.model']._get_id('crm.lead'),
                                'res_id': existing_lead.id,
                                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                'summary': 'Lost lead',
                                'user_id': existing_lead.user_id.id,
                                'date_deadline': fields.Date.today(),
                            })
                            self.env['mail.activity'].sudo().create({
                                'res_model_id': self.env['ir.model']._get_id('crm.lead'),
                                'res_id': existing_lead.id,
                                'activity_type_id': self.env.ref('mail.mail_activity_data_todo').id,
                                'summary': 'Win lead',
                                'user_id': vals['user_id'],
                                'date_deadline': fields.Date.today(),
                            })
                            existing_lead.write({'user_id': vals['user_id']})
                            self.env.cr.commit()
                            raise UserError(_("The lead has been reassigned."))
                        else:
                            raise UserError(_("The client has already been created."))
                    else:
                        raise UserError(_("The client has already been created."))

        leads = super(CrmLeadCcima, self).create(vals_list)
        return leads

    def action_open_url(self):
        for record in self:
            if not record.url:
                raise UserError(_("No URL."))
            url = record.url
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }
