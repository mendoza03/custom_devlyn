# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import api, models, fields, _


class UpdateLastOdometer(models.TransientModel):
    """To Update Last Odometer Readings in Rental Equipment"""
    _name = 'update.last.odometer'
    _description = __doc__

    contract_id = fields.Many2one('rent.order')
    equipment_ids = fields.Many2many('renting.items',
                                     compute='_compute_equipment_ids',
                                     string='Available Equipments')
    equipment_id = fields.Many2one('renting.items', "Equipment",
                                   domain="[('id', 'in', equipment_ids)]")
    current_odometer_reading = fields.Float("Current Readings")
    unit = fields.Selection(related='equipment_id.product_id.odometer_unit',
                            string="Unit")
    last_odometer_reading = fields.Float('Last Readings',
                                         compute='_compute_last_odometer_reading')

    @api.model
    def default_get(self, fields_list):
        res = super(UpdateLastOdometer, self).default_get(fields_list)
        active_id = self._context.get('active_id')
        contract_id = self.env['rent.order'].sudo().search([('id', '=', active_id)])
        if active_id:
            res['contract_id'] = contract_id.id
        return res

    @api.depends('equipment_id')
    def _compute_equipment_ids(self):
        """Compute equipment"""
        for rec in self:
            vehicles = []
            for data in rec.contract_id.renting_items_ids:
                if data.product_id.is_vehicle and not data.equipment_odometer_id:
                    vehicles.append(data.id)
            rec.equipment_ids = vehicles

    @api.depends('equipment_id')
    def _compute_last_odometer_reading(self):
        """Compute last odometer reading"""
        for rec in self:
            reading = 0
            odometer_record = self.env['equipment.odometer'].sudo().search(
                [('product_id', '=', rec.equipment_id.product_id.id)], order="create_date DESC", limit=1)
            if odometer_record:
                reading = odometer_record.current_readings
            rec.last_odometer_reading = reading

    def update_readings(self):
        """Update Reading"""
        equipment_odometer = self.env['equipment.odometer'].sudo()
        if self.equipment_id:
            if self.current_odometer_reading < self.last_odometer_reading:
                raise ValidationError(_('Current reading can not be less than last reading.'))
            data = {
                'product_id': self.equipment_id.product_id.id,
                'current_readings': self.current_odometer_reading,
                'last_readings': self.last_odometer_reading,
                'unit': self.unit
            }
            equipment_odometer_id = equipment_odometer.create(data)
            self.equipment_id.write({
                'equipment_odometer_id': equipment_odometer_id.id
            })
