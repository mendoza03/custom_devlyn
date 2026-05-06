from odoo import models, fields, api


class ModalityFinanceLines(models.Model):
    _name = 'modality.finance.line'
    _description = 'Lines from modality finance'


    name = fields.Char(string="Finance")
    order_id = fields.Many2one('sale.order',string="Order Id")
    # discount = fields.Float(string="% Discount")
    promotion_id = fields.Many2one('promotions.property', string="Promotion Id")
    domain_promotion_ids = fields.Many2many('promotions.property', string="Domain Promotion Ids")
    finance_months = fields.Integer(string="Finance months")
    pu_discount = fields.Float(string="P.U. Discount")
    discount_total = fields.Float(string="Discount")
    amount_total = fields.Float(string="Amount Total")
    gradual_initial_investment = fields.Float(
        string="Inversion Inicial Gradual",
        compute="_compute_gradual_initial_investment",
        store=True,
    )
    hitch_porcent = fields.Float(string="% Hitch")
    hitch = fields.Float(string="Amount Hitch")
    hitch_no_discount = fields.Float(string="Amount Hitch no discount")
    interest_id = fields.Many2one('installment.template', string="Finance Id")
    amount_finance = fields.Float(string="Amount Finance")
    financial_line_1 = fields.Float(string="1 to 48 months")
    financial_line_2 = fields.Float(string="49 to 120 months")
    financial_line_3 = fields.Float(string="121 to 180 months")
    financial_line_4 = fields.Float(string="181 to 240 months")

    @api.depends('amount_total', 'discount_total', 'hitch_porcent', 'hitch')
    def _compute_gradual_initial_investment(self):
        for record in self:
            discounted_total = (record.amount_total or 0.0) - (record.discount_total or 0.0)
            total_hitch = discounted_total * (record.hitch_porcent or 0.0)
            hitch_discount = total_hitch - (record.hitch or 0.0)
            record.gradual_initial_investment = discounted_total - hitch_discount

    @api.onchange('promotion_id', 'amount_total', 'discount_total', 'order_id.hitch_porcent')
    def onchange_discount(self):
        if self.promotion_id:
            discount_percent = (self.amount_total or 0.0) * (self.promotion_id.porcent or 0.0)
            discount_bono = self.promotion_id.porcent_bono or 0.0

            self.discount_total = discount_percent

            amount_after_discount = (self.amount_total or 0.0) - (self.discount_total or 0.0)

            hitch_from_percent = amount_after_discount * (self.order_id.hitch_porcent or 0.0)

            discount_hitch = hitch_from_percent * (self.promotion_id.porcent_financial or 0.0)

            self.hitch = hitch_from_percent - discount_hitch - discount_bono

            self.hitch_no_discount = hitch_from_percent

            self.amount_finance = amount_after_discount - hitch_from_percent

            print("FINANCE CALC promotion_id=", self.promotion_id.id)
            print("FINANCE CALC amount_total=", self.amount_total)
            print("FINANCE CALC discount_percent=", discount_percent)
            print("FINANCE CALC total_discount=", self.discount_total)
            print("FINANCE CALC amount_after_discount=", amount_after_discount)
            print("FINANCE CALC hitch_porcent=", self.order_id.hitch_porcent)
            print("FINANCE CALC hitch_from_percent=", hitch_from_percent)
            print("FINANCE CALC porcent_financial=", self.promotion_id.porcent_financial)
            print("FINANCE CALC discount_hitch=", discount_hitch)
            print("FINANCE CALC discount_bono=", discount_bono)
            print("FINANCE CALC amount_finance_formula=", amount_after_discount, "-", hitch_from_percent)
            print("FINANCE CALC final_hitch=", self.hitch)
            print("FINANCE CALC amount_finance=", self.amount_finance)

            values = self.order_id._get_paymemt_lines(
                self.interest_id.payment_term_ids,
                self.amount_finance
            )

            print("FINANCE CALC payment_values=", values)

            difer_hitch_id = self._origin.order_id.hitch_ids.filtered(
                lambda x: x.finance_id.id == self._origin.id
            )

            if difer_hitch_id:
                difer_hitch_id.write({
                    'amount': self.hitch / difer_hitch_id.months
                })

            self.write(values)