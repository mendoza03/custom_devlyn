# -*- coding: utf-8 -*-
from odoo import models, fields, api


class ProductTemplate(models.Model):
    _inherit = 'product.template'

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------

    inactive_date = fields.Date(
        string="Inactive Date",
        readonly=True,
        copy=False,
        help="Date when the property was marked as inactive"
    )
    inactive_month = fields.Char(
        string="Inactive Month",
        compute="_compute_inactive_month",
        store=True,
        copy=False,
        help="Month and year of inactivation in format 'January 2026'"
    )
    lead_partner_id = fields.Many2one(
        'res.partner',
        string="Lead Customer",
        compute="_compute_lead_partner",
        store=False,
        copy=False,
        help="Customer associated with the lead linked to this property"
    )
    closing_date = fields.Date(
        string="Closing Date",
        help="Expected closing or delivery date for this property"
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends('inactive_date')
    def _compute_inactive_month(self):
        month_names = {
            1: 'January', 2: 'February', 3: 'March', 4: 'April',
            5: 'May', 6: 'June', 7: 'July', 8: 'August',
            9: 'September', 10: 'October', 11: 'November', 12: 'December'
        }
        for record in self:
            if record.inactive_date:
                month_name = month_names.get(record.inactive_date.month, '')
                record.inactive_month = f"{month_name} {record.inactive_date.year}"
            else:
                record.inactive_month = ''

    def _compute_lead_partner(self):
        for record in self:
            partner = False
            if hasattr(record, 'lead') and record.lead:
                partner = record.lead.partner_id if record.lead.partner_id else False
            record.lead_partner_id = partner

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------

    def write(self, vals):
        if 'state' in vals:
            for record in self:
                if vals['state'] == 'inactive' and not record.inactive_date:
                    vals['inactive_date'] = fields.Date.today()
        return super(ProductTemplate, self).write(vals)