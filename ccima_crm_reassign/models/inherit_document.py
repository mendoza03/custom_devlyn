from odoo import models, api
import re

class MailActivity(models.Model):
    _inherit = 'mail.activity'

    @api.model_create_multi
    def create(self, vals_list):
        activities = super().create(vals_list)

        for activity in activities:
            if activity.res_model == 'crm.lead' and activity.res_id and activity.note:
                lead = self.env['crm.lead'].browse(activity.res_id)

                if lead.property_id and lead.property_id.carpet_id:
                    folder_id = lead.property_id.carpet_id.id

                    attachment_ids = self._extract_attachment_ids_from_note(activity.note)

                    attachments = self.env['ir.attachment'].browse(attachment_ids)

                    for attachment in attachments:
                        if not attachment.datas:
                            continue

                        self.env['documents.document'].create({
                            'name': attachment.name,
                            'datas': attachment.datas,
                            'mimetype': attachment.mimetype,
                            'res_model': 'crm.lead',
                            'res_id': lead.id,
                            'folder_id': folder_id,
                            'owner_id': self.env.ref('base.user_root').id,
                            'type': 'binary',
                            'access_internal': 'view',
                        })

            if activity.res_model == 'property.reservation' and activity.res_id and activity.note:
                order = self.env['property.reservation'].browse(activity.res_id)

                if order.order_id.opportunity_id and order.order_id.opportunity_id.property_id.carpet_id and order.order_id.opportunity_id.property_id:
                    folder_id = order.carpet_id.id

                    attachment_ids = self._extract_attachment_ids_from_note(activity.note)

                    attachments = self.env['ir.attachment'].browse(attachment_ids)

                    for attachment in attachments:
                        if not attachment.datas:
                            continue

                        self.env['documents.document'].create({
                            'name': attachment.name,
                            'datas': attachment.datas,
                            'mimetype': attachment.mimetype,
                            'res_model': 'property.reservation',
                            'res_id': order.id,
                            'folder_id': folder_id,
                            'owner_id': self.env.ref('base.user_root').id,
                            'type': 'binary',
                            'access_internal': 'view',
                        })

        return activities

    def _extract_attachment_ids_from_note(self, note_html):
        attachment_ids = []
        matches = re.findall(r'/web/content/(\d+)\?', note_html)
        for match in matches:
            try:
                attachment_ids.append(int(match))
            except ValueError:
                continue
        return attachment_ids