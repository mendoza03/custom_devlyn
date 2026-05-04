from odoo import models, fields

class SaleOrder(models.Model):
    _inherit = 'property.reservation'

    carpet_id = fields.Many2one('documents.document', string='Document', ondelete='cascade')

    def action_confirm(self):
        res = super().action_confirm()

        sign_template = self.env['sign.template'].browse(24)

        for order in self:
            if not order.partner_id.email:
                continue


            reference = f"Firma Pedido {order.name}"

            signature_items = sign_template.sign_item_ids.filtered(
                lambda i: i.type_id.item_type == 'signature' and i.responsible_id
            )

            unique_roles = list({item.responsible_id.id: item.responsible_id for item in signature_items}.values())

            signature_request_items = []

            for role in unique_roles:
                if role.name.lower() == 'cliente':
                    partner = order.partner_id
                elif role.name.lower() == 'usuario':
                    partner = self.env.user.partner_id
                else:
                    continue

                if not partner or not partner.email:
                    continue

                signature_request_items.append((0, 0, {
                    'partner_id': partner.id,
                    'role_id': role.id,
                }))

            if order.order_id:
                if order.order_id.opportunity_id:
                    stage = self.env['crm.stage'].search([('name', '=', 'Apartado')], limit=1)
                    if stage:
                        order.order_id.opportunity_id.write({
                            'stage_id': stage.id,
                        })

                    
            if signature_request_items:
                signature_request = self.env['sign.request'].create({
                    'template_id': sign_template.id,
                    'request_item_ids': signature_request_items,
                    'reference': reference,
                })

                if order.order_id:
                    if order.order_id.opportunity_id:
                        if order.order_id.opportunity_id.property_id:
                            doc_id = self.env['documents.document'].create({
                                'name': self.partner_id.name,
                                "owner_id": self.env.ref('base.user_root').id,
                                "type": "folder",
                                "access_internal": "view",
                                'folder_id': order.order_id.opportunity_id.property_id.carpet_id.id,
                            })

                            order.update({
                                'carpet_id': doc_id.id,
                            })


            partner_name = order.partner_id.name
            email_to = order.partner_id.email
            hitch_text = f"${self.deposit:,.2f}"
            body_html = f"""
                <p>Hola {partner_name},</p>
                <p>¡Excelente elección! Hemos recibido tu selección de financiamiento y estamos listos para continuar con el siguiente paso.</p>
                <p>Para proceder con el apartado de tu unidad, te pedimos realizar el pago inicial de <strong>{hitch_text}</strong> MXN. 
                Junto con esto, adjuntamos una carta de cotización que necesitamos que firmes y nos devuelvas,
                junto con tu INE y el comprobante de pago del apartado escaneados en formato PDF.</p>
                <p>Una vez que recibamos estos documentos, procederemos a bloquear tu unidad y te enviaremos un mensaje de bienvenida confirmando el apartado.</p>
                <p>¡Gracias por tu confianza! Estamos aquí para cualquier duda.</p>
                <p><strong>Equipo Comercial de Grupo CCIMA</strong></p>
            """

            if email_to:
                self.env['mail.mail'].sudo().create({
                    'subject': 'Intencion de compra',
                    'email_to': email_to,
                    'body_html': body_html,
                }).send()

            self.property_id.write({"partner_id": self.partner_id.id})

        return res

class SaleOrder(models.Model):
    _inherit = 'sale.order'

    legal_status = fields.Char(string="Legal Status")
    legal_status_template_id = fields.Many2one('sign.template', string="Personería jurídica")

    def write(self, vals):
        res = super().write(vals)

        if 'legal_status_template_id' in vals:
            for order in self:
                template_id = vals['legal_status_template_id']
                if template_id:
                    lead = order.opportunity_id
                    if not lead:
                        lead = self.env['crm.lead'].search([('order_ids', 'in', order.id)], limit=1)

                    if lead:
                        lead.legal_personality = int(template_id)
        return res
