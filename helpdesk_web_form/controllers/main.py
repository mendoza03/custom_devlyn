import base64

from odoo import http
from odoo.http import request


CATEGORY_SLUG_XMLIDS = {
    "facturacion_reenvio_pdf_xml": "helpdesk_custom_datos.helpdesk_ticket_category_facturacion_reenvio_pdf_xml",
    "dev_real_tc_db": "helpdesk_custom_datos.helpdesk_ticket_category_devoluciones_reales_tarjeta_credito_debito",
    "dev_real_cash_order": "helpdesk_custom_datos.helpdesk_ticket_category_devoluciones_reales_efectivo_orden_pago",
    "dev_real_cash_transfer": "helpdesk_custom_datos.helpdesk_ticket_category_devoluciones_reales_efectivo_transferencia",
    "receta_lc_lente_contacto": "helpdesk_custom_datos.helpdesk_ticket_category_receta_lc_lente_contacto",
    "papeleria_seguimiento": "helpdesk_custom_datos.helpdesk_ticket_category_papeleria_seguimiento",
}


class HelpdeskController(http.Controller):

    def _get_category_slug(self, category):
        if not category:
            return ""

        env = request.env(user=request.website.user_id.id)
        # env = request.env
        for slug, xmlid in CATEGORY_SLUG_XMLIDS.items():
            record = env.ref(xmlid, raise_if_not_found=False)
            if record and record.id == category.id:
                return slug
        return ""

    def _validate_hierarchy(self, section_id, category_id, subcategory_id):

        env = request.env(user=request.website.user_id.id)
        section = env['helpdesk.section'].sudo().browse(section_id) if section_id else request.env['helpdesk.section']
        category = env['helpdesk.ticket.category'].sudo().browse(category_id) if category_id else request.env['helpdesk.ticket.category']
        subcategory = env['helpdesk.ticket.subcategory'].sudo().browse(subcategory_id) if subcategory_id else request.env['helpdesk.ticket.subcategory']

        if section_id and not section.exists():
            return False
        if category_id and not category.exists():
            return False
        if subcategory_id and not subcategory.exists():
            return False
        if section_id and category_id and category.section_id.id != section.id:
            return False
        if category_id and subcategory_id and subcategory.category_id.id != category.id:
            return False
        return True

    @http.route(['/helpdesk', '/<string:lang>/helpdesk'], type='http', auth='public', website=True)
    def helpdesk_form(self, **kwargs):
        env = request.env(user=request.website.user_id.id)
        sections = env['helpdesk.section'].sudo().search([('active', '=', True)], order='sequence, name, id')
        return request.render('helpdesk_web_form.helpdesk_form_template', {'sections': sections})

    @http.route(
        ['/helpdesk/categories', '/<string:lang>/helpdesk/categories'],
        type='http', auth='public', methods=['POST'], csrf=False, website=True
    )
    def helpdesk_categories(self, **post):
        section_id = int(post.get('section_id') or 0)
        env = request.env(user=request.website.user_id.id)
        cats = env['helpdesk.ticket.category'].sudo().sudo().search([
            ('section_id', '=', section_id),
            ('active', '=', True),
        ])
        return request.make_json_response([
            {'id': c.id, 'name': c.name, 'slug': self._get_category_slug(c)}
            for c in cats
        ])

    @http.route(
        ['/helpdesk/subcategories', '/<string:lang>/helpdesk/subcategories'],
        type='http', auth='public', methods=['POST'], csrf=False, website=True
    )
    def helpdesk_subcategories(self, **post):
        category_id = int(post.get('category_id') or 0)
        env = request.env(user=request.website.user_id.id)
        subs = env['helpdesk.ticket.subcategory'].sudo().search([
            ('category_id', '=', category_id),
            ('active', '=', True),
        ])
        return request.make_json_response([
            {'id': s.id, 'name': s.name, 'code': s.code or ''}
            for s in subs
        ])

    @http.route(
        ['/helpdesk/submit', '/<string:lang>/helpdesk/submit'],
        type='http', auth='public', methods=['POST'], website=True
    )
    def helpdesk_submit(self, **post):
        env = request.env(user=request.website.user_id.id)

        def _int(key):
            val = post.get(key)
            return int(val) if val else False

        def _str(key):
            val = post.get(key, '').strip()
            return val if val else False

        def _float(key):
            val = post.get(key, '').strip()
            try:
                return float(val) if val else False
            except ValueError:
                return False

        def _date(key):
            val = post.get(key, '').strip()
            return val if val else False

        def _sel(key):
            return post.get(key) or 'select'

        def _radio(key):
            val = post.get(key, '').strip()
            return val if val else False

        section_id = _int('x_section_id')
        category_id = _int('x_category_id')
        subcategory_id = _int('x_subcategory_id')

        if not self._validate_hierarchy(section_id, category_id, subcategory_id):
            return request.not_found()

        ticket = env['helpdesk.ticket'].sudo().create({
            # ── Campos base ───────────────────────────────────────────────────
            'name':                     _str('x_general_description'),
            'x_general_description':    _str('x_general_description'),
            'x_section_id':             section_id,
            'x_category_id':            category_id,
            'x_subcategory_id':         subcategory_id,
            'x_detailed_description':   _str('x_detailed_description'),
            'partner_email':            post.get('email'),

            # ── Micas sin cortar / Trabajos atrasados ─────────────────────────
            'x_order_number':           _str('x_order_number'),
            'x_bag':                    _str('x_bag'),
            'x_customer_warehouse':     _sel('x_customer_warehouse'),
            'x_order_type':             _sel('x_order_type'),
            'x_authorized_by':          _str('x_authorized_by'),
            'x_lab_indicated':          _str('x_lab_indicated'),
            'x_job_type':               _str('x_job_type'),
            'x_original_order_number':  _str('x_original_order_number'),
            'x_shipping_guide_number':  _str('x_shipping_guide_number'),
            'x_frame_bag_number':       _str('x_frame_bag_number'),

            # ── Sub-bloque tipo pedido (adaptación / imagen) ──────────────────
            'x_order_type_adaptation':  _sel('x_order_type_adaptation'),
            'x_order_type_imagen':      _sel('x_order_type_imagen'),

            # ── Correo electrónico ────────────────────────────────────────────
            'x_branch_email':           _str('x_branch_email'),
            'x_email_issue_type_2':     _str('x_email_issue_type_2'),
            'x_contact_number':         _str('x_contact_number'),

            # ── Equipo de cómputo ─────────────────────────────────────────────
            'x_internal_folio_number':  _str('x_internal_folio_number'),
            'x_equipment_type':         _sel('x_equipment_type'),
            'x_model_or_brand':         _str('x_model_or_brand'),
            'x_serial_number':          _str('x_serial_number'),
            'x_fixed_asset_number':     _str('x_fixed_asset_number'),
            'x_shipping_guide':         _str('x_shipping_guide'),
            'x_courier':                _str('x_courier'),

            # ── Interredes ────────────────────────────────────────────────────
            'x_store_number':           _str('x_store_number'),
            'x_interredes_user':        _str('x_interredes_user'),

            # ── Problemas impresora / Surtido tóner ───────────────────────────
            'x_printer_model':          _str('x_printer_model'),
            'x_contact_person_name':    _str('x_contact_person_name'),
            'x_toner_below_15':         _sel('x_toner_below_15'),

            # ── Limpieza profunda ─────────────────────────────────────────────
            'x_cleaning_area':          _sel('x_cleaning_area'),

            # ── Facturación (no_recibidos_facturacion) ────────────────────────
            'x_fact_busco_portal':          _sel('x_fact_busco_portal'),
            'x_fact_encontraste':           _sel('x_fact_encontraste'),
            'x_fact_pdf_xml_incorrectos':   _sel('x_fact_pdf_xml_incorrectos'),

            # ── Refacturación ─────────────────────────────────────────────────
            'x_refac_order_number':         _str('x_refac_order_number'),
            'x_refac_sale_order':           _str('x_refac_sale_order'),
            'x_refac_legal_name':           _str('x_refac_legal_name'),
            'x_refac_rfc':                  _str('x_refac_rfc'),
            'x_refac_sat_screen_attached':  _sel('x_refac_sat_screen_attached'),
            'x_refac_payment_method':       _sel('x_refac_payment_method'),
            'x_refac_person_type':          _sel('x_refac_person_type'),
            'x_refac_cfdi_use':             _sel('x_refac_cfdi_use'),
            'x_refac_fiscal_regime':        _sel('x_refac_fiscal_regime'),
            'x_refac_fiscal_address':       _sel('x_refac_fiscal_address'),
            'x_refac_cp':                   _str('x_refac_cp'),

            # ── Devoluciones reales - Tarjeta crédito/débito ──────────────────
            'x_card_client_name':               _str('x_card_client_name'),
            'x_card_sap_center':                _str('x_card_sap_center'),
            'x_card_sale_order':                _str('x_card_sale_order'),
            'x_card_order_number':              _str('x_card_order_number'),
            'x_card_sale_date':                 _date('x_card_sale_date'),
            'x_card_sale_amount':               _float('x_card_sale_amount'),
            'x_card_refund_amount':             _float('x_card_refund_amount'),
            'x_card_refund_reason':             _str('x_card_refund_reason'),
            'x_card_number_16_digits':          _str('x_card_number_16_digits'),
            'x_card_expiration_mmaa':           _str('x_card_expiration_mmaa'),
            'x_card_authorization_number':      _str('x_card_authorization_number'),
            'x_card_holder_relationship':       _str('x_card_holder_relationship'),
            'x_card_client_received_product':   _sel('x_card_client_received_product'),

            # ── Devoluciones reales - Cargos duplicados ───────────────────────
            'x_duplicate_affiliation':              _str('x_duplicate_affiliation'),
            'x_duplicate_tracking_id':              _str('x_duplicate_tracking_id'),
            'x_duplicate_internal_terminal':        _str('x_duplicate_internal_terminal'),
            'x_duplicate_refund_request_attached':  _radio('x_duplicate_refund_request_attached'),

            # ── Devoluciones reales - Error examen / Fecha entrega ────────────
            'x_exam_ov_cancelled':                  _radio('x_exam_ov_cancelled'),
            'x_exam_refund_request_attached':       _radio('x_exam_refund_request_attached'),

            # ── Devoluciones reales - Efectivo (Orden de pago / Transferencia) ─
            'x_cash_society':                   _str('x_cash_society'),
            'x_cash_banamex_branch_number':     _str('x_cash_banamex_branch_number'),
            'x_cash_beneficiary_name':          _str('x_cash_beneficiary_name'),
            'x_transfer_clabe_18':              _str('x_transfer_clabe_18'),
            'x_transfer_account_holder':        _str('x_transfer_account_holder'),
            'x_transfer_bank':                  _str('x_transfer_bank'),

            # ── ALE página web ────────────────────────────────────────────────
            'x_ale_incident_type':          _sel('x_ale_incident_type'),
            'x_ale_employee_name':          _str('x_ale_employee_name'),
            'x_ale_branch':                 _str('x_ale_branch'),
            'x_ale_region':                 _str('x_ale_region'),
            'x_ale_district':               _str('x_ale_district'),

            # ── Universidad Devlyn ────────────────────────────────────────────
            'x_university_incident_type':   _sel('x_university_incident_type'),
            'x_university_employee_name':   _str('x_university_employee_name'),
            'x_university_employee_number': _str('x_university_employee_number'),
            'x_university_branch':          _str('x_university_branch'),
            'x_university_zone':            _str('x_university_zone'),
            'x_university_district':        _str('x_university_district'),
            'x_university_course_name':     _str('x_university_course_name'),
            'x_university_real_position':   _str('x_university_real_position'),

            # ── Evaluaciones - Carpeta de productos ───────────────────────────
            'x_eval_request_type':          _sel('x_eval_request_type'),
            'x_eval_ale_incident':          _sel('x_eval_ale_incident'),
            'x_eval_employee_name':         _str('x_eval_employee_name'),
            'x_eval_employee_number':       _str('x_eval_employee_number'),
            'x_eval_branch':                _str('x_eval_branch'),

            # ── Evaluaciones - Políticas y procedimientos ─────────────────────
            'x_eval_policies_type':                 _sel('x_eval_policies_type'),
            'x_eval_policies_employee_name':        _str('x_eval_policies_employee_name'),
            'x_eval_policies_employee_number':      _str('x_eval_policies_employee_number'),
            'x_eval_policies_branch':               _str('x_eval_policies_branch'),

            # ── Promoción de puesto ───────────────────────────────────────────
            'x_promotion_is_responsible':       _sel('x_promotion_is_responsible'),
            'x_promotion_interested_name':      _str('x_promotion_interested_name'),
            'x_promotion_employee_numbers':     _str('x_promotion_employee_numbers'),

            # ── Display campañas y aperturas ──────────────────────────────────
            'x_display_manual_read':                _sel('x_display_manual_read'),
            'x_display_aparador_type':              _str('x_display_aparador_type'),
            'x_display_checklist_review':           _sel('x_display_checklist_review'),
            'x_display_missing_campaign_aparador':  _sel('x_display_missing_campaign_aparador'),
            'x_display_missing_promo_campaign':     _sel('x_display_missing_promo_campaign'),
            'x_display_other':                      _radio('x_display_other'),
            'x_display_checklist_attached':         _radio('x_display_checklist_attached'),

            # ── Reposición elemento dañado ────────────────────────────────────
            'x_damaged_element_to_replace':     _str('x_damaged_element_to_replace'),
            'x_damaged_brief_description':      _str('x_damaged_brief_description'),
            'x_damaged_quantity':               _str('x_damaged_quantity'),
            'x_damaged_measurements':           _str('x_damaged_measurements'),
            'x_damaged_photo_attached':         _radio('x_damaged_photo_attached'),

            # ── Convenios ─────────────────────────────────────────────────────
            'x_agreement_support_type':         _sel('x_agreement_support_type'),
            'x_agreement_number':               _str('x_agreement_number'),
            'x_agreement_social_name':          _str('x_agreement_social_name'),

            # ── Problema pagos (anticipos) ────────────────────────────────────
            'x_payment_center':         _str('x_payment_center'),
            'x_payment_pos_order':      _str('x_payment_pos_order'),
            'x_payment_sale_date':      _date('x_payment_sale_date'),
            'x_payment_sale_total':     _float('x_payment_sale_total'),
            'x_payment_number_1':       _str('x_payment_number_1'),
            'x_payment_receipt_1':      _str('x_payment_receipt_1'),
            'x_payment_date_1':         _date('x_payment_date_1'),

            # ── Captura OV ────────────────────────────────────────────────────
            'x_capture_ov_error_type':          _sel('x_capture_ov_error_type'),
            'x_capture_ov_sphere_od':           _str('x_capture_ov_sphere_od'),
            'x_capture_ov_sphere_oi':           _str('x_capture_ov_sphere_oi'),
            'x_capture_ov_material_type':       _str('x_capture_ov_material_type'),
            'x_capture_ov_work_type':           _str('x_capture_ov_work_type'),
            'x_capture_ov_discount_type':       _str('x_capture_ov_discount_type'),
            'x_capture_ov_payment_type':        _str('x_capture_ov_payment_type'),
            'x_capture_ov_employee_number':     _str('x_capture_ov_employee_number'),

            # ── No recepcionar bolsa ──────────────────────────────────────────
            'x_bag_number':             _str('x_bag_number'),
            'x_bag_key':                _str('x_bag_key'),
            'x_sap_branch_send':        _str('x_sap_branch_send'),
            'x_sap_branch_receive':     _str('x_sap_branch_receive'),
            'x_transport_number':       _str('x_transport_number'),
            'x_transfer':               _sel('x_transfer'),

            # ── Pedido sin embalaje ───────────────────────────────────────────
            'x_order_without_packaging_pos_order':  _str('x_order_without_packaging_pos_order'),
            'x_order_without_packaging_date':       _date('x_order_without_packaging_date'),
            'x_order_without_packaging_branch':     _str('x_order_without_packaging_branch'),

            # ── Problema captura devolución ───────────────────────────────────
            'x_return_capture_error_type':      _sel('x_return_capture_error_type'),
            'x_return_capture_type':            _sel('x_return_capture_type'),
            'x_return_capture_sale_order':      _str('x_return_capture_sale_order'),
            'x_return_capture_order':           _str('x_return_capture_order'),
            'x_return_capture_cause_number':    _str('x_return_capture_cause_number'),

            # ── Rescate cancelaciones clientes molestos ───────────────────────
            'x_rescue_client_name':     _str('x_rescue_client_name'),
            'x_rescue_client_phone':    _str('x_rescue_client_phone'),
            'x_rescue_sale_order':      _str('x_rescue_sale_order'),
            'x_rescue_order_number':    _str('x_rescue_order_number'),
            'x_rescue_client_email':    _str('x_rescue_client_email'),

            # ── Online: campos comunes ────────────────────────────────────────
            'x_online_fulfillment':         _str('x_online_fulfillment'),
            'x_online_sale_date':           _date('x_online_sale_date'),
            'x_online_customer_email':      _str('x_online_customer_email'),
            'x_online_pos_order':           _str('x_online_pos_order'),
            'x_online_customer_name':       _str('x_online_customer_name'),
            'x_online_client_phone':        _str('x_online_client_phone'),
            'x_online_payment_method':      _str('x_online_payment_method'),
            'x_online_attachment_capture':  _radio('x_online_attachment_capture'),

            # ── Online: pedidos incompletos ───────────────────────────────────
            'x_online_missing_product':     _str('x_online_missing_product'),

            # ── Online: graduación incorrecta ─────────────────────────────────
            'x_online_requested_graduation':    _str('x_online_requested_graduation'),
            'x_online_received_graduation':     _str('x_online_received_graduation'),
            'x_online_return_sap_center':       _str('x_online_return_sap_center'),
            'x_online_return_bag_cedis':        _str('x_online_return_bag_cedis'),

            # ── Online: pedido otro cliente ───────────────────────────────────
            'x_online_reported_customer_vtex':  _str('x_online_reported_customer_vtex'),
            'x_online_arrived_order_vtex':      _str('x_online_arrived_order_vtex'),
            'x_online_received_order_name':     _str('x_online_received_order_name'),
            'x_online_received_product':        _str('x_online_received_product'),

            # ── Online: devolución de pedidos ─────────────────────────────────
            'x_online_return_reason':           _str('x_online_return_reason'),
            'x_online_payment_platform':        _sel('x_online_payment_platform'),
            'x_online_payment_reference':       _str('x_online_payment_reference'),

            # ── Online: graduación error cliente ──────────────────────────────
            'x_online_correct_graduation':      _str('x_online_correct_graduation'),

            # ── Online: pedidos sin estatus ───────────────────────────────────
            'x_online_promised_date':           _date('x_online_promised_date'),

            # ── Online: paquete retornado / cambio domicilio ──────────────────
            'x_online_guide_number':            _str('x_online_guide_number'),
            'x_online_receiver_name':           _str('x_online_receiver_name'),
            'x_online_contact_phone':           _str('x_online_contact_phone'),
            'x_online_new_address':             _str('x_online_new_address'),
            'x_online_additional_references':   _str('x_online_additional_references'),

            # ── Online: devolución sin entregar ───────────────────────────────
            'x_online_unshipped_order':         _str('x_online_unshipped_order'),

            # ── Online: graduación sucursal ───────────────────────────────────
            'x_online_exam_sap_center':         _str('x_online_exam_sap_center'),
            'x_online_exam_date':               _date('x_online_exam_date'),
            'x_online_exam_employee_number':    _str('x_online_exam_employee_number'),
            'x_online_exam_employee_name':      _str('x_online_exam_employee_name'),
            'x_online_sphere_od':               _str('x_online_sphere_od'),
            'x_online_sphere_oi':               _str('x_online_sphere_oi'),
            'x_online_cylinder_od':             _str('x_online_cylinder_od'),
            'x_online_cylinder_oi':             _str('x_online_cylinder_oi'),
            'x_online_axis_od':                 _str('x_online_axis_od'),
            'x_online_axis_oi':                 _str('x_online_axis_oi'),
            'x_online_ipd_od':                  _str('x_online_ipd_od'),
            'x_online_ipd_oi':                  _str('x_online_ipd_oi'),

            # ── Online: atraso lente de contacto ──────────────────────────────
            'x_online_work_order_number':       _str('x_online_work_order_number'),

            # ── Búsqueda de armazón ───────────────────────────────────────────
            'x_frame_search_sale_order':        _str('x_frame_search_sale_order'),
            'x_frame_search_frame_code':        _str('x_frame_search_frame_code'),
            'x_frame_search_packaging_bag':     _str('x_frame_search_packaging_bag'),
            'x_frame_search_shipping_date':     _date('x_frame_search_shipping_date'),
            'x_frame_search_courier':           _str('x_frame_search_courier'),
            'x_frame_search_cause':             _sel('x_frame_search_cause'),
            'x_frame_search_other_specify':     _str('x_frame_search_other_specify'),

            # ── Calidad micas / armazón ───────────────────────────────────────
            'x_quality_order_number':           _str('x_quality_order_number'),
            'x_quality_customer_name':          _str('x_quality_customer_name'),
            'x_quality_customer_phone':         _str('x_quality_customer_phone'),
            'x_quality_shipping_bag':           _str('x_quality_shipping_bag'),
            'x_quality_courier_guide':          _str('x_quality_courier_guide'),
            'x_quality_evidence_attached':      _radio('x_quality_evidence_attached'),

            # ── Medallia ──────────────────────────────────────────────────────
            'x_medallia_employee_number': _str('x_medallia_employee_number'),
            'x_medallia_employee_name': _str('x_medallia_employee_name'),

            # ── Logística / mensajería ────────────────────────────────────────
            'x_bag_arrival': _str('x_bag_arrival'),
            'x_delivery_oc': _str('x_delivery_oc'),
            'x_paq_pos_order': _str('x_paq_pos_order'),

            'x_shipping_noncompliance_type': _sel('x_shipping_noncompliance_type'),
            'x_shipping_assigned_courier': _str('x_shipping_assigned_courier'),

            'x_shipping_arrival_bag': _str('x_shipping_arrival_bag'),
            'x_shipping_guide_number_detail': _str('x_shipping_guide_number_detail'),
            'x_shipping_content_detail': _str('x_shipping_content_detail'),
            'x_shipping_photo_evidence_confirmed': _radio('x_shipping_photo_evidence_confirmed'),

            'x_shipping_unreceived_pos_order': _str('x_shipping_unreceived_pos_order'),
            'x_shipping_unreceived_arrival_bag': _str('x_shipping_unreceived_arrival_bag'),
            'x_shipping_unreceived_transport': _str('x_shipping_unreceived_transport'),

            'x_shipping_lab_followup_pos_order': _str('x_shipping_lab_followup_pos_order'),

            'x_shipping_extraordinary_pos_order': _str('x_shipping_extraordinary_pos_order'),
            'x_shipping_extraordinary_sap_center': _str('x_shipping_extraordinary_sap_center'),
            'x_shipping_extraordinary_manager_authorization': _radio('x_shipping_extraordinary_manager_authorization'),

            # accesorios
            'x_shipping_missing_accessory_order': _str('x_shipping_missing_accessory_order'),
            'x_shipping_missing_accessory_bag': _str('x_shipping_missing_accessory_bag'),
            'x_shipping_missing_accessory_brand': _str('x_shipping_missing_accessory_brand'),
            'x_shipping_missing_accessory_arrival_date': _date('x_shipping_missing_accessory_arrival_date'),
            'x_shipping_missing_accessory_supplier': _sel('x_shipping_missing_accessory_supplier'),

            'x_shipping_missing_accessory_cloth': bool(post.get('x_shipping_missing_accessory_cloth')),
            'x_shipping_missing_accessory_case': bool(post.get('x_shipping_missing_accessory_case')),
            'x_shipping_missing_accessory_clipon': bool(post.get('x_shipping_missing_accessory_clipon')),
            'x_shipping_missing_accessory_certificate': bool(post.get('x_shipping_missing_accessory_certificate')),

            # mercancía
            'x_prev_guide_number': _str('x_prev_guide_number'),
            'x_prev_courier_type': _sel('x_prev_courier_type'),
            'x_prev_photo_evidence_confirm': _radio('x_prev_photo_evidence_confirm'),

            # ── Reportes ──────────────────────────────────────────────────────
            'x_report_whatsapp_date': _date('x_report_whatsapp_date'),
            'x_report_marketing_date': _date('x_report_marketing_date'),
            'x_report_attached': _radio('x_report_attached'),

            # ── Papelería / seguimiento ───────────────────────────────────────
            'x_supply_material_code': _str('x_supply_material_code'),
            'x_supply_material_description': _str('x_supply_material_description'),
            'x_supply_quantity': _str('x_supply_quantity'),
            'x_supply_unit_measure': _sel('x_supply_unit_measure'),
            'x_supply_center': _str('x_supply_center'),
            'x_supply_manager_approval_attached': _radio('x_supply_manager_approval_attached'),

            # ── extras papelería ──────────────────────────────────────────────
            'x_supply_sku_code': _str('x_supply_sku_code'),
            'x_supply_frame_type': _sel('x_supply_frame_type'),
            'x_supply_frame_brand_basic': _str('x_supply_frame_brand_basic'),
            'x_supply_return_folio': _str('x_supply_return_folio'),

            # ── Laboratorio local ─────────────────────────────────────────────
            'x_lab_local_pos_order': _str('x_lab_local_pos_order'),
            'x_lab_local_promise_date': _date('x_lab_local_promise_date'),
            'x_lab_local_name': _str('x_lab_local_name'),
        })

        files = request.httprequest.files.getlist('attachments')
        for f in files:
            if f and f.filename:
                    env['helpdesk.ticket.attachment.line'].create({
                    'ticket_id': ticket.id,
                    'file':      base64.b64encode(f.read()),
                    'filename':  f.filename,
                })

        return request.redirect(f'/helpdesk/success?ticket_id={ticket.id}')

    @http.route(
        ['/helpdesk/success', '/<string:lang>/helpdesk/success'],
        type='http', auth='public', website=True
    )
    def helpdesk_success(self, ticket_id=None, **kwargs):
        return request.render('helpdesk_web_form.helpdesk_success_template', {
            'ticket_id': ticket_id,
        })