from odoo import models, fields, api


class CcimaCommissionSource(models.Model):
    _name = 'ccima.commission.source'
    _description = 'Commission by Source'

    name = fields.Char(string='Name', required=True)
    origin_ids = fields.Many2many(
        'utm.source',
        'ccima_commission_source_utm_rel',
        'commission_source_id',
        'utm_source_id',
        string='Origins',
        required=True,
    )
    line_ids = fields.One2many(
        'ccima.commission.source.line',
        'commission_source_id',
        string='Commission Lines',
    )

    total_commission_percent = fields.Float(
        string='Total Commission %',
        default=0.0,
    )

    position = fields.Selection(
        selection=[
            ("asesor", "Asesor"),
            ("kam", "KAM"),
            ("gerente", "Gerente"),
            ("dvn", "DVN"),
            ("cco", "CCO"),
        ],
        string="Posición"
    )

    def _recalculate_commission_totals(self):
        for rec in self:
            commission_total = sum(
                rec.line_ids.mapped('commission_percent')
            )
            flow_total = sum(
                rec.line_ids.mapped('flow_percent')
            )

            rec.sudo().with_context(skip_recalc=True).write({
                'total_commission_percent': commission_total + flow_total,
            })

    @api.model
    def create(self, vals):
        rec = super().create(vals)
        rec._recalculate_commission_totals()
        return rec

    def write(self, vals):
        if self.env.context.get('skip_recalc'):
            return super().write(vals)
        res = super().write(vals)
        self._recalculate_commission_totals()
        return res


class CcimaCommissionSourceLine(models.Model):
    _name = 'ccima.commission.source.line'
    _description = 'Commission by Source Line'

    commission_source_id = fields.Many2one(
        'ccima.commission.source',
        string='Commission Source',
        ondelete='cascade',
        required=True,
    )

    name = fields.Char(string='Name', required=True)

    commission_percent = fields.Float(
        string='Commission %',
        digits=(16, 2),
        help='Percent of commission for this line.',
    )

    flow_percent = fields.Float(
        string='Flow %',
        digits=(16, 2),
        help='Percent of cash flow for this line.',
    )

    total_percent = fields.Float(
        string='Total %',
        compute='_compute_total_percent',
        store=True,
        digits=(16, 2),
    )

    @api.depends('commission_percent', 'flow_percent')
    def _compute_total_percent(self):
        for line in self:
            line.total_percent = (line.commission_percent or 0.0) + (line.flow_percent or 0.0)







