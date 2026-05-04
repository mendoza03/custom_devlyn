# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class EquipmentImage(models.Model):
    """Equipment Image"""
    _name = 'equipment.image'
    _description = __doc__
    _rec_name = 'name'

    avatar = fields.Binary(string="Avatar")
    name = fields.Char(string="Name", required=True, translate=True, size=23)
    product_id = fields.Many2one('product.product', ondelete='cascade')
    product_template_id = fields.Many2one('product.template', ondelete='cascade')


class EquipmentRentingInfo(models.Model):
    """Equipment Renting Info"""
    _name = 'equipment.renting.info'
    _description = __doc__
    _rec_name = 'rate_name'

    rate_name = fields.Char(string="Title", required=True)
    range = fields.Selection([
        ('hour', "Per Hour"),
        ('day', "Per Day"),
        ('week', "Per Week"),
        ('month', "Per Month"),
        ('year', "Per Year")],
        string="Length")
    renting_day = fields.Integer(string="Days")
    renting_hours = fields.Integer(string="Hours")
    rate = fields.Monetary(string="Price")
    extra_hour_price = fields.Monetary(string="Extra Hour Price")
    company_id = fields.Many2one('res.company',
                                 default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency',
                                  string='Currency',
                                  related="company_id.currency_id")
    product_id = fields.Many2one('product.product', ondelete='cascade')
    product_template_id = fields.Many2one('product.template', ondelete='cascade')

    @api.constrains('renting_day')
    def _check_renting_day(self):
        for record in self:
            if not record.renting_day:
                raise ValidationError(_("Please include the number of days in the pricing details tab"))

    @api.constrains('renting_hours')
    def _check_renting_hours(self):
        for record in self:
            if not record.renting_hours:
                raise ValidationError(_("Kindly include the hours in the pricing details tab"))


class RentingProductTemplate(models.Model):
    """Renting Product Template"""
    _inherit = "product.template"
    _description = __doc__

    can_be_rental = fields.Boolean(string="Can be Rental")
    is_vehicle = fields.Boolean(string='Is Vehicle')
    serial_number = fields.Char(string="Serial Number")
    life_span = fields.Char(string="Lifespan(Year)")
    date_of_purchase = fields.Date(string="Date of Purchase")
    equipment_value = fields.Monetary(string="Equipment Value")
    starting_profit = fields.Monetary(string="Starting Profit")

    hours_count = fields.Float(string="Total Hours", compute="_compute_equipment_hour_count")
    maintenance_count = fields.Integer(string="Maintenance", compute='_compute_maintenance_count')
    request_count = fields.Integer(string="Request", compute='_compute_request_count')

    equipment_image_ids = fields.One2many(comodel_name='equipment.image',
                                          inverse_name='product_template_id')
    equipment_renting_info_ids = fields.One2many(comodel_name='equipment.renting.info',
                                                 inverse_name='product_template_id')


class RentingProduct(models.Model):
    """Renting Product"""
    _inherit = "product.product"
    _inherits = {'product.template': 'product_tmpl_id'}
    _description = __doc__

    hours_count = fields.Float(string="Total Hours",
                               compute="_compute_equipment_hour_count")
    maintenance_count = fields.Integer(string="Maintenance",
                                       compute='_compute_maintenance_count')
    request_count = fields.Integer(string="Request",
                                   compute='_compute_request_count')
    maintenance_equipment_id = fields.Many2one('maintenance.equipment',
                                               string="Maintenance Equip")
    last_odometer_val = fields.Float(string='Last Odometer',
                                     compute='_compute_last_odometer_val')
    odometer_unit = fields.Selection(
        [('kilometer', 'km'), ('miles', 'mi')],
        default='kilometer')
    odometer_count = fields.Integer(compute='_compute_odometer_count')
    maintenance_hours = fields.Float(string='Maintenance Hours')
    equipment_image_ids = fields.One2many(comodel_name='equipment.image',
                                          inverse_name='product_id')
    equipment_renting_info_ids = fields.One2many(comodel_name='equipment.renting.info',
                                                 inverse_name='product_id')

    @api.depends('odometer_count')
    def _compute_odometer_count(self):
        """Compute Odometer Count"""
        for rec in self:
            rec.odometer_count = self.env['equipment.odometer'].sudo().search_count([('product_id', '=', rec.id)])

    @api.depends('last_odometer_val')
    def _compute_last_odometer_val(self):
        """Compute Last Odometer Value"""
        for rec in self:
            reading = 0
            last_record = self.env['equipment.odometer'].sudo().search([('product_id', '=', rec.id)],
                                                                       order='create_date DESC', limit=1)
            if last_record:
                reading = last_record.current_readings
            rec.last_odometer_val = reading

    def action_equipment_odometer_views(self):
        """Equipment Odometer Views"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Equipment Odometers'),
            'res_model': 'equipment.odometer',
            'domain': [('product_id', 'in', self.ids)],
            'view_mode': 'list',
            'view_id': self.env.ref('tk_rental.equipment_odometer_view_list').id,
            'search_view_id': self.env.ref('tk_rental.equipment_odometer_search_view').id,
            'target': 'current',
        }

    @api.depends('hours_count')
    def _compute_equipment_hour_count(self):
        """Compute Equipment Hours"""
        hours_count = 0.0
        for rec in self:
            hours_count = self.env['renting.items'].sudo().search(
                [('product_id', 'in', rec.ids), ('status', '=', 'close')]).mapped('total_hours')
        hours_count = sum(hours_count)
        self.hours_count = hours_count

    def action_equipment_hours_views(self):
        """Equipment Hours"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Total Hours'),
            'res_model': 'renting.items',
            'domain': [('product_id', 'in', self.ids), ('status', '=', 'close')],
            'view_mode': 'list,form',
            'views': [(self.env.ref('tk_rental.renting_items_list_view').id, 'list'),
                      (self.env.ref('tk_rental.renting_items_form_view').id, 'form')],
            'target': 'current',
        }

    def action_create_maintenance(self):
        """Create Maintenance"""
        data = {
            'name': self.name,
            'product_id': self.id,
        }
        maintenance_equipment_id = self.env['maintenance.equipment'].create(data)
        self.maintenance_equipment_id = maintenance_equipment_id.id
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance Equipment'),
            'res_model': 'maintenance.equipment',
            'res_id': maintenance_equipment_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def _compute_maintenance_count(self):
        """Maintenance Count"""
        for rec in self:
            rec.maintenance_count = self.env['maintenance.equipment'].search_count([('product_id', '=', rec.id)])

    def action_maintenances_view(self):
        """Maintenance View"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Maintenance'),
            'res_model': 'maintenance.equipment',
            'view_mode': 'kanban,list,form',
            'target': 'current',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
            },
        }

    def _compute_request_count(self):
        """Compute Request Count"""
        for rec in self:
            rec.request_count = self.env['maintenance.request'].search_count([('product_id', '=', rec.id)])

    def action_maintenances_request_view(self):
        """Maintenance Request Views"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Requests'),
            'res_model': 'maintenance.request',
            'view_mode': 'kanban,list,form,pivot,graph,calendar,activity',
            'target': 'current',
            'domain': [('product_id', '=', self.id)],
            'context': {
                'default_product_id': self.id,
            },
        }
