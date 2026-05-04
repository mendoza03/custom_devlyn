# -*- coding: utf-8 -*-
# Copyright 2022-Today TechKhedut.
# Part of TechKhedut. See LICENSE file for full copyright and licensing details.
from odoo.exceptions import ValidationError
from odoo import api, fields, models, _


class RentOrder(models.Model):
    """Rent Order"""
    _name = 'rent.order'
    _inherit = ['mail.thread', 'mail.activity.mixin']
    _description = __doc__
    _rec_name = 'order_number'

    order_number = fields.Char(string='Order Number', readonly=True,
                               default=lambda self: _('New'), copy=False)
    customer_id = fields.Many2one('res.partner', string="Customer", required=True,
                                  domain=[('type', '=', 'contact')])
    phone = fields.Char(string="Mobile")
    email = fields.Char(string="Email")

    shipping_street = fields.Char(string="Street", translate=True)
    shipping_street2 = fields.Char(string="Street 2", translate=True)
    shipping_city = fields.Char(string="City", translate=True)
    shipping_state_id = fields.Many2one("res.country.state", string='State',
                                        domain="[('country_id', '=?', shipping_country_id)]")

    shipping_country_id = fields.Many2one("res.country", string="Country")
    shipping_zip = fields.Char(string="Zip")

    billing_street = fields.Char(string=" Street", translate=True)
    billing_street2 = fields.Char(string=" Street 2", translate=True)
    billing_city = fields.Char(string=" City", translate=True)
    billing_state_id = fields.Many2one("res.country.state", string=' State',
                                       domain="[('country_id', '=?', billing_country_id)]")

    billing_country_id = fields.Many2one("res.country", string=" Country")
    billing_zip = fields.Char(string=" Zip")

    start_date = fields.Date(string="Start Date", required=True)
    return_date = fields.Date(string="Return Date", required=True)

    rent_term_id = fields.Many2one('rent.term', string=" Terms & Conditions")
    description = fields.Html(string="Terms & Conditions")
    responsible_id = fields.Many2one('res.users',
                                     default=lambda self: self.env.user,
                                     string="Responsible", required=True)

    renting_items_ids = fields.One2many(comodel_name='renting.items',
                                        inverse_name='rent_order_id',
                                        string="Renting Items")
    equipment_delivery_ids = fields.One2many(comodel_name='equipment.delivery',
                                             inverse_name='rent_order_id',
                                             string="Equipment Delivery")

    total_item_cost = fields.Monetary(compute="_compute_total_item_cost",
                                      string="Total")
    total_damage_charge = fields.Monetary(compute="_compute_total_return_damage_charges",
                                          string="Total Damage Charge")
    extra_hour_charge = fields.Monetary(compute="_compute_extra_hour_charge",
                                        string="Total Extra Hour Charge")
    company_id = fields.Many2one('res.company', default=lambda self: self.env.company)
    currency_id = fields.Many2one('res.currency', string='Currency',
                                  related="company_id.currency_id")

    status = fields.Selection([
        ('draft', "New"), ('quotation', "Quotation"),
        ('quotation_sent', "Quotation Sent"), ('approve', "Quotation Approved"),
        ('reject', "Reject"), ('in_progress', "In Progress"),
        ('in_delivery', "In Delivered"), ('delivery', "Delivered"),
        ('return', "Return"), ('close', "Closed"),
        ('cancel', "Cancel")], default='draft', string="Status", group_expand='_expand_groups')

    invoice_id = fields.Many2one('account.move', string="Renting Invoice")
    invoice_payment_state = fields.Selection(related='invoice_id.payment_state',
                                             string="Payment Status")
    reject_reason = fields.Text(string="Quotation Reject Reasons")

    delivery_order_id = fields.Many2one('stock.picking')
    delivery_type = fields.Selection([
        ('product_wise_delivery', "Product Wise Delivery"),
        ('single_delivery_order', "Single Delivery Order")],
        compute='_compute_delivery_type', string="Delivery Type", store=True)
    warehouse_id = fields.Many2one('stock.warehouse', string="Warehouse")
    invoice_count = fields.Integer(string="Invoices",
                                   compute='_compute_invoice_count')
    delivery_order_count = fields.Integer(string="Delivery Orders",
                                          compute='_compute_delivery_order_count')
    return_order_count = fields.Integer(string="Return Orders",
                                        compute='_compute_return_order_count')

    extra_hour_invoice_type = fields.Selection([
        ('single', 'Single'),
        ('together', 'Together')
    ], string="Extra Hour Charge Invoice Type", default='single')
    button_visible = fields.Boolean(compute='_compute_button_visibility')

    # DEPRECATED
    return_invoice_id = fields.Many2one('account.move',
                                        string="Return Damage Invoice")
    invoice_return_state = fields.Selection(related='return_invoice_id.payment_state',
                                            string="Return State")

    @api.model
    def _expand_groups(self, states, domain, order=None):
        return ['draft', 'quotation', 'quotation_sent', 'approve', 'reject', 'in_progress', 'in_delivery', 'delivery',
                'return', 'close', 'cancel']

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get('order_number', _('New')) == _('New'):
                vals['order_number'] = self.env['ir.sequence'].next_by_code('rent.order') or _('New')
        res = super(RentOrder, self).create(vals_list)
        return res

    def draft_to_quotation(self):
        """Draft to Quotation Send"""
        self.status = 'quotation'

    def quotation_to_send_quotation(self):
        """Check Renting Items Available"""
        if not self.renting_items_ids:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("Please fill in all required renting items"),
                    'sticky': False,
                }
            }
            return message
        mail_template = self.env.ref('tk_rental.rental_quotation_mail_template')
        if mail_template:
            mail_template.send_mail(self.id, force_send=True)
        self.status = 'quotation_sent'

    def quotation_sent_to_approve(self):
        """Quotation Send to Approve"""
        self.status = 'approve'

    def quotation_sent_to_reject(self):
        """Quotation Send to Reject"""
        self.status = 'reject'

    def get_create_rental_invoice(self):
        """Create Rental Invoice"""
        invoice_lines = []
        for rec in self.renting_items_ids:
            if not rec.rent_per_unit > 0:
                message = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'message': _("""Ensure you've selected all required rental items and added their prices before
                         proceeding."""),
                        'sticky': False,
                    }
                }
                return message
            data = {
                'product_id': rec.product_id.id,
                'name': rec.description,
                'quantity': rec.product_qty,
                'product_uom_id': rec.product_id.uom_id.id,
                'price_unit': rec.rent_per_unit,
            }
            invoice_lines.append((0, 0, data))
        data = {
            'partner_id': self.customer_id.id,
            'move_type': 'out_invoice',
            'invoice_date': fields.Date.today(),
            'invoice_line_ids': invoice_lines,
            'rent_order_id': self.id
        }
        invoice_id = self.env['account.move'].sudo().create(data)
        self.write({
            'invoice_id': invoice_id.id,
            'status': 'in_progress'
        })
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rent Invoice'),
            'res_model': 'account.move',
            'res_id': invoice_id.id,
            'view_mode': 'form',
            'target': 'current'
        }

    def reject_to_draft(self):
        """Reject to Draft Stage"""
        self.status = 'draft'

    def in_delivery_to_delivery(self):
        """Delivery Stage"""
        self.status = 'delivery'

    def delivery_to_return(self):
        """Return Order Check"""
        # Fetch all delivery orders linked to the current rental order
        delivery_orders = self.env['stock.picking'].search(
            [('rent_order_id', '=', self.id), ('is_return_order', '=', False)]
        )
        # Fetch all return orders linked to the current rental order
        return_orders = self.env['stock.picking'].search(
            [('rent_order_id', '=', self.id), ('is_return_order', '=', True)]
        )
        if not return_orders or len(return_orders) < len(delivery_orders):
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': _("All delivery orders must be converted into return orders before proceeding."),
                    'sticky': False,
                }
            }
        # Check if all return orders are in 'done' state
        incomplete_orders = return_orders.filtered(lambda r: r.state != 'done')
        if incomplete_orders:
            return {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': "All return orders must be completed before proceeding.",
                    'sticky': False,
                }
            }
        # If all return orders are done, proceed with sending the email
        mail_template = self.env.ref('tk_rental.equipment_rental_damage_charges_mail_template')
        if mail_template:
            mail_template.send_mail(self.id, force_send=True)
        self.status = 'return'

    def return_to_close(self):
        # Check if the invoice payment state is not 'paid'
        if self.invoice_payment_state != 'paid':
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': "Pay the rent invoice first, then proceed with the next steps.",
                    'sticky': False,
                }
            }
            return message
        for rec in self.equipment_delivery_ids:
            if rec.invoice_id and rec.invoice_state != 'paid':
                message = {
                    'type': 'ir.actions.client',
                    'tag': 'display_notification',
                    'params': {
                        'type': 'warning',
                        'message': "Pay the return damage invoice first, then proceed with the process.",
                        'sticky': False,
                    }
                }
                return message
        self.status = 'close'

    def close_to_cancel(self):
        """Order Cancel"""
        self.status = 'cancel'

    def _compute_invoice_count(self):
        """Invoice Count"""
        for rec in self:
            rec.invoice_count = self.env['account.move'].search_count([('rent_order_id', '=', rec.id)])

    def action_rent_invoice_view(self):
        """Invoice View"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Rent Invoice'),
            'res_model': 'account.move',
            'domain': [('rent_order_id', '=', self.id)],
            'view_mode': 'list,form',
            'target': 'current',
            'context': {
                'create': False,
            }
        }

    @api.onchange('customer_id')
    def _onchange_customer_details(self):
        """Onchange Customer Details"""
        for rec in self:
            rec.phone = rec.customer_id.phone
            rec.email = rec.customer_id.email
            rec.shipping_street = rec.customer_id.street
            rec.shipping_street2 = rec.customer_id.street2
            rec.shipping_city = rec.customer_id.city
            rec.shipping_state_id = rec.customer_id.state_id.id
            rec.shipping_country_id = rec.customer_id.country_id.id
            rec.shipping_zip = rec.customer_id.zip
            rec.billing_street = rec.customer_id.street
            rec.billing_street2 = rec.customer_id.street2
            rec.billing_city = rec.customer_id.city
            rec.billing_state_id = rec.customer_id.state_id.id
            rec.billing_country_id = rec.customer_id.country_id.id
            rec.billing_zip = rec.customer_id.zip

    @api.onchange('rent_term_id')
    def _onchange_rent_term_template(self):
        """Rent Term Template"""
        for rec in self:
            rec.description = rec.rent_term_id.description

    @api.depends('renting_items_ids.total_amount')
    def _compute_total_item_cost(self):
        """Compute Total Item Cost"""
        for rec in self:
            rec.total_item_cost = sum(item.total_amount for item in rec.renting_items_ids)

    @api.depends('equipment_delivery_ids.total_damage_charge')
    def _compute_total_return_damage_charges(self):
        """Compute extra hour charge"""
        for rec in self:
            rec.total_damage_charge = sum(equip.total_damage_charge for equip in rec.equipment_delivery_ids)

    @api.depends('equipment_delivery_ids.total_charge')
    def _compute_extra_hour_charge(self):
        """Compute extra hour charge"""
        for rec in self:
            rec.extra_hour_charge = sum(equip.total_charge for equip in rec.equipment_delivery_ids)

    @api.constrains('start_date', 'return_date')
    def _contract_check_dates(self):
        """Check equipment renting dates"""
        for record in self:
            today = fields.Date.today()
            if record.start_date < today:
                raise ValidationError(_("The start date cannot be in the past."))
            if record.return_date and record.return_date < record.start_date:
                raise ValidationError(_("The return date must be greater than the start date."))

    @api.depends('renting_items_ids.start_date', 'renting_items_ids.return_date')
    def _compute_delivery_type(self):
        for record in self:
            # Get the set of all start and end dates
            start_dates = {item.start_date for item in record.renting_items_ids}
            end_dates = {item.return_date for item in record.renting_items_ids}
            # Check if there is exactly one unique start date and one unique end date
            if len(start_dates) == 1 and len(end_dates) == 1:
                record.delivery_type = 'single_delivery_order'
            else:
                record.delivery_type = 'product_wise_delivery'

    def action_create_delivery_order(self):
        """Create Delivery Order"""
        self._create_equipment_deliveries()
        if self.delivery_type == 'single_delivery_order':
            self._create_single_delivery_order()
        elif self.delivery_type == 'product_wise_delivery':
            self._create_product_wise_delivery_orders()
        self.status = 'in_delivery'

    def _create_equipment_deliveries(self):
        """Create Equipment Delivery"""
        for item in self.renting_items_ids:
            data = {
                'product_id': item.product_id.id,
                'product_qty': item.product_qty,
                'description': item.description,
                'rent_order_id': item.rent_order_id.id,
            }
            self.env['equipment.delivery'].create(data)

    def _create_single_delivery_order(self):
        """Create Single Delivery Order"""
        lines = [
            (0, 0, {
                'product_id': line.product_id.id,
                'product_uom_qty': line.product_qty,
                'product_uom': line.product_id.uom_id.id,
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id': self.warehouse_id.wh_output_stock_loc_id.id,
                'name': line.product_id.name
            })
            for line in self.equipment_delivery_ids
        ]
        delivery_record = {
            'partner_id': self.customer_id.id,
            'picking_type_id': self.warehouse_id.out_type_id.id,
            'location_id': self.warehouse_id.lot_stock_id.id,
            'location_dest_id': self.warehouse_id.wh_output_stock_loc_id.id,
            'move_ids_without_package': lines,
            'move_type': 'one',
            'rent_order_id': self.id
        }
        delivery_order = self.env['stock.picking'].create(delivery_record)
        for delivery in self.equipment_delivery_ids:
            delivery.deliver_order_id = delivery_order.id

    def _create_product_wise_delivery_orders(self):
        """Create Product Wise Delivery Order"""
        for line in self.equipment_delivery_ids:
            delivery_record = {
                'partner_id': self.customer_id.id,
                'picking_type_id': self.warehouse_id.out_type_id.id,
                'location_id': self.warehouse_id.lot_stock_id.id,
                'location_dest_id': self.warehouse_id.wh_output_stock_loc_id.id,
                'move_ids_without_package': [(0, 0, {
                    'product_id': line.product_id.id,
                    'product_uom_qty': line.product_qty,
                    'product_uom': line.product_id.uom_id.id,
                    'location_id': self.warehouse_id.lot_stock_id.id,
                    'location_dest_id': self.warehouse_id.wh_output_stock_loc_id.id,
                    'name': line.product_id.name
                })],
                'move_type': 'one',
                'rent_order_id': self.id
            }
            delivery_order = self.env['stock.picking'].create(delivery_record)
            line.deliver_order_id = delivery_order.id

    def _compute_delivery_order_count(self):
        """Compute Delivery Order Count"""
        for rec in self:
            rec.delivery_order_count = self.env['stock.picking'].search_count(
                [('rent_order_id', '=', rec.id), ('is_return_order', '=', False)])

    def action_delivery_order_view(self):
        """Delivery Order View"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Delivery Orders'),
            'res_model': 'stock.picking',
            'domain': [('rent_order_id', '=', self.id), ('is_return_order', '=', False)],
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'context': {
                'create': False,
            }
        }

    def _compute_return_order_count(self):
        """Compute Return Order Count"""
        for rec in self:
            rec.return_order_count = self.env['stock.picking'].search_count(
                [('rent_order_id', '=', rec.id), ('is_return_order', '!=', False)])

    def action_return_order_view(self):
        """Return Order Views"""
        return {
            'type': 'ir.actions.act_window',
            'name': _('Return Orders'),
            'res_model': 'stock.picking',
            'domain': [('rent_order_id', '=', self.id), ('is_return_order', '!=', False)],
            'view_mode': 'list,form,kanban',
            'target': 'current',
            'context': {
                'create': False,
            }
        }

    @api.depends('button_visible')
    def _compute_button_visibility(self):
        """Compute button visibility"""
        for rec in self:
            button_visible = True
            for record in rec.equipment_delivery_ids:
                if not record.extra_hour_invoice_id:
                    button_visible = False
                    break
            rec.button_visible = button_visible

    def action_create_extra_hour_invoice(self):
        invoice_lines = []
        rent_orders = self.equipment_delivery_ids.mapped('rent_order_id')
        # Check if all invoices are already created
        if all(record.extra_hour_invoice_id for record in self.equipment_delivery_ids):
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': "All invoices already created",
                    'sticky': False,
                }
            }
            return message
        # Flag to track if any valid records exist
        has_valid_record = False
        # Process each delivery record
        for data in self.equipment_delivery_ids:
            # Skip records where invoice is already created
            if data.extra_hour_invoice_id:
                continue
            if data.is_any_extra_hours:
                has_valid_record = True
                # Ensure there are extra hours and corresponding charge
                if not data.total_charge:
                    message = {
                        'type': 'ir.actions.client',
                        'tag': 'display_notification',
                        'params': {
                            'type': 'warning',
                            'message': _(
                                """Kindly include the additional hours and corresponding extra hours' price details"""),
                            'sticky': False,
                        }
                    }
                    return message
                # Prepare invoice line data
                line_data = {
                    'product_id': data.product_id.id,
                    'name': data.description,
                    'quantity': data.extra_hours,
                    'price_unit': data.extra_hour_price,
                    'tax_ids': [],  # Empty list for taxes
                }
                invoice_lines.append((0, 0, line_data))
        # If no valid record found, return warning
        if not has_valid_record:
            message = {
                'type': 'ir.actions.client',
                'tag': 'display_notification',
                'params': {
                    'type': 'warning',
                    'message': "Not available record",
                    'sticky': False,
                }
            }
            return message
        # Create invoice data if there are valid invoice lines
        if invoice_lines:
            invoice_data = {
                'partner_id': self.customer_id.id,
                'move_type': 'out_invoice',
                'invoice_date': fields.Date.today(),
                'invoice_line_ids': invoice_lines,
                'rent_order_id': rent_orders.id
            }
            # Create the invoice
            invoice_id = self.env['account.move'].sudo().create(invoice_data)
            # Update delivery records with invoice ID
            for rec in self.equipment_delivery_ids:
                if rec.is_any_extra_hours and not rec.extra_hour_invoice_id:
                    rec.extra_hour_invoice_id = invoice_id.id


class ReturnPicking(models.TransientModel):
    _inherit = 'stock.return.picking'

    #* ---------------------------------------------------------
    #* SUPER METHODS
    #* ---------------------------------------------------------
    def action_create_returns(self):
        res = super(ReturnPicking, self).action_create_returns()
        return_order = self.env['stock.picking'].browse(res['res_id'])
        return_order.write({'is_return_order': True})