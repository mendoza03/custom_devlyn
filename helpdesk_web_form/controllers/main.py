from odoo import http
from odoo.http import request


class HelpdeskController(http.Controller):

    @http.route(['/helpdesk', '/<string:lang>/helpdesk'], type='http', auth='public', website=True, sitemap=True)
    def helpdesk_form(self, lang=None, **kwargs):
        sections = request.env['helpdesk.section'].sudo().search([('active', '=', True)])
        return request.render('helpdesk_web_form.helpdesk_form_template', {
            'sections': sections,
        })

    @http.route(
        ['/helpdesk/categories', '/<string:lang>/helpdesk/categories'],
        type='http', auth='public', methods=['POST'], csrf=False, website=True
    )
    def helpdesk_categories(self, lang=None, **post):
        section_id = int(post.get('section_id') or 0)
        cats = request.env['helpdesk.ticket.category'].sudo().search([
            ('section_id', '=', section_id),
            ('active', '=', True),
        ])
        return request.make_json_response([{
            'id': c.id,
            'name': c.name,
        } for c in cats])

    @http.route(
        ['/helpdesk/subcategories', '/<string:lang>/helpdesk/subcategories'],
        type='http', auth='public', methods=['POST'], csrf=False, website=True
    )
    def helpdesk_subcategories(self, lang=None, **post):
        category_id = int(post.get('category_id') or 0)
        subs = request.env['helpdesk.ticket.subcategory'].sudo().search([
            ('category_id', '=', category_id),
            ('active', '=', True),
        ])
        return request.make_json_response([{
            'id': s.id,
            'name': s.name,
            'code': s.code or '',
        } for s in subs])

    @http.route(
        ['/helpdesk/subcategory_info', '/<string:lang>/helpdesk/subcategory_info'],
        type='http', auth='public', methods=['POST'], csrf=False, website=True
    )
    def helpdesk_subcategory_info(self, lang=None, **post):
        subcategory_id = int(post.get('subcategory_id') or 0)
        sub = request.env['helpdesk.ticket.subcategory'].sudo().browse(subcategory_id)
        if not sub.exists():
            return request.make_json_response({'id': 0, 'code': ''})
        return request.make_json_response({
            'id': sub.id,
            'code': sub.code or '',
        })

    @http.route(
        ['/helpdesk/submit', '/<string:lang>/helpdesk/submit'],
        type='http', auth='public', methods=['POST'], website=True, csrf=True
    )
    def helpdesk_submit(self, lang=None, **post):
        def _int(v):
            try:
                return int(v) if v else False
            except Exception:
                return False

        def _sel(v):
            return v if v and v != 'select' else False

        sub_id = _int(post.get('x_subcategory_id'))
        sub = request.env['helpdesk.ticket.subcategory'].sudo().browse(sub_id) if sub_id else request.env['helpdesk.ticket.subcategory'].sudo().browse()
        sub_code = (sub.code or '') if sub and sub.exists() else ''

        values = {
            'name': post.get('x_general_description') or 'Ticket',
            'x_general_description': post.get('x_general_description') or False,
            'x_section_id': _int(post.get('x_section_id')),
            'x_category_id': _int(post.get('x_category_id')),
            'x_subcategory_id': sub_id,
            'x_detailed_description': post.get('x_detailed_description') or False,

            'x_order_number': post.get('x_order_number') or False,
            'x_bag': post.get('x_bag') or False,
            'x_customer_warehouse': _sel(post.get('x_customer_warehouse')),
            'x_order_type': _sel(post.get('x_order_type')),
            'x_lab_indicated': post.get('x_lab_indicated') or False,
            'x_shipping_guide_number': post.get('x_shipping_guide_number') or False,
            'x_frame_bag_number': post.get('x_frame_bag_number') or False,
            'x_authorized_by': post.get('x_authorized_by') or False,
            'x_order_type_adaptation': _sel(post.get('x_order_type_adaptation')),
            'x_original_order_number': post.get('x_original_order_number') or False,
            'x_job_type': post.get('x_job_type') or False,
            'x_order_type_imagen': _sel(post.get('x_order_type_imagen')),

            'x_branch_email': post.get('x_branch_email') or False,
            'x_email_issue_type_2': post.get('x_email_issue_type_2') or post.get('x_email_issue_type') or False,
            'x_contact_number': post.get('x_contact_number') or False,

            'x_internal_folio_number': post.get('x_internal_folio_number') or False,
            'x_equipment_type': _sel(post.get('x_equipment_type')),
            'x_model_or_brand': post.get('x_model_or_brand') or False,
            'x_serial_number': post.get('x_serial_number') or False,
            'x_fixed_asset_number': post.get('x_fixed_asset_number') or False,
            'x_shipping_guide': post.get('x_shipping_guide') or False,
            'x_courier': post.get('x_courier') or False,

            'x_store_number': post.get('x_store_number') or False,
            'x_interredes_user': post.get('x_interredes_user') or False,

            'x_printer_model': post.get('x_printer_model') or False,
            'x_contact_person_name': post.get('x_contact_person_name') or False,

            'x_toner_below_15': _sel(post.get('x_toner_below_15')),
            'x_cleaning_area': _sel(post.get('x_cleaning_area')),

            'partner_email': post.get('partner_email') or post.get('email') or False,
        }

        ticket = request.env['helpdesk.ticket'].sudo().with_context(tracking_disable=True).create(values)
        ticket.flush_recordset()
        ticket.invalidate_recordset()
        _ = ticket.x_subcategory_code

        import base64
        files = request.httprequest.files.getlist('attachments')
        for f in files:
            if f:
                request.env['helpdesk.ticket.attachment.line'].sudo().create({
                    'ticket_id': ticket.id,
                    'file': base64.b64encode(f.read()),
                    'filename': f.filename,
                })

        return request.redirect('/helpdesk')