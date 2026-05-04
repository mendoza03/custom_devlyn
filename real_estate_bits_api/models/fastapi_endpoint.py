# -*- coding: utf-8 -*-

from odoo import fields, models
from fastapi import APIRouter

from ..routers import real_estate_router

import logging

_logger = logging.getLogger(__name__)


class FastapiEndpoint(models.Model):
    _inherit = 'fastapi.endpoint'

    app = fields.Selection(
        selection_add=[
            ('real_estate', 'Real Estate'),
        ], ondelete={'real_estate': 'cascade'}
    )

    real_estate_api_key = fields.Char(string="API Key", help="API Key to access the real estate endpoints.")

    def _get_fastapi_routers(self) -> list[APIRouter]:
        if self.app == 'real_estate':
            return [real_estate_router]
        return super()._get_fastapi_routers()