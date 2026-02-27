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
        return request.make_json_response([{'id': s.id, 'name': s.name} for s in subs])

    @http.route(['/helpdesk/submit', '/<string:lang>/helpdesk/submit'], type='http', auth='public', methods=['POST'], website=True)
    def helpdesk_submit(self, **post):
        ticket = request.env['helpdesk.ticket'].sudo().create({
            'name': post.get('x_general_description'),
            'x_general_description': post.get('x_general_description'),
            'x_section_id': int(post.get('x_section_id')) if post.get('x_section_id') else False,
            'x_category_id': int(post.get('x_category_id')) if post.get('x_category_id') else False,
            'x_subcategory_id': int(post.get('x_subcategory_id')) if post.get('x_subcategory_id') else False,
            'x_detailed_description': post.get('x_detailed_description'),
            'partner_email': post.get('email'),
        })

        import base64
        files = request.httprequest.files.getlist('attachments')
        for f in files:
            if f:
                request.env['helpdesk.ticket.attachment.line'].sudo().create({
                    'ticket_id': ticket.id,
                    'file': base64.b64encode(f.read()),
                    'filename': f.filename,
                })

        return request.redirect(request.httprequest.referrer or '/helpdesk')