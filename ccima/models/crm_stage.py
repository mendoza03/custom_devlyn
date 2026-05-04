# -*- coding: utf-8 -*-
from typing import Dict

from odoo import models, fields, api # type: ignore


class CrmStage(models.Model):
    _inherit = 'crm.stage'

    background_color = fields.Char(string='Background color')
    text_color = fields.Char(string='Text color', default='#000000')
    short_name = fields.Char(string='Short name')
    need_partner_id_to_move = fields.Boolean(string="Need partner to move")
    need_email_to_move = fields.Boolean(string="Need email to move")
    need_phone_to_move = fields.Boolean(string="Need phone to move")
    need_origin_to_move = fields.Boolean(string="Need origin to move")
    need_salesman_to_move = fields.Boolean(string="Need salesman to move")
    need_company_to_move = fields.Boolean(string="Need company to move")
    need_title_to_move = fields.Boolean(string="Need title to move")
    need_address_to_move = fields.Boolean(string="Need address to move")
    need_job_position = fields.Boolean(string="Need Job position")
    need_property_id = fields.Boolean(string="Need property")
    need_date_deadline = fields.Boolean(string="Need date deadline")
    need_at_least_one_quote = fields.Boolean(string="Need at least one quotation")

    #* ---------------------------------------------------------
    #*  HELPERS
    #* ---------------------------------------------------------
    @api.model
    def _stage_restrictions(self) -> Dict[str, bool]:
        self.ensure_one()
        restrictions: Dict[str, bool] = {}
        if self.need_partner_id_to_move:
            restrictions['partner_id'] = True
        if self.need_email_to_move:
            restrictions['email_from'] = True
        if self.need_phone_to_move:
            restrictions['phone'] = True
        if self.need_origin_to_move:
            restrictions['source_id'] = True
        if self.need_salesman_to_move:
            restrictions['user_id'] = True
        if self.need_company_to_move:
            restrictions['partner_name'] = True
        if self.need_title_to_move:
            restrictions['title'] = True
        if self.need_address_to_move:
            restrictions['street'] = True
        if self.need_job_position:
            restrictions['function'] = True
        if self.need_property_id:
            restrictions['property_id'] = True
        if self.need_date_deadline:
            restrictions['date_deadline'] = True
        if self.need_at_least_one_quote:
            restrictions['order_ids'] = True
        return restrictions
