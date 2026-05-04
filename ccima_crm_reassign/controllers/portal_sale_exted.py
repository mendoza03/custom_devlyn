from odoo import http, fields
from odoo.http import request
import binascii

class PortalSignatureCustom(http.Controller):

    @http.route('/product_layout/view/<int:design_id>', type='http', auth='user', website=True)
    def view_layout_html(self, design_id, **kwargs):
        design = request.env['product.layout.design'].sudo().browse(design_id)
        return request.render('ccima_crm_reassign.product_layout_html_template', {
            'design': design,
        })

    @http.route(['/my/orders/<int:order_id>/accept'], type='json', auth="public", website=True)
    def portal_quote_accept(self, order_id, name=None, signature=None, legal_status_template_id=None, **kwargs):

        order = request.env['sale.order'].sudo().browse(order_id)
        if not order.exists():
            return {'error': 'Order not found'}

        try:
            order.write({
                'signed_by': name,
                'signed_on': fields.Datetime.now(),
                'signature': signature,
            })

            if legal_status_template_id:
                order.legal_status_template_id = int(legal_status_template_id)

            request.env.cr.commit()
        except (TypeError, binascii.Error) as e:
            return {'error': 'Invalid signature or data'}

        query_string = '&message=sign_ok'
        if order._has_to_be_paid():
            query_string += '&allow_payment=yes'

        return {
            'force_refresh': True,
            'redirect_url': order.get_portal_url(query_string=query_string),
        }
