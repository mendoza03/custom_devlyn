from odoo import models, fields, api
from odoo.exceptions import UserError


class CcimaCommissions(models.Model):
    _name = 'ccima.commissions'
    _description = 'Commissions'

    name = fields.Char(
        string='Name',
        required=True,
        help='Internal name of the commission record'
    )
    state = fields.Selection(
        [
            ('draft', 'Draft'),
            ('reviewed', 'Reviewed'),
            ('paid', 'Paid'),
        ],
        string='Status',
        default='draft',
        required=True,
    )
    origin_id = fields.Many2one(
        'utm.source',
        string='Origen',
        related='lead_id.source_id',
        store=True,
        readonly=False
    )


    partner_id = fields.Many2one(
        comodel_name='res.partner',
        string='Customer',
    )
    reference = fields.Char(
        string='Reference',
    )
    amount_to_commission = fields.Float(
        string='Amount to Commission',
    )
    down_payment = fields.Float(
        string='Down Payment (10%)',
    )
    deposit = fields.Float(
        string='Deposit',
    )
    deposit_date = fields.Date(
        string='Deposit Date',
    )
    contract_date = fields.Date(
        string='Contract Date',
    )
    lead_id = fields.Many2one(
        comodel_name='crm.lead',
        string='Opportunity / Lead',
    )
    employee_id = fields.Many2one(
        comodel_name="hr.employee",
        string="Employee",
        compute="_compute_employee_id",
        store=True,
        readonly=True,
    )
    promotion_name = fields.Char(
        string='Promotion Name',
    )
    region = fields.Char(
        string="Region",
        related="employee_id.work_location_id.name",
        store=True,
        readonly=True,
    )
    total_commission = fields.Float(
        string='Total Commission',
        compute='_compute_totals',
        store=True,
        readonly=True,
    )
    total_amount = fields.Float(
        string='Total Amount',
        compute='_compute_totals',
        store=True,
        readonly=True,
    )
    total_to_pay = fields.Float(
        string='Total To Pay',
        compute='_compute_totals',
        store=True,
        readonly=True,
    )

    commission_line_ids = fields.One2many(
        comodel_name='ccima.commissions.lines',
        inverse_name='commission_id',
        string='Commission Lines',
    )

    finance_amount_total = fields.Float(
        string='Finance Amount Total',
        help='Amount total from selected financial line'
    )
    finance_hitch = fields.Float(
        string='Finance Hitch',
        help='Hitch from selected financial line'
    )
    finance_amount_finance = fields.Float(
        string='Finance Amount Finance',
        help='Amount finance from selected financial line'
    )
    lead_user_id = fields.Many2one(
        comodel_name="res.users",
        string="Lead User",
        related="lead_id.user_id",
        store=True,
        readonly=True,
    )

    finance_descount = fields.Float(
        string='Finance Amount discount',
        help='Amount finance discount'
    )

    @api.depends("lead_user_id")
    def _compute_employee_id(self):
        Employee = self.env["hr.employee"]
        for rec in self:
            if rec.lead_user_id:
                rec.employee_id = Employee.search(
                    [("user_id", "=", rec.lead_user_id.id)],
                    limit=1
                )
            else:
                rec.employee_id = False

    def action_set_reviewed(self):
        for rec in self:
            rec.state = 'reviewed'

    def action_set_paid(self):
        for rec in self:
            rec.state = 'paid'

    def action_set_draft(self):
        for rec in self:
            rec.state = 'draft'

    @api.depends('commission_line_ids.commission',
                 'commission_line_ids.amount',
                 'commission_line_ids.to_pay')
    def _compute_totals(self):
        for record in self:
            total_commission = 0.0
            total_amount = 0.0
            total_to_pay = 0.0

            for line in record.commission_line_ids:
                total_commission += line.commission or 0.0
                total_amount += line.amount or 0.0
                total_to_pay += line.to_pay or 0.0

            record.total_commission = total_commission
            record.total_amount = total_amount
            record.total_to_pay = total_to_pay


    @api.onchange('lead_id')
    def _onchange_lead_id(self):
        for record in self:
            if not record.lead_id:
                record.partner_id = False
                record.finance_amount_total = 0.0
                record.finance_hitch = 0.0
                record.finance_amount_finance = 0.0
                continue

            lead = record.lead_id

            record.partner_id = lead.partner_id

            SaleOrder = self.env['sale.order']
            sale_order = SaleOrder.search(
                [('opportunity_id', '=', lead.id)],
                limit=1,
                order='id desc',
            )

            finance_amount_total = 0.0
            finance_hitch = 0.0
            finance_amount_finance = 0.0

            lot_ref = ''
            finance_descount = 0

            if sale_order:
                financial_lines = getattr(sale_order, 'financial_lines', False)
                finance_plan = getattr(sale_order, 'finance_id', False)

                if sale_order.order_line:
                    lot_ref = sale_order.order_line[0].product_template_id.default_code

                if financial_lines and finance_plan:
                    line = financial_lines.filtered(
                        lambda l: l.name == finance_plan.name
                    )[:1]
                    if line:
                        finance_amount_total = getattr(line, 'amount_total', 0.0) or 0.0
                        finance_hitch = getattr(line, 'hitch', 0.0) or 0.0
                        finance_amount_finance = getattr(line, 'amount_finance', 0.0) or 0.0
                        finance_descount = getattr(line, 'discount_total', 0.0) or 0.0

            record.finance_amount_total = finance_amount_total - finance_descount
            record.finance_hitch = finance_hitch
            record.finance_amount_finance = finance_amount_finance

            record.update({
                'reference': lot_ref,
                'finance_descount': finance_descount,
            })

    def _get_template_total_commission_percent(self, template):
        if not template:
            return 0.0

        if 'total_commission_percent' in template._fields:
            return template.total_commission_percent or 0.0

        lines = getattr(template, 'line_ids', self.env['ccima.commission.source.line'])
        return sum(lines.mapped('commission_percent')) or 0.0

    def _adjust_publicidad_remaining(self):
        CommissionSource = self.env['ccima.commission.source']

        for rec in self:
            if not rec.origin_id:
                continue

            template = CommissionSource.search([('origin_ids', 'in', rec.origin_id.ids)], limit=1)
            total_pct = rec._get_template_total_commission_percent(template)
            if not total_pct:
                continue

            current_pct = sum(rec.commission_line_ids.mapped('commission')) or 0.0
            remaining = total_pct - current_pct

            if remaining <= 0.0000001:
                continue

            pub_line = rec.commission_line_ids.filtered(
                lambda l: (l.position or '').strip().upper() == 'PUBLICIDAD'
            )[:1]
            if not pub_line:
                continue

            new_pct = (pub_line.commission or 0.0) + remaining

            base = pub_line.amount_to_commission or 0.0
            disc = pub_line.discount or 0.0
            new_amount = base * new_pct / 100.0
            new_to_pay = new_amount - disc

            pub_line.with_context(skip_pub_adjust=True).write({
                'commission': new_pct,
                'amount': new_amount,
                'to_pay': new_to_pay,
            })

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        if not self.env.context.get('skip_pub_adjust'):
            rec._adjust_publicidad_remaining()
        return rec

    def write(self, vals):
        res = super().write(vals)
        if not self.env.context.get('skip_pub_adjust'):
            self._adjust_publicidad_remaining()
        return res

    def action_calculate_lines(self):
        CommissionSource = self.env['ccima.commission.source']
        CommissionLine = self.env['ccima.commissions.lines']
        Employee = self.env['hr.employee']

        for record in self:
            if record.commission_line_ids:
                record.commission_line_ids.unlink()

            lead = record.lead_id
            if not lead or not lead.user_id:
                continue

            vendor_employee = Employee.search([('user_id', '=', lead.user_id.id)], limit=1)
            if not vendor_employee:
                continue

            # 2) Detect vendor position from fields stored on hr.employee
            vendor_position = False
            if getattr(vendor_employee, 'asesor', False):
                vendor_position = 'asesor'
            elif getattr(vendor_employee, 'kam', False):
                vendor_position = 'kam'
            elif getattr(vendor_employee, 'gerente', False):
                vendor_position = 'gerente'
            elif getattr(vendor_employee, 'dvn', False):
                vendor_position = 'dvn'
            elif getattr(vendor_employee, 'cco', False):
                vendor_position = 'cco'

            if not vendor_position:
                continue

            domain = [('position', '=', vendor_position)]
            if lead.source_id:
               domain.append(('origin_ids', 'in', [lead.source_id.id]))
            else:
                raise UserError('set source')

            template = CommissionSource.search(domain, limit=1)
            if not template:
                continue

            lot_name = False
            contract_brief = self.env['rev.crm.contract.brief'].search([('lead_id', '=', lead.id)], limit=1)
            if contract_brief:
                lot_name = contract_brief.lot or False

            amount_base = record.finance_amount_total or 0.0
            record.amount_to_commission = amount_base

            def calc_amount(pct):
                return (amount_base * pct / 100.0) if (amount_base and pct) else 0.0

            def get_payment_type(employee):
                return employee.payment_type if employee and hasattr(employee, 'payment_type') else False

            template_map = {
                (line.name or '').strip().upper(): line
                for line in template.line_ids
            }

            def get_tpl_line(name):
                return template_map.get((name or '').strip().upper())

            asesor_tpl = get_tpl_line('ASESOR')
            gerente_tpl = get_tpl_line('GERENTE')
            dvn_tpl = get_tpl_line('DVN')
            cco_tpl = get_tpl_line('CCO')
            kam_tpl = get_tpl_line('KAM')
            pub_tpl = next(
                (l for l in template.line_ids if 'PUBLICIDAD' in ((l.name or '').strip().upper())),
                False
            )
            pub_pct = pub_tpl.commission_percent if pub_tpl else 0.0

            equipo_tpl = next(
                (
                    l for l in template.line_ids
                    if 'EQUIPO INTERNO' in ((l.name or '').strip().upper())
                ),
                False
            )

            equipo_pct = equipo_tpl.commission_percent if equipo_tpl else 0.0

            asesor_pct = asesor_tpl.commission_percent if asesor_tpl else 0.0
            gerente_pct = gerente_tpl.commission_percent if gerente_tpl else 0.0
            dvn_pct = dvn_tpl.commission_percent if dvn_tpl else 0.0
            kam_pct = kam_tpl.commission_percent if kam_tpl else 0.0

            cco_commission_pct = cco_tpl.commission_percent if cco_tpl else 0.0
            cco_flow_pct = cco_tpl.flow_percent if cco_tpl else 0.0
            pub_pct = pub_tpl.commission_percent if pub_tpl else 0.0

            asesor_employee = vendor_employee.asesor if hasattr(vendor_employee, 'asesor') else False
            gerente_employee = vendor_employee.gerente if hasattr(vendor_employee, 'gerente') else False
            dvn_employee = vendor_employee.dvn if hasattr(vendor_employee, 'dvn') else False
            cco_employee = vendor_employee.cco if hasattr(vendor_employee, 'cco') else False
            kam_employee = vendor_employee.kam if hasattr(vendor_employee, 'kam') else False

            line_vals = []

            # ASESOR
            if asesor_employee and asesor_pct:
                amt = calc_amount(asesor_pct)
                line_vals.append({
                    'commission_id': record.id,
                    'employee_id': asesor_employee.id,
                    'position': 'ASESOR',
                    'lot': lot_name,
                    'amount_to_commission': amount_base,
                    'commission': asesor_pct,
                    'amount': amt,
                    'discount': 0.0,
                    'to_pay': amt,
                    'payment_type': get_payment_type(asesor_employee),
                })

            # KAM
            if kam_employee and kam_pct:
                amt = calc_amount(kam_pct)
                line_vals.append({
                    'commission_id': record.id,
                    'employee_id': kam_employee.id,
                    'position': 'KAM',
                    'lot': lot_name,
                    'amount_to_commission': amount_base,
                    'commission': kam_pct,
                    'amount': amt,
                    'discount': 0.0,
                    'to_pay': amt,
                    'payment_type': get_payment_type(kam_employee),
                })

            # GERENTE
            if gerente_employee and gerente_pct:
                amt = calc_amount(gerente_pct)
                line_vals.append({
                    'commission_id': record.id,
                    'employee_id': gerente_employee.id,
                    'position': 'GERENTE',
                    'lot': lot_name,
                    'amount_to_commission': amount_base,
                    'commission': gerente_pct,
                    'amount': amt,
                    'discount': 0.0,
                    'to_pay': amt,
                    'payment_type': get_payment_type(gerente_employee),
                })

            # DVN
            if dvn_employee and dvn_pct:
                amt = calc_amount(dvn_pct)
                line_vals.append({
                    'commission_id': record.id,
                    'employee_id': dvn_employee.id,
                    'position': 'DVN',
                    'lot': lot_name,
                    'amount_to_commission': amount_base,
                    'commission': dvn_pct,
                    'amount': amt,
                    'discount': 0.0,
                    'to_pay': amt,
                    'payment_type': get_payment_type(dvn_employee),
                })

            # CCO (commission_percent)
            if cco_employee and cco_commission_pct:
                amt = calc_amount(cco_commission_pct)
                line_vals.append({
                    'commission_id': record.id,
                    'employee_id': cco_employee.id,
                    'position': 'CCO',
                    'lot': lot_name,
                    'amount_to_commission': amount_base,
                    'commission': cco_commission_pct,
                    'amount': amt,
                    'discount': 0.0,
                    'to_pay': amt,
                    'payment_type': get_payment_type(cco_employee),
                })

            # CCO (flow_percent) -> second line
            if cco_employee and cco_flow_pct:
                amt = calc_amount(cco_flow_pct)
                line_vals.append({
                    'commission_id': record.id,
                    'employee_id': cco_employee.id,
                    'position': 'CCO',
                    'lot': lot_name,
                    'amount_to_commission': amount_base,
                    'commission': cco_flow_pct,
                    'amount': amt,
                    'discount': 0.0,
                    'to_pay': amt,
                    'payment_type': get_payment_type(cco_employee),
                })

            # PUBLICIDAD
            if pub_pct:
                amt = calc_amount(pub_pct)
                line_vals.append({
                    'commission_id': record.id,
                    'employee_id': False,
                    'position': 'PUBLICIDAD',
                    'lot': lot_name,
                    'amount_to_commission': amount_base,
                    'commission': pub_pct,
                    'amount': amt,
                    'discount': 0.0,
                    'to_pay': amt,
                })

            if equipo_pct:
                amt = calc_amount(equipo_pct)
                line_vals.append({
                    'commission_id': record.id,
                    'employee_id': False,
                    'position': 'EQUIPO INTERNO',
                    'lot': lot_name,
                    'amount_to_commission': amount_base,
                    'commission': equipo_pct,
                    'amount': amt,
                    'discount': 0.0,
                    'to_pay': amt,
                })

            if line_vals:
                CommissionLine.create(line_vals)

        return True


class CcimaCommissionsLines(models.Model):
    _name = 'ccima.commissions.lines'
    _description = 'Commission Lines'

    name = fields.Char(
        string='Description',
        required=False,
    )

    commission_id = fields.Many2one(
        comodel_name='ccima.commissions',
        string='Commission',
        ondelete='cascade',
    )

    employee_id = fields.Many2one(
        comodel_name='hr.employee',
        string='Commission Agent',
    )
    position = fields.Char(string='Position')
    lot = fields.Char(string='Lot')
    amount_to_commission = fields.Float(string='Amount to Commission')
    commission = fields.Float(string='Commission (%)')
    amount = fields.Float(string='Amount')
    payment_type = fields.Char(string='Payment Type')
    discount = fields.Float(string='Discount')
    to_pay = fields.Float(
        string='To Pay',
    )

    def _recompute_amounts(self):
        for line in self:
            base = line.amount_to_commission or 0.0
            pct = line.commission or 0.0
            line.amount = base * pct / 100.0
            disc = line.discount or 0.0
            line.to_pay = line.amount - disc

    @api.onchange('employee_id')
    def _onchange_employee_id(self):
        for line in self:
            if line.employee_id and line.employee_id.job_id:
                line.position = line.employee_id.job_id.name
            else:
                line.position = False

            commission = line.commission_id
            if commission:
                lead = commission.lead_id
                if lead and getattr(lead, 'property_id', False):
                    line.lot = lead.property_id.name or False
                else:
                    line.lot = False

                line.amount_to_commission = commission.finance_amount_total or 0.0
            else:
                line.lot = False
                line.amount_to_commission = 0.0

        self._recompute_amounts()

    @api.onchange('commission', 'amount_to_commission', 'discount')
    def _onchange_commission_data(self):
        self._recompute_amounts()

    @api.onchange('discount')
    def _onchange_discount(self):
        for line in self:
            if line.discount is False:
                continue

            line.to_pay = line.amount - line.discount





