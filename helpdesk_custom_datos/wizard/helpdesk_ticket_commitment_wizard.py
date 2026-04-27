from odoo import fields, models, _
from odoo.exceptions import UserError


class HelpdeskTicketCommitmentWizard(models.TransientModel):
    _name = "helpdesk.ticket.commitment.wizard"
    _description = "Helpdesk Ticket Commitment Wizard"

    ticket_id = fields.Many2one("helpdesk.ticket", string="Ticket", required=True)
    commitment_date = fields.Date(string="Fecha compromiso", required=True)

    def action_confirm(self):
        self.ensure_one()
        if not self.ticket_id:
            raise UserError(_("No se encontró el ticket a actualizar."))

        self.ticket_id._change_stage(
            "helpdesk.stage_in_progress",
            {"In Progress", "En proceso de solución"},
            extra_vals={"x_commitment_date": self.commitment_date},
        )
        return {"type": "ir.actions.act_window_close"}
