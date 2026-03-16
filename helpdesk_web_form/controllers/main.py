import base64

from odoo import http
from odoo.http import request


class HelpdeskController(http.Controller):

    @http.route(['/helpdesk', '/<string:lang>/helpdesk'], type='http', auth='public', website=True)
    def helpdesk_form(self, **kwargs):
        sections = request.env['helpdesk.section'].sudo().search([('active', '=', True)])
        return request.render('helpdesk_web_form.helpdesk_form_template', {'sections': sections})

    @http.route(
        ['/helpdesk/categories', '/<string:lang>/helpdesk/categories'],
        type='http', auth='public', methods=['POST'], csrf=False, website=True
    )
    def helpdesk_categories(self, **post):
        section_id = int(post.get('section_id') or 0)
        cats = request.env['helpdesk.ticket.category'].sudo().search([
            ('section_id', '=', section_id),
            ('active', '=', True),
        ])
        return request.make_json_response([{'id': c.id, 'name': c.name} for c in cats])

    @http.route(
        ['/helpdesk/subcategories', '/<string:lang>/helpdesk/subcategories'],
        type='http', auth='public', methods=['POST'], csrf=False, website=True
    )
    def helpdesk_subcategories(self, **post):
        category_id = int(post.get('category_id') or 0)
        subs = request.env['helpdesk.ticket.subcategory'].sudo().search([
            ('category_id', '=', category_id),
            ('active', '=', True),
        ])
        # Incluimos el "code" para que el JS pueda identificar qué bloque mostrar
        return request.make_json_response([
            {'id': s.id, 'name': s.name, 'code': s.code or ''}
            for s in subs
        ])

    @http.route(
        ['/helpdesk/submit', '/<string:lang>/helpdesk/submit'],
        type='http', auth='public', methods=['POST'], website=True
    )
    def helpdesk_submit(self, **post):

        def _int(key):
            val = post.get(key)
            return int(val) if val else False

        def _str(key):
            val = post.get(key, '').strip()
            return val if val else False

        def _sel(key):
            """Devuelve el valor del selection, o 'select' si no viene."""
            return post.get(key) or 'select'

        ticket = request.env['helpdesk.ticket'].sudo().create({
            # ── Campos base ───────────────────────────────────────────────────
            'name':                     post.get('x_general_description'),
            'x_general_description':    post.get('x_general_description'),
            'x_section_id':             _int('x_section_id'),
            'x_category_id':            _int('x_category_id'),
            'x_subcategory_id':         _int('x_subcategory_id'),
            'x_detailed_description':   post.get('x_detailed_description'),
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
        })

        # ── Adjuntos ──────────────────────────────────────────────────────────
        files = request.httprequest.files.getlist('attachments')
        for f in files:
            if f and f.filename:
                request.env['helpdesk.ticket.attachment.line'].sudo().create({
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