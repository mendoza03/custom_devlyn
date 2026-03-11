from odoo import api, fields, models


class HelpdeskTicketAttachmentLine(models.Model):
    _name = "helpdesk.ticket.attachment.line"
    _description = "Helpdesk Ticket Attachment Line"
    _order = "id desc"

    ticket_id = fields.Many2one(
        "helpdesk.ticket",
        required=True,
        ondelete="cascade",
        index=True,
    )

    file = fields.Binary(string="Fichero", required=True)
    filename = fields.Char(string="Nombre")

    attachment_id = fields.Many2one("ir.attachment", readonly=True)

    @api.model_create_multi
    def create(self, vals_list):
        records = self.env[self._name]

        for vals in vals_list:
            if not vals.get("filename"):
                ctx_filename = self.env.context.get("filename")
                vals["filename"] = ctx_filename or "archivo_adjunto"

            rec = super(HelpdeskTicketAttachmentLine, self).create(vals)

            att = self.env["ir.attachment"].create({
                "name": rec.filename,
                "datas": rec.file,
                "type": "binary",
                "res_model": "helpdesk.ticket",
                "res_id": rec.ticket_id.id,
            })

            rec.attachment_id = att.id
            records |= rec

        return records