from odoo import api, fields, models, _
from odoo.exceptions import UserError
import json
from odoo.tools.misc import formatLang, get_lang
from dateutil.relativedelta import relativedelta
from datetime import timedelta
import calendar

import ast

PROJECT_WORKSITE_TYPE = [
    ("tower", "Tower"),
    ("villa", "Villa"),
    ("commercial", "Commercial (Mall)"),
    ("plots", "Open Plots"),
    ("warehouse", "Warehouse"),
]


class Condominium(models.Model):
    _name = "condominium.worksite"
    _description = "condominium Worksite"
    _inherit = ["mail.thread", "mail.activity.mixin"]
    _order = "sequence, id"

    def set_is_enabled(self):
        self.write({'is_enabled': not self.is_enabled})

    image_1920 = fields.Image("Image", max_width=1920, max_height=1920)
    is_enabled = fields.Boolean("Enabled", default=True)
    is_demo_worksite = fields.Boolean("Demo Worksite")
    is_sub_enabled = fields.Boolean("Sub Enabled", related="parent_id.is_enabled")
    # Project Fields
    name = fields.Char("Name", size=64, required=True)
    active = fields.Boolean("Active", default=True, )

    default_code = fields.Char("Code", size=16)
    sequence = fields.Integer(default=10, index=True)

    partner_id = fields.Many2one("res.partner", "Owner")
    region_id = fields.Many2one("region.region", "Region")

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
    attachment_line_ids = fields.One2many("attachment.line", "condominium_worksite_id", "Documents")

    license_code = fields.Char("License Code", size=16)
    license_date = fields.Date("License Date")
    date_added = fields.Date("Date Added to Notarization")
    license_location = fields.Char("License Notarization")

    utility_ids = fields.One2many("property.utilities", "project_id")
    maintenance_type = fields.Selection(selection=[("fix", "Fix Cost"), ("sft", "Per SFT")], default="fix")
    maintenance_charges = fields.Float()
    maintenance_count = fields.Integer(compute='_maintenance_count', string='Maintenance Count')

    # Project
    construction_date = fields.Date("Construction Date")
    purchase_date = fields.Date("Purchase Date")
    launch_date = fields.Date("Launching Date")

    no_of_floors = fields.Integer("# Floors")
    no_of_shops = fields.Integer("# Shops")
    no_of_towers = fields.Integer("# Towers")
    no_of_villa = fields.Integer("# Villa")
    no_of_property = fields.Integer("# Total Numbers of Property")

    parent_id = fields.Many2one("project.worksite", "Main Property")
    child_ids = fields.One2many("project.worksite", "parent_id", "Sub Property")

    property_plan_ids = fields.One2many("attachment.line", "project_plan_id", string="Plans", copy=True)
    amenities_ids = fields.Many2many("project.amenities", "condominium_worksite_amenities_rel", "pidcon", "aidcon")

    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    property_ids = fields.Many2many("product.template", "property_condominium_product_template_rel", 'p_id_co', 'pw_id_co',
                                    string="Properties")

    project_is_readonly = fields.Boolean(compute="_compute_is_readonly")
    sub_project_is_readonly = fields.Boolean(compute="_compute_is_readonly")

    sub_project_count = fields.Integer(compute="_compute_sub_project_count")
    property_count = fields.Integer(compute="_compute_property_count")

    visible_button_property = fields.Boolean(compute="_compute_visible_button")
    visible_button_project = fields.Boolean(compute="_compute_visible_button")

    project_size = fields.Float("Project Size (Sq. ft)", digits=(16, 8))
    unit_of_measure = fields.Selection([("m", "m²"), ("yard", "Yard²")], default="m", required=True)
    converted_area = fields.Float("Converted Size", digits=(16, 2))

    # Project
    project_type = fields.Selection(selection=PROJECT_WORKSITE_TYPE, default="tower", )
    net_price = fields.Float("Cost Price", compute="_calc_price", store=True)
    price_before_discount = fields.Float("Price Before Discount", compute="_calc_price", store=True)

    # Property
    props_per_floors = fields.Integer("Property per Floor")
    floor = fields.Integer("Floor")
    project_area = fields.Float("Project Area m²")

    discount_type = fields.Selection([("percentage", "Percentage"), ("amount", "Amount")])
    discount = fields.Float("Discount")

    property_price_type = fields.Selection(selection=[("fix", "Fix Cost"), ("sft", "Per SFT")], default="sft")
    price_per_m = fields.Float("Price Per m²", )
    property_area = fields.Float("Property Area")
    property_type_id = fields.Many2one("property.type", "Property Type")

    total_area = fields.Float(compute="_compute_total_area")
    sold_area = fields.Float(compute="_compute_total_area")
    available_area = fields.Float(compute="_compute_total_area")
    available_units = fields.Float(compute="_compute_total_area")
    sold_units = fields.Float(compute="_compute_total_area")
    total_units = fields.Integer(string="Total Properties", compute="_compute_total_units")

    total_value_of_project = fields.Float(compute="_calc_total")
    amenities_charges = fields.Float(compute="_calc_total")
    total_maintenance_collection = fields.Float(compute="_calc_maintenance")

    is_shop = fields.Boolean(default=False)

    promotion_ids = fields.Many2many('promotions.property', string="Promotions")
    main_project_id = fields.Many2one(
        'project.worksite',
        string='Parent Project',
        help="Main project associated to this condominium."
    )

    _sql_constraints = [
        (
            "unique_project_worksite_code",
            "UNIQUE (default_code,region_id)",
            "Project Worksite code must be unique!",
        ),
    ]

    color = fields.Integer("Color Index", default=0)
    kanban_dashboard = fields.Text(compute='_kanban_dashboard')
    kanban_dashboard_graph = fields.Text(compute='_kanban_dashboard_graph')

    # json_activity_data = fields.Text(compute='_get_json_activity_data')
    # show_on_dashboard = fields.Boolean(string='Show journal on dashboard',
    #                                    help="Whether this journal should be displayed on the dashboard or not",
    #                                    default=True)
    # entries_count = fields.Integer(compute='_compute_entries_count')

    def _kanban_dashboard(self):
        for rec in self:
            rec.kanban_dashboard = json.dumps(rec.get_project_worksite_dashboard_datas())

    def get_project_worksite_dashboard_datas(self):
        currency = self.company_id.currency_id

        if self.child_ids:
            property_ids = self.env['product.template'].search([('condominium_worksite_id', 'in', self.child_ids.ids)])

            number_available = property_ids.filtered(lambda x: x.state == 'free')
            number_booked = property_ids.filtered(lambda x: x.state == 'reserved')
            number_sold = property_ids.filtered(lambda x: x.state == 'sold')
            number_rented = property_ids.filtered(lambda x: x.state == 'on_lease')

        else:
            property_ids = self.env['product.template'].search([('condominium_worksite_id', 'in', self.ids)])

            number_available = property_ids.filtered(lambda x: x.state == 'free')
            number_booked = property_ids.filtered(lambda x: x.state == 'reserved')
            number_sold = property_ids.filtered(lambda x: x.state == 'sold')
            number_rented = property_ids.filtered(lambda x: x.state == 'on_lease')

        sum_available = sum(number_available.mapped('net_price'))
        sum_booked = sum(number_booked.mapped('net_price'))
        sum_sold = sum(number_sold.mapped('net_price'))
        sum_rented = sum(number_rented.mapped('net_price'))

        return {
            'company_count': len(self.env.companies),
            'number_available': len(number_available),
            'number_booked': len(number_booked),
            'number_sold': len(number_sold),
            'number_rented': len(number_rented),
            'sum_available': formatLang(self.env, currency.round(sum_available) + 0.0, currency_obj=currency),
            'sum_booked': formatLang(self.env, currency.round(sum_booked) + 0.0, currency_obj=currency),
            'sum_sold': formatLang(self.env, currency.round(sum_sold) + 0.0, currency_obj=currency),
            'sum_rented': formatLang(self.env, currency.round(sum_rented) + 0.0, currency_obj=currency),
        }

    def _kanban_dashboard_graph(self):
        for rec in self:
            rec.kanban_dashboard_graph = json.dumps(rec.get_bar_graph_datas())
            # rec.kanban_dashboard_graph = False

    # def _get_bar_graph_select_query(self):
    #     sign = ''
    #     return ('''
    #         SELECT
    #             ''' + sign + ''' + SUM(move.amount_residual_signed) AS total,
    #             MIN(invoice_date_due) AS aggr_date
    #         FROM account_move move
    #         WHERE move.project_worksite_id IN %(project_worksite_id)s
    #         AND move.state = 'posted'
    #         AND move.payment_state in ('not_paid', 'partial')
    #         AND move.move_type IN %(invoice_types)s
    #     ''', {
    #         'invoice_types': tuple(self.env['account.move'].get_invoice_types(True)),
    #         'project_worksite_id': self.id,
    #     })

    def get_bar_graph_datas(self):
        data = []
        reservation_obj = self.env['property.reservation']
        today = fields.Date.today()
        project_ids = self.child_ids.ids if self.child_ids else self.ids
        first = today.replace(day=1)
        for i in range(5):
            last = first + relativedelta(months=1) - timedelta(days=1)
            month_name = calendar.month_name[last.month]
            property_area = sum(
                reservation_obj.search([('project_id', 'in', project_ids), ('state', 'not in', ['draft', 'canceled']),
                                        ('date', '>', first),
                                        ('date', '<', last)]).mapped('property_area'))
            data.append({'label': _(month_name), 'value': property_area, 'type': 'past'})
            first -= relativedelta(months=1)

        data.reverse()
        return [{'values': data, 'title': '', 'key': _('Property SFT'), 'is_sample_data': False}]

    #
    # def _get_json_activity_data(self):
    #     for journal in self:
    #         activities = []
    #         # search activity on move on the journal
    #         sql_query = '''
    #             SELECT act.id,
    #                 act.res_id,
    #                 act.res_model,
    #                 act.summary,
    #                 act_type.name as act_type_name,
    #                 act_type.category as activity_category,
    #                 act.date_deadline,
    #                 m.date,
    #                 m.ref,
    #                 CASE WHEN act.date_deadline < CURRENT_DATE THEN 'late' ELSE 'future' END as status
    #             FROM account_move m
    #                 LEFT JOIN mail_activity act ON act.res_id = m.id
    #                 LEFT JOIN mail_activity_type act_type ON act.activity_type_id = act_type.id
    #             WHERE act.res_model = 'account.move'
    #                 AND m.journal_id = %s
    #         '''
    #         self.env.cr.execute(sql_query, (journal.id,))
    #         for activity in self.env.cr.dictfetchall():
    #             act = {
    #                 'id': activity.get('id'),
    #                 'res_id': activity.get('res_id'),
    #                 'res_model': activity.get('res_model'),
    #                 'status': activity.get('status'),
    #                 'name': (activity.get('summary') or activity.get('act_type_name')),
    #                 'activity_category': activity.get('activity_category'),
    #                 'date': odoo_format_date(self.env, activity.get('date_deadline'))
    #             }
    #             if activity.get('activity_category') == 'tax_report' and activity.get('res_model') == 'account.move':
    #                 act['name'] = activity.get('ref')
    #
    #             activities.append(act)
    #         journal.json_activity_data = json.dumps({'activities': activities})
    #
    # def _compute_entries_count(self):
    #     res = {
    #         r['journal_id'][0]: r['journal_id_count']
    #         for r in self.env['account.move'].read_group(
    #             domain=[('journal_id', 'in', self.ids)],
    #             fields=['journal_id'],
    #             groupby=['journal_id'],
    #         )
    #     }
    #     for journal in self:
    #         journal.entries_count = res.get(journal.id, 0)

    def action_create_new(self):
        pass

    def open_action(self):
        action = False
        domain = []

        if not self.parent_id and not self.child_ids:
            action = self.env.ref('real_estate_bits.action_project_worksite_act_window').sudo().read()[0]
            domain = ast.literal_eval(action['domain'])
            domain.append(('id', '=', self.id))
            form_view = [(self.env.ref('real_estate_bits.project_worksite_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view
            action['res_id'] = self.id

        elif self.child_ids:
            action = self.env.ref('real_estate_bits.action_sub_project_worksite_act_window').sudo().read()[0]
            domain = ast.literal_eval(action['domain'])
            domain.append(('id', 'in', self.child_ids.ids))

        elif self.parent_id and not self.property_ids:
            action = self.env.ref('real_estate_bits.action_sub_project_worksite_act_window').sudo().read()[0]
            domain = ast.literal_eval(action['domain'])
            domain.append(('id', 'in', self.ids))

            form_view = [(self.env.ref('real_estate_bits.sub_project_worksite_form').id, 'form')]
            if 'views' in action:
                action['views'] = form_view + [(state, view) for state, view in action['views'] if view != 'form']
            else:
                action['views'] = form_view

            action['res_id'] = self.id

        elif self.property_ids:
            action = self.env.ref('real_estate_bits.action_property_act_window').sudo().read()[0]
            domain = ast.literal_eval(action['domain'])
            domain.append(('id', 'in', self.property_ids.ids))

        if self._context.get('search_default_available'):
            if self.child_ids:
                action = self.env.ref('real_estate_bits.action_property_act_window').sudo().read()[0]
                domain = ast.literal_eval(action['domain'])
                domain.append(('id', 'in', self.child_ids.mapped('property_ids').ids))
            domain.append(('state', '=', 'free'))

        elif self._context.get('search_default_booked'):
            if self.child_ids:
                action = self.env.ref('real_estate_bits.action_property_act_window').sudo().read()[0]
                domain = ast.literal_eval(action['domain'])
                domain.append(('id', 'in', self.child_ids.mapped('property_ids').ids))
            domain.append(('state', '=', 'reserved'))

        elif self._context.get('search_default_sold'):
            if self.child_ids:
                action = self.env.ref('real_estate_bits.action_property_act_window').sudo().read()[0]
                domain = ast.literal_eval(action['domain'])
                domain.append(('id', 'in', self.child_ids.mapped('property_ids').ids))
            domain.append(('state', '=', 'sold'))

        elif self._context.get('search_default_rented'):
            if self.child_ids:
                action = self.env.ref('real_estate_bits.action_property_act_window').sudo().read()[0]
                domain = ast.literal_eval(action['domain'])
                domain.append(('id', 'in', self.child_ids.mapped('property_ids').ids))
            domain.append(('state', '=', 'on_lease'))

        if action:
            action['domain'] = domain
            action['context'] = {'create': False}

        return action

    def unlink(self):
        for rec in self:
            if not rec.parent_id and rec.child_ids:
                raise UserError(_("Please Delete Sub Project First!"))
            elif rec.parent_id and rec.property_ids:
                raise UserError(_("Please Delete Property First!"))
            else:
                return super(Condominium, self).unlink()

    def _compute_total_area(self):
        ProductTmpl = self.env['product.template'].sudo()
        area_field = 'property_area'


        for rec in self:

            domain = [('condominium_worksite_id', '=', rec.id)]
            products = ProductTmpl.search(domain)
            free_products = products.filtered(lambda p: (p.state or '') == 'free')
            sold_products = products.filtered(lambda p: (p.state or '') == 'sold')
            reserved_products = products.filtered(lambda p: (p.state or '') == 'reserved')


            total_area = sum(products.mapped(area_field)) if products else 0.0
            free_area = sum(free_products.mapped(area_field)) if free_products else 0.0
            sold_area = (
                    (sum(sold_products.mapped(area_field)) if sold_products else 0.0) +
                    (sum(reserved_products.mapped(area_field)) if reserved_products else 0.0)
            )
            rec.total_area = total_area
            rec.sold_area = sold_area
            rec.available_area = free_area
            rec.available_units = len(free_products)
            rec.sold_units = (len(sold_products) + len(reserved_products))

    @api.depends('sold_units', 'available_units')
    def _compute_total_units(self):
        for rec in self:
            rec.total_units = rec.sold_units + rec.available_units


    def _calc_maintenance(self):
        for rec in self:
            rec.total_maintenance_collection = sum(rec.property_ids.mapped("maintenance_charges"))

    @api.depends("child_ids", "property_ids")
    def _calc_total(self):
        for rec in self:
            rec.amenities_charges = sum(rec.property_ids.mapped("total_utilities"))
            if rec.child_ids:
                rec.total_value_of_project = sum(rec.child_ids.mapped("total_value_of_project"))
            else:
                rec.total_value_of_project = sum(rec.property_ids.mapped("net_price"))

    @api.onchange("unit_of_measure", "project_area")
    def _onchange_converted_area(self):
        for rec in self:
            if rec.unit_of_measure == "m":
                converted_area = rec.project_area * 0.092903
            elif rec.unit_of_measure == "yard":
                converted_area = rec.project_area * 0.111111
            else:
                converted_area = rec.project_area

            rec.converted_area = converted_area

    @api.onchange("converted_area")
    def _onchange_project_area_net(self):
        for rec in self:
            if rec.unit_of_measure == "m":
                project_area = rec.converted_area / 0.092903
            elif rec.unit_of_measure == "yard":
                project_area = rec.converted_area / 0.111111
            else:
                project_area = rec.converted_area

            rec.project_area = project_area

    def _compute_visible_button(self):
        for rec in self:
            visible_button_property = visible_button_project = False
            if rec.parent_id:
                visible_button_property = True
                if rec.property_ids:
                    visible_button_property = False
            else:
                visible_button_project = True
                if rec.child_ids:
                    visible_button_project = False

            rec.visible_button_project = visible_button_project
            rec.visible_button_property = visible_button_property

    def _compute_sub_project_count(self):
        for rec in self:
            rec.sub_project_count = len(self.child_ids)

    def _compute_property_count(self):
        for rec in self:
            #rec.property_count = 1
            obj_ids = self
            rec.property_ids = self.env["product.template"].search([("condominium_worksite_id", "in", obj_ids.ids)])
            rec.property_count = len(self.env["product.template"].search([("condominium_worksite_id", "in", obj_ids.ids)]))

    def _compute_is_readonly(self):
        for rec in self:
            sub_project_is_readonly = project_is_readonly = True
            if not rec.parent_id:
                project_is_readonly = False
                if rec.property_ids or rec.child_ids:
                    project_is_readonly = True

            else:
                sub_project_is_readonly = False
                if rec.property_ids:
                    sub_project_is_readonly = True

            rec.sub_project_is_readonly = sub_project_is_readonly
            rec.project_is_readonly = project_is_readonly

    @api.depends("price_per_m", "discount_type", "discount", "property_area")
    def _calc_price(self):
        for rec in self:
            if rec.property_price_type == 'sft':
                rec.price_before_discount = rec.price_per_m * rec.property_area
            else:
                rec.price_before_discount = rec.price_per_m

            if rec.discount_type == "amount":
                rec.net_price = rec.price_before_discount - rec.discount
            elif rec.discount_type == "percentage":
                rec.net_price = rec.price_before_discount - ((rec.discount / 100) * rec.price_before_discount)
            else:
                rec.net_price = rec.price_before_discount

    def action_create_sub_project(self):
        i = 1
        if self.no_of_property:
            while i <= self.no_of_property:
                vals = {
                    "parent_id": self.id,
                    "property_ids": False,
                    "name": "{}-{}".format(self.name, i),
                    "default_code": "{}-{}".format(self.default_code, i),
                    "no_of_shops": False,
                    "no_of_property": 0,
                }
                self.copy(vals)
                i += 1

            if self.project_type in ["tower", "commercial"] and self.no_of_shops > 0:
                vals = {
                    "parent_id": self.id,
                    "property_ids": False,
                    "no_of_floors": 0,
                    "props_per_floors": 0,
                    "name": "{}-Shops".format(self.name),
                    "default_code": "{}-Shops".format(self.default_code),
                    "is_shop": True,
                    "no_of_shops": self.no_of_shops,
                }
                self.copy(vals)

    def action_create_property(self):
        property_pool = self.env["product.template"]
        props = []


        default_vals = {
            "condominium_worksite_id": self.id,
            "worksite_id": self.parent_id.parent_id.id if self.parent_id and self.parent_id.parent_id else False,
            "project_worksite_id": self.parent_id.id if self.parent_id else False,
            "company_id": self.company_id.id,
            "is_property": True,
            "region_id": self.region_id.id,
            "property_type_id": self.property_type_id.id,
            "property_area": self.property_area,
            "price_per_m": self.price_per_m,
            "property_price_type": self.property_price_type,
            "maintenance_type": self.maintenance_type,
            "maintenance_charges": self.maintenance_charges,
            "net_price": self.net_price,
            "description": self.description,
            "partner_id": self.partner_id.id,
        }

        if self.project_type in ["tower", 'commercial']:
            i = 1
            no = 1

            if self.is_shop and self.no_of_shops:
                while i <= self.no_of_shops:
                    doc_id = self.env['documents.document'].create({
                        'name': self.name + "-" + str(i),
                        "owner_id": self.env.ref('base.user_root').id,
                        "type": "folder",
                        "access_internal": "view",
                        'folder_id': self.carpet_id.id
                    })
                    default_vals.update({
                        "name": self.name + "-" + str(i),
                        "default_code": "S-" + self.default_code + "-" + str(i),
                        "is_shop": True,
                        "project_type": 'shop',
                        "carpet_id": doc_id.id,
                    })
                    prop_id = property_pool.create(default_vals)
                    prop_id._onchange_converted_area()
                    props.append(prop_id.id)
                    i += 1
            else:
                while i <= self.no_of_floors:
                    j = 1
                    while j <= self.props_per_floors:
                        doc_id = self.env['documents.document'].create({
                            'name':  self.name + "-" + str(i) + "-" + str(j),
                            "owner_id": self.env.ref('base.user_root').id,
                            "type": "folder",
                            "access_internal": "view",
                            'folder_id': self.carpet_id.id
                        })
                        default_vals.update({
                            "name": self.name + "-" + str(i) + "-" + str(j),
                            "default_code": "T-" + self.default_code + "-" + str(i) + "-" + str(j),
                            "floor": str(i),
                            "carpet_id": doc_id.id,
                            "project_type": self.project_type,
                            "utility_ids": [
                                (0, 0, {"name": rec.name, "price": rec.price})
                                for rec in self.utility_ids
                            ],
                            "carpet_id": doc_id.id,
                        })

                        prop_id = property_pool.create(default_vals)
                        prop_id._onchange_converted_area()
                        props.append(prop_id.id)
                        j += 1
                    i += 1
                no += 1
            self.property_ids = [(6, 0, props)]

        elif self.project_type == "villa" and self.no_of_villa:
            i = 1
            while i <= self.no_of_villa:
                doc_id = self.env['documents.document'].create({
                    'name': self.name + "-" + str(i),
                    "owner_id": self.env.ref('base.user_root').id,
                    "type": "folder",
                    "access_internal": "view",
                    'folder_id': self.carpet_id.id
                })
                default_vals.update({
                    "name": self.name + "-" + str(i),
                    "project_type": self.project_type,
                    "default_code": "V-" + self.default_code + "-" + str(i),
                    "carpet_id": doc_id.id,
                })
                prop_id = property_pool.create(default_vals)
                prop_id._onchange_converted_area()
                props.append(prop_id.id)
                i += 1
            self.property_ids = [(6, 0, props)]

        elif self.project_type in ["plots", "warehouse"] and self.no_of_property:
            i = 1
            if self.project_type == "plots":
                code = "P-"
            else:
                code = "W-"

            while i <= self.no_of_property:
                doc_id = self.env['documents.document'].create({
                    'name': self.name + "-" + str(i),
                    "owner_id": self.env.ref('base.user_root').id,
                    "type": "folder",
                    "access_internal": "view",
                    'folder_id': self.carpet_id.id
                })
                default_vals.update({
                    "project_type": self.project_type,
                    "name": self.name + "-" + str(i),
                    "default_code": code + self.default_code + "-" + str(i),
                    "carpet_id": doc_id.id,
                })
                prop_id = property_pool.create(default_vals)
                prop_id._onchange_converted_area()
                props.append(prop_id.id)
                i += 1

            self.property_ids = [(6, 0, props)]

    def _maintenance_count(self):
        maintenance_obj = self.env['repair.order']
        for project in self:
            maintenance_ids = maintenance_obj.search([('project_id', '=', project.id)])
            project.maintenance_count = len(maintenance_ids)

    def view_maintenance(self):
        maintenance_ids = self.env['repair.order'].search([('project_id', 'in', self.ids)])

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

    def toggle_active_value(self):
        for record in self:
            record.active = not record.active

    def action_view_all_property(self):
        action = self.env.ref("real_estate_bits.action_property_act_window").read()[0]
        action["domain"] = [
            ("is_property", "=", True),
            ("condominium_worksite_id", "in", self.ids),
        ]
        return action

    def action_view_all_sub_project(self):
        action = self.env.ref("real_estate_bits.action_sub_project_worksite_act_window").read()[0]
        action["domain"] = [("parent_id", "=", self.id)]
        action["context"] = {'default_parent_id': self.parent_id and self.parent_id.id or self.id}
        return action

    def edit_action(self):
        project_id = self.id

        return {
            'name': 'Project',
            'view_type': 'form',
            'view_mode': 'form',
            'res_id': project_id,
            'res_model': 'project.worksite',
            'type': 'ir.actions.act_window',
            'target': 'current',

        }

    def delete_action(self):
        self.unlink()
