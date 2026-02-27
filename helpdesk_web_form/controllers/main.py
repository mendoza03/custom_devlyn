from odoo import http
from odoo.http import request

class HelpdeskController(http.Controller):

    @http.route(['/helpdesk'], type='http', auth='public', website=True)
    def helpdesk_form(self, **kwargs):
        teams = request.env['helpdesk.team'].sudo().search([])

        return request.render('helpdesk_web_form.helpdesk_form_template', {
            'teams': teams,
        })

    @http.route('/helpdesk/submit', type='http', auth='public', methods=['POST'], website=True, csrf=False)
    def helpdesk_submit(self, **post):

        request.env['helpdesk.ticket'].sudo().create({
            'name': post.get('name'),
            'description': post.get('description'),
            'partner_email': post.get('email'),
            'team_id': int(post.get('team_id')) if post.get('team_id') else False,
        })

        return request.redirect('/helpdesk/thanks')