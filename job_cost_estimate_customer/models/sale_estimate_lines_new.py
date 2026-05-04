# -*- coding: utf-8 -*-

from odoo import api, fields, models, _

class SaleEstimatelineJob(models.Model):
    _name = "sale.estimate.line.job"
    _description = 'Sale Estimate line Job'
    
    @api.depends('price_unit','product_uom_qty','discount')
    def _compute_amount(self):
        for rec in self:
            if rec.discount:
                disc_amount = (rec.price_unit * rec.product_uom_qty) * rec.discount / 100
                rec.price_subtotal = (rec.price_unit * rec.product_uom_qty) - disc_amount
            else:
                rec.price_subtotal = rec.price_unit * rec.product_uom_qty

    estimate_id = fields.Many2one(
        'sale.estimate.job',
        string='Sale Estimate', 
    )
    product_id = fields.Many2one(
        'product.product',
        string='Product',
        domain="[('sale_ok', '=', True)]",
        required=False
    )
    product_uom_qty = fields.Float(
        string='Quantity', 
        required=True, 
        default=1.0,
        digits='Product Unit of Measure',
    )
    product_uom_category_id = fields.Many2one(related='product_id.uom_id.category_id', depends=['product_id'])
    product_uom = fields.Many2one(
        'uom.uom',
        string='Unit of Measure',
        compute='_compute_product_uom',
        store=True, readonly=False, precompute=True, ondelete='restrict',
        domain="[('category_id', '=', product_uom_category_id)]",
        required=False
    )
    pricelist_item_id = fields.Many2one(
        comodel_name='product.pricelist.item',
        compute='_compute_pricelist_item_id'
    )
    price_unit = fields.Float(
        string="Unit Price",
        compute='_compute_price_unit',
        digits='Product Price',
        store=True, readonly=False, required=True, precompute=True
    )
    price_subtotal = fields.Monetary(
        string="Subtotal",
        compute='_compute_amount',
        store=True, precompute=True
    )
    currency_id = fields.Many2one(
        related='estimate_id.currency_id',
        depends=['estimate_id.currency_id'],
        store=True, precompute=True)
    product_description = fields.Char(
        string='Description',
        compute='_compute_product_description',
        store=True, readonly=False, required=False, precompute=True
    )
    discount = fields.Float(
        string='Discount (%)',
        compute='_compute_discount',
        digits='Discount',
        store=True, readonly=False, precompute=True
    )
    company_id = fields.Many2one(related='estimate_id.company_id', string='Company', store=True, readonly=True)
    # tax_id = fields.Many2many('account.tax', string='Taxes', domain=['|', ('active', '=', False), ('active', '=', True)])

    job_type = fields.Selection(
        selection=[('material','Material'),
                   ('labour','Labour'),
                    ('overhead','Overhead')
                ],
        string="Type",
        required=True,
    )
    analytic_id = fields.Many2one(
        'account.analytic.account',
        'Analytic Account',
    )
    display_type = fields.Selection([
        ('line_section', "Section"),
        ('line_note', "Note")], 
        default=False
    )
    name = fields.Char(
        string='Name',
    )
    sequence = fields.Integer(
        string="Sequence", 
        default=10
    )

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_pricelist_item_id(self):
        for line in self:
            if not line.product_id or not line.estimate_id.pricelist_id:
                line.pricelist_item_id = False
            else:
                line.pricelist_item_id = line.estimate_id.pricelist_id._get_product_rule(
                    line.product_id,
                    quantity=line.product_uom_qty or 1.0,
                    uom=line.product_uom,
                    date=line.estimate_id.estimate_date,
                )

    @api.depends('product_id')
    def _compute_product_uom(self):
        for line in self:
            if not line.product_uom or (line.product_id.uom_id.id != line.product_uom.id):
                line.product_uom = line.product_id.uom_id

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_price_unit(self):
        for line in self:
            # Don't compute the price for deleted lines.
            if not line.estimate_id:
                continue
            
            if not line.product_uom or not line.product_id:
                line.price_unit = 0.0
            else:
                line = line.with_company(line.company_id)
                line.price_unit = line.product_id._get_tax_included_unit_price(
                    self.company_id,
                    self.estimate_id.currency_id,
                    self.estimate_id.estimate_date,
                    'sale',
                    product_price_unit=line._get_display_price(),
                    product_currency=self.estimate_id.currency_id
                )

    def _get_display_price(self):
        self.ensure_one()

        pricelist_price = self._get_pricelist_price()
        if not self.pricelist_item_id._show_discount():
            # No pricelist rule found => no discount from pricelist
            return pricelist_price

        base_price = self._get_pricelist_price_before_discount()

        # negative discounts (= surcharge) are included in the display price
        return max(base_price, pricelist_price)

    @api.depends('price_unit','product_uom_qty','discount')
    def _compute_amount(self):
        for rec in self:
            if rec.discount:
                disc_amount = (rec.price_unit * rec.product_uom_qty) * rec.discount / 100
                rec.price_subtotal = (rec.price_unit * rec.product_uom_qty) - disc_amount
            else:
                rec.price_subtotal = rec.price_unit * rec.product_uom_qty

    @api.depends('product_id')
    def _compute_product_description(self):
        for line in self:
            if line.product_id:
                line.product_description = line.product_id.get_product_multiline_description_sale()
                continue

    @api.depends('product_id', 'product_uom', 'product_uom_qty')
    def _compute_discount(self):
        discount_enabled = self.env['product.pricelist.item']._is_discount_feature_enabled()
        for line in self:
            if not line.product_id:
                line.discount = 0.0

            if not (line.estimate_id.pricelist_id and discount_enabled):
                continue

            line.discount = 0.0

            line = line.with_company(line.company_id)
            pricelist_price = line._get_pricelist_price()
            base_price = line._get_pricelist_price_before_discount()

            if base_price != 0:  # Avoid division by zero
                discount = (base_price - pricelist_price) / base_price * 100
                if (discount > 0 and base_price > 0) or (discount < 0 and base_price < 0):
                    # only show negative discounts if price is negative
                    # otherwise it's a surcharge which shouldn't be shown to the customer
                    line.discount = discount

    def _get_pricelist_price(self):
        """Compute the price given by the pricelist for the given line information.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()
        product = self.product_id.with_context(
            lang=self.estimate_id.partner_id.lang,
            partner=self.estimate_id.partner_id,
            quantity=self.product_uom_qty,
            date=self.estimate_id.estimate_date,
            pricelist=self.estimate_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        price = self.pricelist_item_id._compute_price(
            product=product,
            quantity=self.product_uom_qty or 1.0,
            uom=self.product_uom,
            date=self.estimate_id.estimate_date,
            currency=self.estimate_id.currency_id,
        )

        return price

    def _get_pricelist_price_before_discount(self):
        """Compute the price used as base for the pricelist price computation.

        :return: the product sales price in the order currency (without taxes)
        :rtype: float
        """
        self.ensure_one()
        self.product_id.ensure_one()
        product = self.product_id.with_context(
            lang=self.estimate_id.partner_id.lang,
            partner=self.estimate_id.partner_id,
            quantity=self.product_uom_qty,
            date=self.estimate_id.estimate_date,
            pricelist=self.estimate_id.pricelist_id.id,
            uom=self.product_uom.id,
            fiscal_position=self.env.context.get('fiscal_position')
        )

        return self.pricelist_item_id._compute_price_before_discount(
            product=product,
            quantity=self.product_uom_qty or 1.0,
            uom=self.product_uom,
            date=self.estimate_id.estimate_date,
            currency=self.estimate_id.currency_id,
        )