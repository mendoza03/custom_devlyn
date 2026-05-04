# -*- coding: utf-8 -*-

from odoo import fields, models
from dateutil.relativedelta import relativedelta

import logging

_logger = logging.getLogger(__name__)


class PropertyReservation(models.Model):
    _inherit = 'property.reservation'

    def action_confirm(self):
        result = super().action_confirm()
        for reservation in self:
            reservation_date = False
            if reservation.date:
                reservation_date = fields.Datetime.to_datetime(reservation.date).date()

            vals = {
                'property_date': reservation_date,
            }

            if (
                'month_deliver' in reservation.property_id._fields
                and 'date_deliver' in reservation.property_id._fields
            ):
                month_deliver = reservation.property_id.month_deliver or 0
                vals['date_deliver'] = (
                    reservation_date + relativedelta(months=month_deliver)
                    if reservation_date else False
                )

            reservation.property_id.write(vals)
        return result

    def action_cancel(self):
        result = super().action_cancel()
        self.property_id.write({
            'property_date': False,
        })
        return result
