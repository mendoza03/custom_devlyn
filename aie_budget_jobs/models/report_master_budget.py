from odoo import models, _
from datetime import date


class MasterBudgetReportHandler(models.AbstractModel):
    _name = 'master.budget.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Master Budget Report Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        budgets = self.env['master.budget'].search([])
        lines = []

        for budget in budgets:
            line_id = report._get_generic_line_id('master.budget', budget.id)
            lines.append({
                'id': line_id,
                'name': budget.name,
                'columns': [{'name': ''}] * len(options['columns']),
                'level': 0,
                'unfoldable': True,
                'unfolded': line_id in options.get('unfolded_lines', []),
                'expand_function': '_report_expand_unfoldable_line_budget_lines',
            })

        return [(0, l) for l in lines]

    def _get_options(self, previous_options=None):
        today = date.today()
        month_start = today.replace(day=1)

        if not previous_options or not previous_options.get('date'):
            previous_options = {
                'date': {
                    'string': today.strftime('%B %Y'),
                    'period_type': 'month',
                    'mode': 'range',
                    'date_from': month_start.strftime('%Y-%m-%d'),
                    'date_to': today.strftime('%Y-%m-%d'),
                    'filter': 'custom'
                },
                'comparison': {'filter': 'no_comparison'}
            }

        return super()._get_options(previous_options=previous_options)

    def _custom_options_initializer(self, report, options, previous_options=None):
        super()._custom_options_initializer(report, options, previous_options=previous_options)

        today = date.today()
        month_start = today.replace(day=1)

        options['comparison'] = {'filter': 'no_comparison'}
        options['date'] = {
            'string': today.strftime('%B %Y'),
            'period_type': 'month',
            'mode': 'range',
            'date_from': month_start.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d'),
            'filter': 'custom'
        }
        options['all_entries'] = False
        options['show_currency'] = False
        options['buttons'] = []
        options['warnings'] = []

    def _get_options_custom(self, report, options, previous_options=None):
        options = super()._get_options_custom(report, options, previous_options)

        today = date.today()
        month_start = today.replace(day=1)

        options['comparison'] = {'filter': 'no_comparison'}
        options['date'] = {
            'string': today.strftime('%B %Y'),
            'period_type': 'month',
            'mode': 'range',
            'date_from': month_start.strftime('%Y-%m-%d'),
            'date_to': today.strftime('%Y-%m-%d'),
            'filter': 'custom'
        }
        options['all_entries'] = False
        options['show_currency'] = False
        options['buttons'] = []
        options['warnings'] = []

        return options

    def _init_options_date(self, options, previous_options=None):
        if not previous_options or not previous_options.get('date') or not previous_options['date'].get('date_from'):
            today = date.today()
            month_start = today.replace(day=1)
            options['date'] = {
                'string': today.strftime('%B %Y'),
                'period_type': 'month',
                'mode': 'range',
                'date_from': month_start.strftime('%Y-%m-%d'),
                'date_to': today.strftime('%Y-%m-%d'),
                'filter': 'custom'
            }
        else:
            options['date'] = previous_options['date']

    def _report_expand_unfoldable_line_budget_lines(self, line_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self.env['account.report'].browse(options['report_id'])
        _, _, budget_id = report._parse_line_id(line_id)[-1]

        root_lines = self.env['master.budget.line'].search([
            ('budget_id', '=', budget_id),
            ('parent_id', '=', False)
        ])

        return {
            'lines': [self._format_line(report, line, parent_id=line_id) for line in root_lines],
            'offset_increment': len(root_lines),
            'has_more': False,
        }

    def _report_expand_unfoldable_line_child_lines(self, line_id, groupby, options, progress, offset, unfold_all_batch_data=None):
        report = self.env['account.report'].browse(options['report_id'])
        _, _, parent_line_id = report._parse_line_id(line_id)[-1]
        parent_line = self.env['master.budget.line'].browse(parent_line_id)

        return {
            'lines': [self._format_line(report, child, parent_id=line_id) for child in parent_line.child_ids],
            'offset_increment': len(parent_line.child_ids),
            'has_more': False,
        }

    def _format_line(self, report, line, parent_id=None):
        level = self._get_line_hierarchy_level(line)

        return {
            'id': report._get_generic_line_id('master.budget.line', line.id, parent_line_id=parent_id),
            'parent_id': parent_id,
            'name': line.complete_name,
            'columns': [
                {'name': line.code or ''},
                {'name': line.name or ''},
                {'name': line.type or ''},
                {'name': line.parent_id.complete_name if line.parent_id else ''},
                {'name': line.project_id.display_name if line.project_id else ''},
                {'name': line.task_id.display_name if line.task_id else ''},
                {'name': line.product_id.display_name if line.product_id else ''},
                {'name': line.product_id.categ_id.name if line.product_id and line.product_id.categ_id else ''},
                {'name': line.ref_product or ''},
                {'name': line.price_unit},
                {'name': line.quantity},
                {'name': line.product_uom.name if line.product_uom else ''},
                {'name': line.price_subtotal},
                {'name': line.price_total},
                {'name': line.amount_residual},
            ],
            'level': level,
            'unfoldable': bool(line.child_ids),
            'unfolded': False,
            'expand_function': '_report_expand_unfoldable_line_child_lines' if line.child_ids else None,
        }

    def _get_line_hierarchy_level(self, line):
        level = 1
        current = line
        while current.parent_id:
            level += 1
            current = current.parent_id
        return level
