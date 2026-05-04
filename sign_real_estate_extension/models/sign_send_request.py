# -*- coding: utf-8 -*-
from typing import Union
from ..tools.logger_config import configure_logger

from odoo import models, fields, api, Command  # type: ignore

_logger = configure_logger()


class SignSendRequestRealEstate(models.TransientModel):
    _inherit = 'sign.send.request'

    opportunity_id = fields.Many2one(
        'crm.lead',
        string='Opportunity',
        domain="[('user_id', '=', uid)]",
    )

    sale_order_id = fields.Many2one(
        'sale.order',
        string='Quotation',
        domain="[('opportunity_id', '=', opportunity_id)]",
    )

    finance_time = fields.Selection(
        [('10', '10'), ('15', '15'), ('20', '20')],
        string='financing modality',
        default='10',
    )

    property_contract_id = fields.Many2one(
        'property.contract',
        string='Property Contract',
    )


    # ---------------------------------------------------------
    # OVERRIDDEN FUNCTIONS
    # ---------------------------------------------------------
    def create_request(self):
        template_id = self.template_id.id
        if self.signers_count:
            signers = [
                {
                    'partner_id': signer.partner_id.id,
                    'role_id': signer.role_id.id,
                    'mail_sent_order': signer.mail_sent_order,
                }
                for signer in self.signer_ids
            ]
        else:
            signers = [
                {
                    'partner_id': self.signer_id.id,
                    'role_id': self.env.ref('sign.sign_item_role_default').id,
                    'mail_sent_order': self.signer_ids.mail_sent_order,
                }
            ]
        cc_partner_ids = self.cc_partner_ids.ids
        reference = self.filename
        subject = self.subject
        message = self.message
        message_cc = self.message_cc
        attachment_ids = self.attachment_ids
        sign_request = self.env['sign.request'].create(
            {
                'template_id': template_id,
                'opportunity_id': self.opportunity_id.id,
                'sale_order_id': self.sale_order_id.id,
                'finance_time': self.finance_time,
                'property_contract_id': self.property_contract_id.id,
                'request_item_ids': [
                    Command.create(
                        {
                            'partner_id': signer['partner_id'],
                            'role_id': signer['role_id'],
                            'mail_sent_order': signer['mail_sent_order'],
                        }
                    )
                    for signer in signers
                ],
                'reference': reference,
                'subject': subject,
                'message': message,
                'message_cc': message_cc,
                'attachment_ids': [Command.set(attachment_ids.ids)],
                'validity': self.validity,
                'reminder': self.reminder,
                'reminder_enabled': self.reminder_enabled,
                'reference_doc': self.reference_doc,
            }
        )
        sign_request.message_subscribe(partner_ids=cc_partner_ids)
        sign_request.update_partner_id_property_values()
        return sign_request
