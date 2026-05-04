from odoo import models, fields

class JobCostingReportHandler(models.AbstractModel):
    _name = 'job.costing.report.handler'
    _inherit = 'account.report.custom.handler'
    _description = 'Job Costing Report Handler'

    def _dynamic_lines_generator(self, report, options, all_column_groups_expression_totals, warnings=None):
        job_costings = self.env['job.costing'].search([])
        lines = []

        project_map = {}
        for job in job_costings:
            project = job.project_id
            if project not in project_map:
                project_map[project] = []
            project_map[project].append(job)

        for project, job_list in project_map.items():
            project_id = project.id if project else 0
            line_id = report._get_generic_line_id('project.project', project_id)
            lines.append({
                'id': line_id,
                'name': project.display_name if project else 'No Project',
                'columns': [{}] * len(options['columns']),
                'level': 0,
                'unfoldable': True,
                'unfolded': line_id in options.get('unfolded_lines', []),
                'expand_function': '_report_expand_unfoldable_line_project_job_costs',
            })

        return [(0, l) for l in lines]

    def _report_expand_unfoldable_line_project_job_costs(self, line_id, groupby, options, progress, offset,
                                                         unfold_all_batch_data=None):
        report = self.env['account.report'].browse(options['report_id'])
        _, _, project_id = report._parse_line_id(line_id)[-1]
        lines = []

        project = self.env['project.project'].browse(project_id) if project_id else None
        domain = [('project_id', '=', project_id)] if project else [('project_id', '=', False)]
        job_costings = self.env['job.costing'].search(domain)

        total_value = 0.0
        for job in job_costings:
            for line in job.job_cost_line_ids + job.job_labour_line_ids:
                total_value += (line.product_qty or 0.0) * (line.cost_price or 0.0)

        for job in job_costings:
            for line in job.job_cost_line_ids + job.job_labour_line_ids:
                qty = line.product_qty or 0.0
                price = line.cost_price or 0.0
                line_total = qty * price
                percentage = (line_total / total_value * 100.0) if total_value else 0.0

                line_type = 'Cost' if line._name == 'job.cost.line' else 'Labour'

                lines.append({
                    'id': report._get_generic_line_id(line._name, line.id, parent_line_id=line_id),
                    'name': line.product_id.display_name or '—',
                    'parent_id': line_id,
                    'columns': [
                        {'name': line.date or ''},
                        {'name': line_type},
                        {'name': line.job_type_id.name or ''},
                        {'name': line.product_id.display_name or ''},
                        {'name': qty},
                        {'name': line.uom_id.name or ''},
                        {'name': price},
                        {'name': f"{percentage:.2f}%"},
                    ],
                    'level': 1,
                })

        return {
            'lines': lines,
            'offset_increment': len(lines),
            'has_more': False,
        }


