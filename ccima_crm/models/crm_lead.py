# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
from datetime import datetime, date, timedelta


class CrmLead(models.Model):
    _inherit = "crm.lead"

    # -------------------------------------------------------------------------
    # FIELDS
    # -------------------------------------------------------------------------

    show_prospect_fields = fields.Boolean(
        compute="_compute_show_fields",
        store=False
    )
    show_appointment_fields = fields.Boolean(
        compute="_compute_show_fields",
        store=False
    )
    show_opportunity_fields = fields.Boolean(
        compute="_compute_show_fields",
        store=False
    )
    real_interest = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Real Interest"
    )
    profile = fields.Selection(
        [("user", "User"), ("investor", "Investor")],
        string="Profile"
    )
    authority = fields.Selection(
        [("client", "Client"), ("partner", "Partner")],
        string="Authority"
    )
    product = fields.Selection(
        [("pbb", "PBB"), ("pbc", "PBC")],
        string="Product"
    )
    has_budget = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Has Budget"
    )
    timeline = fields.Selection(
        [("investment", "Investment"), ("delivery", "Delivery")],
        string="Timeline"
    )
    location_defined = fields.Selection(
        [("yes", "Yes"), ("no", "No")],
        string="Location Defined"
    )
    commitment_level = fields.Selection(
        [("high", "High"), ("medium", "Medium"), ("low", "Low")],
        string="Commitment Level"
    )
    detailed_presentation = fields.Boolean(
        string="Detailed Presentation"
    )

    tour_completed = fields.Selection(
        [("virtual", "Virtual"), ("physical", "Physical")],
        string="Tour Completed"
    )
    days_since_last_activity = fields.Integer(
        string="Days Since Last Activity",
        compute="_compute_days_since_last_activity",
        store=False
    )
    contacted = fields.Boolean(
        string="Contacted",
        compute="_compute_contacted",
        store=True,
        help="True if the lead has at least one activity registered"
    )
    property_date = fields.Date(
        string="Property Reserved Date",
        compute="_compute_property_date",
        store=True
    )
    property_date_display = fields.Char(
        string="Property Reserved Date (Display)",
        compute="_compute_property_date_display",
        store=True
    )

    delivery_date_crm = fields.Date(
        string="Delivery Date",
        compute="_compute_delivery_date",
        store=True
    )
    delivery_date_display = fields.Char(
        string="Delivery Date (Display)",
        compute="_compute_delivery_date_display",
        store=True
    )

    calculated_closing_date = fields.Char(
        string="Time to Closing",
        compute="_compute_calculated_closing_date",
        store=True,
        help="Business days between property reserved date and delivery"
    )
    expected_revenue = fields.Monetary(
        string="Expected Revenue",
        currency_field="company_currency",
        compute="_compute_expected_revenue_from_last_order",
        store=False,
        tracking=True,
    )
    expected_revenue_display = fields.Char(
        string="Expected Revenue",
        compute="_compute_expected_revenue_display",
        store=False,
        help="Expected revenue formatted with thousands separator"
    )
    interaction_count_frozen = fields.Integer(
        string="Frozen Interaction Count",
        default=0,
        copy=False,
        help="Frozen count of interactions when reaching 'Apartado' stage"
    )
    interaction_count = fields.Integer(
        string="Interactions",
        compute="_compute_interaction_count",
        store=True,
        readonly=True,
        help="Number of calendar activities until reaching 'Apartado' stage. This value freezes once the lead reaches 'Apartado' stage."
    )

    # -------------------------------------------------------------------------
    # COMPUTE METHODS
    # -------------------------------------------------------------------------

    @api.depends("activity_ids", "activity_ids.date_deadline")
    def _compute_days_since_last_activity(self):
        for record in self:
            today = fields.Date.context_today(record)
            has_future = any(
                a.date_deadline and a.date_deadline > today
                for a in record.activity_ids
            )
            if has_future:
                record.days_since_last_activity = 0
            else:
                past_deadlines = [
                    a.date_deadline
                    for a in record.activity_ids
                    if a.date_deadline and a.date_deadline <= today
                ]
                if past_deadlines:
                    latest_deadline = max(past_deadlines)
                    record.days_since_last_activity = (today - latest_deadline).days
                else:
                    record.days_since_last_activity = 0

    @api.depends("activity_ids")
    def _compute_contacted(self):
        for record in self:
            record.contacted = bool(record.activity_ids)

    @api.depends("property_id")
    def _compute_delivery_date(self):
        for record in self:
            date_val = False
            try:
                if record.property_id and record.property_id.exists():
                    if hasattr(record.property_id, "product_tmpl_id"):
                        template = record.property_id.product_tmpl_id
                        if template and template.exists() and hasattr(template, "closing_date"):
                            raw_val = getattr(template, "closing_date", False)
                            if raw_val:
                                date_val = raw_val
                    if not date_val and hasattr(record.property_id, "closing_date"):
                        raw_val = getattr(record.property_id, "closing_date", False)
                        if raw_val:
                            date_val = raw_val
            except Exception:
                pass
            if date_val:
                from odoo import fields as odoo_fields
                if isinstance(date_val, str):
                    try:
                        date_val = odoo_fields.Date.to_date(date_val)
                    except:
                        date_val = False
                elif isinstance(date_val, datetime):
                    date_val = date_val.date()
            record.delivery_date_crm = date_val

    @api.depends("delivery_date_crm")
    def _compute_delivery_date_display(self):
        for record in self:
            if record.delivery_date_crm:
                record.delivery_date_display = record.delivery_date_crm.strftime("%m/%d/%Y")
            else:
                record.delivery_date_display = ""

    @api.depends("property_id.property_date")
    def _compute_property_date(self):
        for record in self:
            date_val = False
            try:
                if record.property_id and record.property_id.exists():
                    if hasattr(record.property_id, "product_tmpl_id"):
                        template = record.property_id.product_tmpl_id
                        if template and template.exists() and hasattr(template, "property_date"):
                            raw_val = getattr(template, "property_date", False)
                            if raw_val:
                                date_val = raw_val
                    if not date_val and hasattr(record.property_id, "property_date"):
                        raw_val = getattr(record.property_id, "property_date", False)
                        if raw_val:
                            date_val = raw_val
            except Exception:
                pass
            if date_val:
                from odoo import fields as odoo_fields
                if isinstance(date_val, str):
                    try:
                        date_val = odoo_fields.Date.to_date(date_val)
                    except:
                        date_val = False
                elif isinstance(date_val, datetime):
                    date_val = date_val.date()
            record.property_date = date_val

    @api.depends("property_date")
    def _compute_property_date_display(self):
        for record in self:
            if record.property_date:
                record.property_date_display = record.property_date.strftime("%m/%d/%Y")
            else:
                record.property_date_display = ""

    @api.depends("property_date", "delivery_date_crm")
    def _compute_calculated_closing_date(self):
        for record in self:
            result = ""
            if record.property_date:
                if record.delivery_date_crm:
                    start_date = record.delivery_date_crm
                    end_date = record.property_date
                else:
                    start_date = date.today()
                    end_date = record.property_date
                if start_date > end_date:
                    start_date, end_date = end_date, start_date
                business_days = 0
                current_date = start_date
                while current_date <= end_date:
                    if current_date.weekday() < 5:
                        business_days += 1
                    current_date += timedelta(days=1)
                result = f"{business_days} business days"
            record.calculated_closing_date = result

    @api.depends(
        "order_ids",
        "order_ids.state",
        "order_ids.date_order",
        "order_ids.create_date",
        "order_ids.finance_id",
        "order_ids.finance_id.name",
        "order_ids.financial_lines.name",
        "order_ids.financial_lines.gradual_initial_investment",
    )
    def _compute_expected_revenue_from_last_order(self):
        for record in self:
            expected_revenue = 0.0

            valid_orders = record.order_ids.filtered(lambda order: order.state != "cancel")
            latest_order = False
            if valid_orders:
                latest_order = max(
                    valid_orders,
                    key=lambda order: (
                        order.date_order or order.create_date or fields.Datetime.now(),
                        order.id,
                    ),
                )
            elif record.order_ids:
                latest_order = max(
                    record.order_ids,
                    key=lambda order: (
                        order.date_order or order.create_date or fields.Datetime.now(),
                        order.id,
                    ),
                )

            if latest_order and latest_order.finance_id:
                finance_line = latest_order.financial_lines.filtered(
                    lambda line: line.name == latest_order.finance_id.name
                )[:1]
                if finance_line:
                    expected_revenue = finance_line.gradual_initial_investment or 0.0

            record.expected_revenue = expected_revenue

    @api.depends("expected_revenue", "company_currency")
    def _compute_expected_revenue_display(self):
        for record in self:
            if record.expected_revenue:
                amount_str = "{:,.2f}".format(record.expected_revenue)
                currency = record.company_currency or self.env.company.currency_id
                currency_symbol = currency.symbol or ""
                if currency.position == "before":
                    record.expected_revenue_display = f"{currency_symbol}{amount_str}"
                else:
                    record.expected_revenue_display = f"{amount_str} {currency_symbol}"
            else:
                record.expected_revenue_display = "0.00"

    @api.depends("stage_id")
    def _compute_show_fields(self):
        for record in self:
            stage_name = record.stage_id.name if record.stage_id else ""
            record.show_prospect_fields = stage_name in ["Prospecto", "Cita", "Oportunidad de Venta"]
            record.show_appointment_fields = stage_name in ["Cita", "Oportunidad de Venta"]
            record.show_opportunity_fields = stage_name == "Oportunidad de Venta"

    @api.depends("activity_ids", "stage_id", "interaction_count_frozen")
    def _compute_interaction_count(self):
        for record in self:
            stage_name = record.stage_id.name if record.stage_id else ""
            if stage_name == "Apartado" or record.interaction_count_frozen > 0:
                # If in "Apartado" stage or already frozen, use frozen value
                record.interaction_count = record.interaction_count_frozen
            else:
                # Otherwise, count current activities
                record.interaction_count = len(record.activity_ids)

    # -------------------------------------------------------------------------
    # ONCHANGE METHODS
    # -------------------------------------------------------------------------

    @api.onchange("stage_id")
    def _onchange_stage_id(self):
        if not self.stage_id or not self._origin.stage_id:
            return
        current_stage_name = self._origin.stage_id.name
        new_stage_name = self.stage_id.name
        errors = self._validate_stage_transition(current_stage_name, new_stage_name)
        if errors:
            self.stage_id = self._origin.stage_id
            return {
                "warning": {
                    "title": _("Validation Error"),
                    "message": _("Please complete the following fields before advancing:\n\n• %s") % ("\n• ".join(errors))
                }
            }

    # -------------------------------------------------------------------------
    # CRUD METHODS
    # -------------------------------------------------------------------------

    def write(self, vals):
        if "stage_id" in vals:
            new_stage = self.env["crm.stage"].browse(vals["stage_id"])
            for record in self:
                if record.stage_id.id == vals["stage_id"]:
                    continue
                current_stage_name = record.stage_id.name
                new_stage_name = new_stage.name
                errors = record._validate_stage_transition(current_stage_name, new_stage_name)
                if errors:
                    raise UserError(_(
                        "Please complete the following fields before advancing:\n\n• %s"
                    ) % ("\n• ".join(errors)))

                # Freeze interaction count when reaching "Apartado" stage
                if new_stage_name == "Apartado" and current_stage_name != "Apartado":
                    vals["interaction_count_frozen"] = len(record.activity_ids)

        return super(CrmLead, self).write(vals)

    # -------------------------------------------------------------------------
    # HELPER METHODS
    # -------------------------------------------------------------------------

    def _get_stage_order(self, stage_name):
        stage_order = {
            "Lead": 0,
            "Prospecto": 1,
            "Cita": 2,
            "Oportunidad de Venta": 3
        }
        return stage_order.get(stage_name, 0)

    def _validate_stage_transition(self, current_stage_name, new_stage_name):
        self.ensure_one()
        errors = []
        current_order = self._get_stage_order(current_stage_name)
        new_order = self._get_stage_order(new_stage_name)
        if new_order <= current_order:
            return errors
        if current_order == 1 and new_order > 1:
            if not self.real_interest:
                errors.append(_("Real Interest"))
            if not self.profile:
                errors.append(_("Profile"))
            if not self.authority:
                errors.append(_("Authority"))
            if not self.product:
                errors.append(_("Product"))
            if not self.has_budget:
                errors.append(_("Has Budget"))
            if not self.location_defined:
                errors.append(_("Location Defined"))
        elif current_order == 2 and new_order > 2:
            if not self.commitment_level:
                errors.append(_("Commitment Level"))
        return errors
