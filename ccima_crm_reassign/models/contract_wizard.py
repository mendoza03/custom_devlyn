from odoo import models, fields, api

class LoanLineUpdateWizardLine(models.TransientModel):
    _name = 'loan.line.update.wizard.line'
    _description = 'Loan Line Update Wizard Line'

    wizard_id = fields.Many2one('loan.line.update.wizard', string='Wizard')
    loan_line_id = fields.Many2one(
        'loan.line',
        string='Loan Line',
        required=True,
        domain="[('contract_id', '=', parent.contract_id)]"  
    )
    amount_capital = fields.Float(string='Amount Capital')
    amount_paid = fields.Float(string='Amount Paid')

    @api.onchange('loan_line_id')
    def _onchange_loan_line_id(self):
        if self.loan_line_id:
            self.amount_capital = self.loan_line_id.amount_capital
            self.amount_paid = self.loan_line_id.amount_paid

class LoanLineUpdateWizard(models.TransientModel):
    _name = 'loan.line.update.wizard'
    _description = 'Wizard to manually update loan lines'

    contract_id = fields.Many2one('property.contract', string='Contract', required=True)
    line_ids = fields.One2many('loan.line.update.wizard.line', 'wizard_id', string='Lines to Update')

    def apply_update(self):
        for line in self.line_ids:
            if line.loan_line_id:
                line.loan_line_id.write({
                    'amount_capital': line.amount_capital,
                    'amount_paid': line.amount_paid,
                })
