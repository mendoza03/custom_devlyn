from odoo import _, api, fields, models, tools
from .project_worksite import PROJECT_WORKSITE_TYPE


class Property(models.Model):
    _inherit = ["product.template"]
    _description = "Property"
    _order = "sequence, id"

    # Commission
    @api.depends()
    def _compute_is_apply(self):
        for rec in self:
            commission_based_on = rec.company_id.commission_based_on if rec.company_id else self.env.company.commission_based_on
            rec.is_apply = False
            if commission_based_on:
                rec.is_apply = True

    commission_type = fields.Selection(string="Commission Amount Type", selection=[('percentage', 'By Percentage'),
                                                                                   ('fix', 'Fixed Amount')])
    is_commission_product = fields.Boolean('Is Commission Product ?')
    is_apply = fields.Boolean(string='Is Apply ?', compute='_compute_is_apply')
    commission_range_ids = fields.One2many('sales.commission.range', 'commission_product_id',
                                           string='Sales Commission Range')

    state = fields.Selection([("free", "Available"), ("reserved", "Booked"), ("sold", "Sold"), ("on_lease", "Leased"), ("blocked", "Blocked"), ("inactive", "Inactive")],"Status", default="free")

    sequence = fields.Integer("Sequ.")

    partner_id = fields.Many2one("res.partner", "Owner")
    region_id = fields.Many2one("region.region", "Region")
    property_date = fields.Date("Date", default=fields.Date.context_today)

    address = fields.Char("Address")
    street = fields.Char(related="region_id.street", store=True)
    street2 = fields.Char(related="region_id.street2", store=True)
    zip = fields.Char(related="region_id.zip", store=True)
    city = fields.Char(related="region_id.city", store=True)
    state_id = fields.Many2one("res.country.state", string="State", ondelete="restrict",
                               related="region_id.state_id", store=True, )
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict",
                                 related="region_id.country_id", store=True, )
    country_code = fields.Char(related="country_id.code", string="Country Code", store=True)

    note = fields.Html("Notes")
    description = fields.Text("Description")
    attachment_line_ids = fields.One2many("attachment.line", "property_id", "Attachments")
    # brochure_line_ids = fields.One2many("attachment.line", "pro_brochure_id", "Brochure")

    license_code = fields.Char("License Code", size=16)
    license_date = fields.Date("License Date")
    date_added = fields.Date("Date Added to Notarization")
    license_location = fields.Char("License Notarization")

    utility_ids = fields.One2many("property.utilities", "property_id")
    maintenance_type = fields.Selection(selection=[("fix", "Fix Cost"), ("sft", "Per SFT")], default="fix")
    maintenance_charges = fields.Float()
    maintenance_count = fields.Integer(compute='_maintenance_count', string='Maintenance Count', )

    property_area = fields.Float("Property Size (m²)", digits=(16, 8))
    unit_of_measure = fields.Selection([("m", "m²"), ("yard", "Yard²")], default="m", required=True)
    converted_area = fields.Float("Converted Size", digits=(16, 8))

    partner_from = fields.Date("Purchase Date")
    partner_to = fields.Date("Sale Date")

    carpet_id = fields.Many2one('documents.document', string='Document', ondelete='cascade')

    worksite_id = fields.Many2one("project.worksite", "Worksite")
    project_worksite_id = fields.Many2one("project.worksite", "Project")
    condominium_worksite_id = fields.Many2one("condominium.worksite", "condominium")
    project_worksite_ids = fields.Many2many("project.worksite", "property_worksite_product_template_rel", 'pw_id',
                                            'p_id', string="Worksites")
    contact_ids = fields.Many2many("res.partner", string="Contacts")

    project_type = fields.Selection(selection=PROJECT_WORKSITE_TYPE + [('shop', 'Shop')], default="tower")
    floor = fields.Integer("Floor")

    net_price = fields.Float("Final Selling Price", compute="_calc_price", store=True)
    price_before_discount = fields.Float('Price Before Discount', compute='_calc_price', store=True)
    discount_type = fields.Selection([("percentage", "Percentage"), ("amount", "Amount")])
    discount = fields.Float("Discount")

    property_price_type = fields.Selection(selection=[("fix", "Fix Cost"), ("sft", "Per SFT")], default="sft")
    price_per_m = fields.Float("Base Price")
    project_area = fields.Float("Project Area")
    tax_base_amount = fields.Float("Tax Base Amount")

    # Property
    rental_fee = fields.Float("Rental fee", digits=(16, 4))
    insurance_fee = fields.Float("Insurance fee")
    template_id = fields.Many2one("installment.template", "Payment Template")

    is_property = fields.Boolean("Property")
    property_type_id = fields.Many2one("property.type", "Property Type")
    reservation_count = fields.Integer(compute="_reservation_count", string="Reservation Count")

    total_maintenance = fields.Float(compute="_calc_total", store=True, compute_sudo=True)
    total_cost = fields.Float(compute="_calc_total", store=True, compute_sudo=True)
    total_utilities = fields.Float(compute="_calc_utilities")

    is_shop = fields.Boolean(default=False)
    doc_charges = fields.Float("Doc Charges")


    @api.onchange("unit_of_measure", "property_area")
    def _onchange_converted_area(self):
        for rec in self:
            if rec.unit_of_measure == "m":
                converted_area = rec.property_area * 0.092903
            elif rec.unit_of_measure == "yard":
                converted_area = rec.property_area * 0.111111
            else:
                converted_area = rec.property_area
            rec.converted_area = converted_area

    @api.onchange("converted_area")
    def _onchange_property_area(self):
        for rec in self:
            if rec.unit_of_measure == "m":
                property_area = rec.converted_area / 0.092903
            elif rec.unit_of_measure == "yard":
                property_area = rec.converted_area / 0.111111
            else:
                property_area = rec.converted_area
            rec.property_area = property_area

    @api.depends("maintenance_charges", "utility_ids")
    def _calc_total(self):
        for rec in self:
            maintenance_charges = rec.maintenance_charges
            if rec.maintenance_type != "fix":
                maintenance_charges = (
                        rec.maintenance_charges * rec.property_area or 0
                )
            rec.total_maintenance = maintenance_charges + sum(rec.utility_ids.mapped("price"))
            rec.total_cost = rec.total_maintenance + rec.net_price

    def _calc_utilities(self):
        for rec in self:
            rec.total_utilities = sum(rec.utility_ids.mapped('price'))

    @api.depends("maintenance_charges", "utility_ids")
    def _calc_maintenance(self):
        for rec in self:
            maintenance_charges = rec.maintenance_charge
            if rec.maintenance_type and rec.maintenance_type == "sft":
                maintenance_charges = (
                        rec.maintenance_charge * rec.property_area or 0
                )

            utility_maintenance = 0
            if rec.utility_ids:
                utility_maintenance = sum(rec.utility_ids.mapped("price"))
            rec.total_maintenance = maintenance_charges + utility_maintenance

    @api.depends("price_per_m", "property_area", "total_utilities")
    def _calc_price(self):
        for rec in self:
            if rec.property_price_type == 'sft':
                rec.net_price = (rec.price_per_m * rec.property_area) + rec.total_utilities
            else:
                rec.net_price = rec.price_per_m + rec.total_utilities

    def action_reservation(self):
        reservation_obj = self.env["property.reservation"]
        reservation_ids = []
        for rec in self:
            reservation_id = reservation_obj.create({
                "partner_id": rec.partner_id.id,
                "region_id": rec.region_id.id,
                "project_id": rec.project_worksite_id.id,
                "property_id": rec.id,
                "property_code": rec.default_code,
                "floor": rec.floor,
                "net_price": rec.net_price,
                "address": rec.address,
                "property_type_id": rec.property_type_id.id,
                "property_area": rec.property_area,
                "price_per_m": rec.price_per_m,
                "property_price_type": rec.property_price_type,

            })
            reservation_ids.append(reservation_id.id)

        return {
            "type": "ir.actions.act_window",
            "res_model": reservation_obj._name,
            "view_type": "form",
            "view_mode": "form",
            "target": "current",
            "res_id": reservation_ids and reservation_ids[0] or False
        }

    @api.model
    # def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False,
    #                    lazy=True, expand=False, expand_limit=None, expand_orderby=False):
    def web_read_group(self, domain, fields, groupby, limit=None, offset=0, orderby=False, lazy=True):
        res = super(Property, self).web_read_group(domain, fields, groupby, limit, offset, orderby,
                                                   lazy)
        if res.get('groups') and groupby and groupby[0] == 'floor':
            res['groups'] = sorted(res['groups'], key=lambda item: int(item['floor']))

        return res

    def _maintenance_count(self):
        maintenance_obj = self.env['repair.order']
        for unit in self:
            maintenance_ids = maintenance_obj.search([('product_id.product_tmpl_id', '=', unit.id)])
            unit.maintenance_count = len(maintenance_ids)


    def write(self, vals):
        records = super().write(vals)
        for record in self:
            if record.active == False and record.state != 'inactive':
                record.update({
                    'state': 'inactive'
                })
        return records

    def view_maintenance(self):
        maintenance_ids = self.env['repair.order'].search([('product_id.product_tmpl_id', 'in', self.ids)])

        return {
            'name': _('Maintenance Requests'),
            'domain': [('id', 'in', maintenance_ids.ids)],
            'view_type': 'form',
            'view_mode': 'list,form',
            'res_model': 'repair.order',
            'type': 'ir.actions.act_window',
            'view_id': False,
            'target': 'current',
        }

    def view_reservations(self):
        reservation_obj = self.env["property.reservation"]
        reservations_ids = reservation_obj.search([("property_id", "=", self.ids)])
        reservations = []
        for obj in reservations_ids:
            reservations.append(obj.id)
        return {
            "name": _("Reservation"),
            "domain": [("id", "in", reservations)],
            "view_type": "form",
            "view_mode": "list,form",
            "res_model": "property.reservation",
            "type": "ir.actions.act_window",
            "view_id": False,
            "target": "current",
        }

    def _reservation_count(self):
        reservation_obj = self.env["property.reservation"]
        for property_id in self:
            property_id.reservation_count = len(reservation_obj.search([("property_id", "=", property_id.id)]))
