from odoo import fields, models


class HelpdeskCancelTicketWizard(models.TransientModel):
    _name = 'helpdesk.cancel.ticket.wizard'
    _description = 'Cancel Helpdesk Ticket Wizard'

    ticket_id = fields.Many2one(
        'helpdesk.ticket',
        string='Ticket',
        required=True,
        readonly=True,
    )
    user_id = fields.Many2one(
        'res.users',
        string='Cancelled By',
        default=lambda self: self.env.user,
        required=True,
        readonly=True,
    )
    reason_id = fields.Many2one(
        'helpdesk.cancel.reason',
        string='Cancellation Reason',
        required=True,
        domain=[('active', '=', True)],
    )
    note = fields.Text(
        string='Internal Note',
        help='Optional internal note explaining the cancellation.',
    )

    def action_confirm_cancel(self):
        self.ensure_one()
        self.ticket_id.action_cancel_ticket_with_reason(
            reason=self.reason_id,
            note=self.note,
        )
        return {'type': 'ir.actions.act_window_close'}
