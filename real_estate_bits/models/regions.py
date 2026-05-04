from odoo import api, fields, models, _


class Regions(models.Model):
    _name = "region.region"
    _description = "Region"
    _parent_name = "region_id"
    _parent_store = True
    _order = "complete_name"
    _rec_name = "complete_name"
    _inherit = ["mail.thread", "mail.activity.mixin"]

    @api.depends("name", "region_id")
    def _compute_complete_name(self):
        """Forms complete name of region from region to child region."""
        name = self.name
        current = self
        while current.region_id:
            current = current.region_id
            name = "%s / %s" % (current.name, name)
        self.complete_name = name

    @api.depends("name", "region_id.complete_name")
    def _compute_complete_name(self):
        """Forms complete name of location from parent location to child location."""
        if self.region_id.complete_name:
            self.complete_name = "%s / %s" % (self.region_id.complete_name, self.name)
        else:
            self.complete_name = self.name

    name = fields.Char("Name", required=True)
    complete_name = fields.Char("Complete Name", compute="_compute_complete_name", recursive=True, store=True)
    region_id = fields.Many2one("region.region", "Parent Region", ondelete="cascade")
    child_ids = fields.One2many("region.region", "region_id", "Child Region")
    parent_left = fields.Integer("Left Parent", index=True)
    parent_right = fields.Integer("Right Parent", index=True)
    discount_account = fields.Many2one("account.account", "Discount Account")
    expanses_account = fields.Many2one("account.account", "Managerial Expenses Account")
    parent_path = fields.Char(index=True, unaccent=False)
    company_id = fields.Many2one("res.company", string="Company", default=lambda self: self.env.company)
    lat_lng_ids = fields.One2many("lat.lng.line", "region_id", string="Lat Lng List", copy=True)
    map = fields.Char("Map")
    street = fields.Char()
    street2 = fields.Char()
    zip = fields.Char(change_default=True)
    city = fields.Char()
    state_id = fields.Many2one("res.country.state", string="State", ondelete="restrict",
                               domain="[('country_id', '=?', country_id)]")
    country_id = fields.Many2one("res.country", string="Country", ondelete="restrict")
    country_code = fields.Char(related="country_id.code", string="Country Code")

    project_count = fields.Integer(compute="_compute_project_count")
    address = fields.Char("Address")

    def _compute_project_count(self):
        for rec in self:
            rec.project_count = len(
                self.env["project.worksite"].search([("region_id", "=", rec.id), ("parent_id", "=", False)]))

    def action_view_all_project(self):
        action = self.env.ref("real_estate_bits.action_project_worksite_act_window").read()[0]
        action["domain"] = [("region_id", "=", self.id), ("parent_id", "=", False)]
        action["context"] = {"default_region_id": self.id}
        return action

    def create_property_project(self):
        self.ensure_one()
        return {
            "name": _("Project"),
            "view_mode": "form",
            "res_model": "project.worksite",
            "type": "ir.actions.act_window",
            "context": {"default_region_id": self.id},
        }


class LatLagLine(models.Model):
    _name = "lat.lng.line"
    _description = 'Lat Lng Line'

    name = fields.Char()
    lat = fields.Float("Latitude", digits=(9, 6), required=True)
    lng = fields.Float("Longitude", digits=(9, 6), required=True)
    url = fields.Char("URL")
    region_id = fields.Many2one("region.region", "Region")
    unit_id = fields.Many2one(
        "product.template", "Unit", domain=[("is_property", "=", True)], required=True
    )

    # @api.onchange("unit_id")
    # def onchange_unit(self):
    #     action_id = self.env.ref("real_estate_bits.action_property_act_window").id
    #     link = "#id={}&action={}&model=product.template&view_type=form".format(self.unit_id.id, action_id)
    #     self.url = link

    @api.onchange("url")
    def onchange_url(self):
        if self.url:
            url = self.url
            self.unit_id = int(((url.split("#")[1]).split("&")[0]).split("=")[1])
        else:
            self.unit_id = None
            # self.state = None
