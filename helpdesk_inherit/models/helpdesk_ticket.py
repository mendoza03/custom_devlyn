from odoo import _, fields, models
from odoo.exceptions import UserError


class HelpdeskTicket(models.Model):
    _inherit = 'helpdesk.ticket'

    cancel_reason_id = fields.Many2one(
        'helpdesk.cancel.reason',
        string='Cancellation Reason',
        readonly=True,
        copy=False,
        tracking=True,
    )
    cancelled_by_id = fields.Many2one(
        'res.users',
        string='Cancelled By',
        readonly=True,
        copy=False,
        tracking=True,
    )
    cancelled_date = fields.Datetime(
        string='Cancelled On',
        readonly=True,
        copy=False,
        tracking=True,
    )
    cancel_note = fields.Text(
        string='Cancellation Note',
        readonly=True,
        copy=False,
    )
    is_cancelled = fields.Boolean(
        string='Cancelled',
        compute='_compute_is_cancelled',
        store=True,
    )

    def _get_cancel_stage(self):
        stage = self.env['helpdesk.stage'].search([
            '|',
            ('fold', '=', True),
            ('name', 'ilike', 'cancel'),
        ], order='sequence desc, id desc', limit=1)

        if not stage:
            raise UserError(_(
                'No cancelled/closed Helpdesk stage was found. '
                'Please create or configure a folded Helpdesk stage first.'
            ))

        return stage

    def _compute_is_cancelled(self):
        for ticket in self:
            ticket.is_cancelled = bool(ticket.cancel_reason_id and ticket.cancelled_date)

    def action_open_cancel_wizard(self):
        self.ensure_one()

        if self.is_cancelled:
            raise UserError(_('This ticket is already cancelled.'))

        return {
            'type': 'ir.actions.act_window',
            'name': _('Cancel Ticket'),
            'res_model': 'helpdesk.cancel.ticket.wizard',
            'view_mode': 'form',
            'target': 'new',
            'context': {
                'default_ticket_id': self.id,
                'default_user_id': self.env.user.id,
            },
        }

    def action_cancel_ticket_with_reason(self, reason, note=False):
        self.ensure_one()

        if not self.env.user.has_group('helpdesk_inherit.group_helpdesk_cancel_manager'):
            raise UserError(_('You are not allowed to cancel Helpdesk tickets.'))

        if self.is_cancelled:
            raise UserError(_('This ticket is already cancelled.'))

        if not reason or not reason.active:
            raise UserError(_('Please select an active cancellation reason.'))

        cancel_stage = self._get_cancel_stage()
        now = fields.Datetime.now()

        self.write({
            'stage_id': cancel_stage.id,
            'cancel_reason_id': reason.id,
            'cancelled_by_id': self.env.user.id,
            'cancelled_date': now,
            'cancel_note': note or False,
        })

        message = _(
            '<b>Ticket cancelled</b><br/>'
            '<b>Reason:</b> %(reason)s<br/>'
            '<b>Cancelled by:</b> %(user)s<br/>'
            '<b>Cancelled on:</b> %(date)s'
        ) % {
            'reason': reason.display_name,
            'user': self.env.user.display_name,
            'date': fields.Datetime.to_string(now),
        }

        if note:
            message += _('<br/><b>Note:</b> %s') % note

        self.message_post(body=message)

        return True
