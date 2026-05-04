# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import models, fields, api, _


class RentingItemsImage(models.Model):
    """Renting Items Image"""
    _name = 'renting.items.image'
    _description = __doc__
    _rec_name = 'name'

    avatar = fields.Binary(string="Avatar")
    name = fields.Char(string="Name", required=True,
                       translate=True, size=23)
    renting_items_id = fields.Many2one('renting.items',
                                       ondelete='cascade')


class RentingItems(models.Model):
    """Renting Items"""
    _name = 'renting.items'
    _description = __doc__
    _rec_name = 'product_id'

    product_ids = fields.Many2many(comodel_name="product.product", string="Booked Equipments",
                                   compute="_compute_product_ids")
    product_id = fields.Many2one('product.product', string="Equipment",
                                 domain="[('can_be_rental', '=', True), ('id', 'not in', product_ids)]",
                                 required=True)
    serial_number = fields.Char(string="Serial Number")
    product_qty = fields.Float(string="Quantity", required=True, default=1)
    description = fields.Char(string="Description", size=36)
    renting_amount = fields.Monetary(string="Renting Amount")

    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")
    rent_amount = fields.Monetary(string="Rent Amount",
                                  compute='_compute_rent_amount')
    renting_items_image_ids = fields.One2many(comodel_name='renting.items.image',
                                              inverse_name='renting_items_id',
                                              string="Image")
    equipment_renting_info_id = fields.Many2one('equipment.renting.info',
                                                string=" Rent Type",
                                                domain="[('product_id', '=', product_id)]")
    range = fields.Selection([
        ('hour', "Per Hour"), ('day', "Per Day"),
        ('week', "Per Week"), ('month', "Per Month"),
        ('year', "Per Year")], string="Rent Type")
    start_date = fields.Date(string="Start Date")
    return_date = fields.Date(string="Return Date")
    status = fields.Selection(related="rent_order_id.status", string="Status")
    total_hours = fields.Float(string="Total Hours",
                               compute="_compute_total_hours")
    rent_order_id = fields.Many2one('rent.order', ondelete='cascade')
    total_contract_days = fields.Integer(string="Contract Days",
                                         compute="_compute_total_rental_days")
    renting_days = fields.Integer(string="Renting Days")
    total_day_diff = fields.Float(string="Day Difference",
                                  compute='_compute_total_day_diff')
    is_any_extra_hours = fields.Boolean(string="Any Extra Hours")
    extra_hours = fields.Integer(string="Extra Hours")
    extra_hour_price = fields.Monetary(string="Extra Hour Price")
    extra_hour_amount = fields.Monetary(string="Extra Hours Amount",
                                        compute='_compute_extra_hour_amount')
    rent_per_unit = fields.Monetary(string="Rent / Unit",
                                    compute='_compute_rent_per_unit')
    total_amount = fields.Monetary(string="Total Amount",
                                   compute='_compute_final_total_amount')

    equipment_odometer_id = fields.Many2one('equipment.odometer')

    @api.constrains('start_date', 'return_date', 'product_id')
    def _check_rented_products(self):
        """Check rented product"""
        for rec in self:
            rented_products = self.env['renting.items'].search(
                [('id', '!=', rec.id), ('status', 'not in', ['close', 'cancel', 'reject', 'return'])])
            for product in rented_products:
                if rec.product_id.id == product.product_id.id:
                    if rec.start_date < product.start_date and rec.return_date >= product.start_date:
                        raise ValidationError(
                            _(f"{product.product_id.name} is already rented between {product.start_date} and {product.return_date}"))
                    elif rec.start_date > product.start_date and rec.start_date <= product.return_date:
                        raise ValidationError(
                            _(f"{product.product_id.name} is already rented between {product.start_date} and {product.return_date}"))
                    elif rec.start_date == product.start_date:
                        raise ValidationError(
                            _(f"{product.product_id.name} is already rented between {product.start_date} and {product.return_date}"))

    @api.onchange('start_date', 'return_date')
    def _onchange_start_return_date(self):
        """Onchange start return date"""
        for rec in self:
            rec.product_id = False

    @api.depends('start_date', 'return_date', 'product_id')
    def _compute_product_ids(self):
        """Compute product ids"""
        rented_products = self.env['renting.items'].search([
            ('start_date', '!=', False),
            ('return_date', '!=', False),
            ('status', 'not in', ['close', 'cancel', 'reject'])
        ])

        for rec in self:
            booked_products = []
            for product in rented_products:
                if product.status == 'return':
                    continue
                if rec.start_date and rec.return_date:
                    if rec.start_date < product.start_date and rec.return_date >= product.start_date:
                        booked_products.append(product.product_id.id)
                    elif rec.start_date > product.start_date and rec.start_date <= product.return_date:
                        booked_products.append(product.product_id.id)
                    elif rec.start_date == product.start_date:
                        booked_products.append(product.product_id.id)
            rec.product_ids = booked_products

    @api.constrains('start_date', 'return_date', 'rent_order_id')
    def _check_renting_dates(self):
        """Check Renting Dates"""
        for record in self:
            if record.rent_order_id:
                rent_start = record.rent_order_id.start_date
                rent_end = record.rent_order_id.return_date
                if not (rent_start <= record.start_date <= rent_end and rent_start <= record.return_date <= rent_end):
                    raise ValidationError(
                        "The renting items dates must be between the start date and return date of the rental order.")

    @api.constrains('renting_days')
    def _constrains_renting_days(self):
        """Check Renting Days"""
        for record in self:
            if record.renting_days > record.total_contract_days:
                raise ValidationError(_("Renting days cannot be greater than contract days."))

    @api.depends('start_date', 'return_date')
    def _compute_total_rental_days(self):
        """Compute Total Rental Days"""
        for rec in self:
            if rec.return_date and rec.start_date:
                if rec.start_date > rec.return_date:
                    raise ValidationError(_("Please ensure that the return date is greater than the start date"))
                else:
                    rec.total_contract_days = (rec.return_date - rec.start_date).days
            else:
                rec.total_contract_days = 0.0

    @api.depends('start_date', 'return_date')
    def _compute_total_hours(self):
        """Compute Total Hours"""
        for rec in self:
            total_hours = 0.0
            if rec.return_date and rec.start_date:
                time_difference = rec.return_date - rec.start_date
                total_hours = time_difference.total_seconds() / 3600
            rec.total_hours = total_hours

    @api.onchange('product_id')
    def _onchange_equipment(self):
        """Onchange Equipment"""
        self.equipment_renting_info_id = False

    @api.onchange('product_id')
    def _onchange_equipment_details(self):
        """Onchange Equipment Details"""
        for rec in self:
            rec.serial_number = rec.product_id.serial_number
            rec.description = rec.product_id.name

    @api.onchange('equipment_renting_info_id')
    def _onchange_equipment_renting_info(self):
        """Onchange Equipment Renting Info"""
        for rec in self:
            rec.renting_amount = rec.equipment_renting_info_id.rate
            rec.range = rec.equipment_renting_info_id.range
            rec.renting_days = rec.equipment_renting_info_id.renting_day
            rec.extra_hour_price = rec.equipment_renting_info_id.extra_hour_price

    @api.onchange('is_any_extra_hours')
    def _onchange_extra_hours(self):
        """Onchange Extra Hours"""
        for rec in self:
            if not rec.is_any_extra_hours:
                rec.extra_hours = ''

    @api.depends('total_contract_days', 'renting_days')
    def _compute_total_day_diff(self):
        """Compute Total Days Diff"""
        for rec in self:
            if rec.renting_days != 0:
                rec.total_day_diff = rec.total_contract_days / rec.renting_days
            else:
                rec.total_day_diff = 0

    @api.depends('renting_amount', 'total_day_diff')
    def _compute_rent_amount(self):
        """Compute Rent Amount"""
        for rec in self:
            rec.rent_amount = rec.renting_amount * rec.total_day_diff

    @api.depends('extra_hours', 'extra_hour_price')
    def _compute_extra_hour_amount(self):
        """Compute Extra Hours Amount"""
        for rec in self:
            rec.extra_hour_amount = rec.extra_hours * rec.extra_hour_price

    @api.depends('rent_amount', 'extra_hour_amount')
    def _compute_rent_per_unit(self):
        """Compute Rent/Unit"""
        for rec in self:
            rec.rent_per_unit = rec.rent_amount + rec.extra_hour_amount

    @api.depends('rent_per_unit', 'product_qty')
    def _compute_final_total_amount(self):
        """Compute Final Total Amount"""
        for rec in self:
            rec.total_amount = rec.rent_per_unit * rec.product_qty
