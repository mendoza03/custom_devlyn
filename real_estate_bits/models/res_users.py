from odoo import fields, models, api
from dateutil.relativedelta import relativedelta
from datetime import datetime, timedelta
import calendar
from random import randrange
from numerize import numerize
from .chart import get_line_chart, get_bar_chart, prepare_chart_data
from odoo.http import request

DATE_FORMATE = "%Y-%m-%d 00:00:00"


def get_last_months(start_date, months):
    for i in range(months):
        yield start_date.year, start_date.month
        start_date += relativedelta(months=-1)


def get_month_data(obj, domain=None):
    date_obj = datetime.today().replace(day=1)
    month = date_obj.month
    first_month = date_obj + relativedelta(months=-month + 1)
    data = {}

    for i in range(6):
        temp_domain = [('create_date', '>', (first_month + relativedelta(months=i)).strftime(DATE_FORMATE)),
                       ('create_date', '<', (first_month + relativedelta(months=i + 1)).strftime(DATE_FORMATE))]
        for rec in domain:
            temp_domain.append(rec)
        data.update({i: obj.search(temp_domain)})

    return data


def area_options(max_val=1200, min_val=0, step=200):
    return {
        'responsive': True,
        'maintainAspectRatio': True,
        'plugins': {
            'filler': {
                'propagate': False
            }
        },
        'scales': {
            'xAxes': [{
                'display': True,
                'ticks': {
                    'display': True,
                    'padding': 10,
                    'fontColor': "#6C7383"
                },
                'gridLines': {
                    'display': False,
                    'drawBorder': False,
                    'color': 'transparent',
                    'zeroLineColor': '#eeeeee'
                }
            }],
            'yAxes': [{
                'display': True,
                'ticks': {
                    'display': True,
                    'autoSkip': False,
                    'maxRotation': 0,
                    'stepSize': step,
                    'min': min_val,
                    'max': max_val,
                    'padding': 18,
                    'fontColor': "#6C7383"
                },
                'gridLines': {
                    'display': True,
                    'color': "#f2f2f2",
                    'drawBorder': False
                }
            }]
        },
        'legend': {
            'display': True
        },
        'tooltips': {
            'enabled': True
        },
        'elements': {
            'line': {
                'tension': .35
            },
            'point': {
                'radius': 0
            }
        }
    }


def doughnut_pie_options():
    return {
        'responsive': True,
        'animation': {
            'animateScale': True,
            'animateRotate': True
        }
    }


def get_colour():
    return 'rgba(' + str(randrange(255)) + ', ' + str(randrange(255)) + ', ' + str(randrange(255)) + ', 0.5)',


def doughnut_pie_data(data, labels):
    lst_color = [get_colour() for i in range(len(labels))]
    return {
        'datasets': [{
            'data': data,
            'backgroundColor': lst_color,
            'borderColor': lst_color,
        }],
        'labels': labels
    }


class Users(models.Model):
    _inherit = "res.users"

    @api.model
    def get_real_estate_dashboard_chart_data(self):
        project_ids = self.env['project.worksite'].search([('parent_id', '=', False), ('is_enabled', '=', True)])

        # SFT Chart
        # property_ids = project_ids.mapped('child_ids').mapped('property_ids')
        all_property = project_ids.filtered(lambda x: x.is_demo_worksite)
        property_ids = []
        if all_property:
            property_ids = self.env['product.template'].search([('is_property', '=', True)])
        elif project_ids:
            property_ids = self.env['product.template'].search([('is_property', '=', True),('project_worksite_id.parent_id','in',project_ids.ids)])
        else:
            property_ids = self.env['product.template'].search([('is_property', '=', True),('project_worksite_id','in',project_ids.ids + [False])])
        lst_months = [calendar.month_abbr[num[1]] for num in get_last_months(datetime.today(), 6)]
        lst_months.reverse()
        date_obj = fields.Date.today().replace(day=1)

        # Revenue chart
        booking_ids = self.env['property.reservation'].search([('property_id', 'in', property_ids.ids)])
        contract_ids = self.env['property.contract'].search([('reservation_id', 'in', booking_ids.ids)])

        loan_line_ids = contract_ids.mapped('loan_line_ids')

        total_sft = {}
        sold_sft = {}
        available_sft = {}

        total_revenue = {}
        collected_revenue = {}

        total_len = len(lst_months)

        for i in range(total_len):
            date_a = date_obj + relativedelta(months=-(total_len - i - 1))
            date_b = date_obj + relativedelta(months=-(total_len - i - 2))

            count_property_ids = property_ids.filtered(lambda x: x.property_date and date_a < x.property_date < date_b)
            #count_property_ids = property_ids.filtered(lambda x: date_a < x.property_date < date_b)
            count_free_property_ids = count_property_ids.filtered(lambda x: x.state in ['free', 'reserved'])
            count_sold_property_ids = count_property_ids.filtered(lambda x: x.state in ['sold', 'on_lease'])

            total_sft.update({lst_months[i]: sum(count_property_ids.mapped('property_area'))})
            sold_sft.update({lst_months[i]: sum(count_sold_property_ids.mapped('property_area'))})
            available_sft.update({lst_months[i]: sum(count_free_property_ids.mapped('property_area'))})

            temp_line_ids = loan_line_ids.filtered(lambda x: x.date and date_a < x.date < date_b)
            # temp_line_ids = loan_line_ids.filtered(lambda x: date_a < x.date < date_b)
            total_revenue.update({lst_months[i]: sum(temp_line_ids.mapped('amount'))})
            collected_revenue.update({lst_months[i]: sum(temp_line_ids.filtered(
                lambda x: x.invoice_id and x.payment_state in ['paid', 'partial']).mapped('amount'))})

        total_sft_val = list(total_sft.values())
        sold_sft_val = list(sold_sft.values())
        available_sft_val = list(available_sft.values())
        max_val = max([max(total_sft_val), max(sold_sft_val), max(available_sft_val)])

        sft_chart = {
            'labels': lst_months,
            'datasets': [
                {
                    'data': total_sft_val,
                    'borderColor': ['#0081B4'],
                    'borderWidth': 2,
                    'fill': False,
                    'label': "Total SFT"
                },
                {
                    'data': sold_sft_val,
                    'borderColor': ['#4747A1'],
                    'borderWidth': 2,
                    'fill': False,
                    'label': "Sold SFT"
                },
                {
                    'data': available_sft_val,
                    'borderColor': ['#F09397'],
                    'borderWidth': 2,
                    'fill': False,
                    'label': "Available SFT"
                }
            ]

        }

        # Revenue chart
        total_revenue_val = list(total_revenue.values())
        collected_revenue_val = list(collected_revenue.values())

        # Property Chart
        property_data = [
            len(property_ids.filtered(lambda x: x.project_type == 'tower')),
            len(property_ids.filtered(lambda x: x.project_type == 'villa')),
            len(property_ids.filtered(lambda x: x.project_type == 'commercial')),
            len(property_ids.filtered(lambda x: x.project_type == 'plots')),
            len(property_ids.filtered(lambda x: x.project_type == 'warehouse')),
            len(property_ids.filtered(lambda x: x.project_type == 'shop'))
        ]

        labels = [
            'Open Plots',
            'Villa',
            'Commercial (Mall)',
            'Tower',
            'Warehouse',
            'Shop'
        ]

        return {
            'sft_chart': {
                'type': 'line',
                'data': sft_chart,
                'options': area_options(max_val=max_val, step=max_val / 5)
            },
            'renting_revenue_chart_options': {
                'max': max(total_revenue_val),
                'min': 0
            },
            'renting_revenue_chart': {
                'labels': lst_months,
                'datasets': [
                    {
                        'label': 'Total',
                        'data': total_revenue_val,
                        'backgroundColor': '#98BDFF'
                    },
                    {
                        'label': 'Collected',
                        'data': collected_revenue_val,
                        'backgroundColor': '#4B49AC'
                    }
                ]
            },

            'property_type_chart': {
                'type': 'doughnut',
                'data': doughnut_pie_data(property_data, labels),
                'options': doughnut_pie_options(),
            }

        }

    @api.model
    def get_real_estate_dashboard_data(self):
        list_project_ids = self.env['project.worksite'].search([('parent_id', '=', False)])
        project_ids = list_project_ids.filtered(lambda x: x.is_enabled)
        all_property = project_ids.filtered(lambda x: x.is_demo_worksite)
        count_property_ids = []
        if all_property:
            count_property_ids = self.env['product.template'].search([('is_property', '=', True)])
        else:
            if project_ids:
                count_property_ids = self.env['product.template'].search([('is_property', '=', True),('project_worksite_id.parent_id','in',project_ids.ids)])
            else:
                count_property_ids = self.env['product.template'].search([('is_property', '=', True),('project_worksite_id','in',project_ids.ids + [False])])

        # count_property_ids = project_ids.mapped('child_ids').mapped('property_ids')
        count_free_property_ids = count_property_ids.filtered(lambda x: x.state == 'free')
        count_booked_property_ids = count_property_ids.filtered(lambda x: x.state == 'reserved')
        count_sold_property_ids = count_property_ids.filtered(lambda x: x.state == 'sold')
        count_rented_property_ids = count_property_ids.filtered(lambda x: x.state == 'on_lease')

        brochure_ids = count_property_ids.attachment_line_ids.filtered(lambda x: x.is_brochure)
        brochure_ids += project_ids.attachment_line_ids.filtered(lambda x: x.is_brochure)

        booking_ids = self.env['property.reservation'].search([('property_id', 'in', count_property_ids.ids)])
        contract_ids = self.env['property.contract'].search([('reservation_id', 'in', booking_ids.ids)])

        loan_line_ids = contract_ids.mapped('loan_line_ids')
        total_revenue = sum(loan_line_ids.mapped('amount'))
        collected_revenue = sum(loan_line_ids.filtered(
            lambda x: x.invoice_id and x.payment_state in ['paid', 'partial']).mapped('amount'))

        cids = request.httprequest.cookies.get('cids') and request.httprequest.cookies.get('cids').split(
            '-') or request.env.company.ids
        company_ids = self.env['res.company'].browse([int(i) for i in cids]).mapped('name')
        return {
            'company_name': ", ".join(company_ids),

            'projects': [{'id': rec.id, 'name': rec.name, 'is_enabled': rec.is_enabled} for rec in list_project_ids],

            'cards': [
                {'name': 'Number of Properties', 'value': numerize.numerize(len(count_property_ids)),
                 'id': 'no_of_unit', 'class': 'card-dark-reb'},
                {'name': 'Available Properties', 'value': numerize.numerize(len(count_free_property_ids)),
                 'id': 'avail_unit', 'class': 'card-gray-reb'},
                {'name': 'Booking Properties', 'value': numerize.numerize(len(count_booked_property_ids)),
                 'id': 'book_property', 'class': 'card-bluish-reb'},
                {'name': 'Sold Properties', 'value': numerize.numerize(len(count_sold_property_ids)),
                 'id': 'sold_property', 'class': 'card-slate-reb'},
                {'name': 'Rented Properties', 'value': numerize.numerize(len(count_rented_property_ids)),
                 'id': 'rent_property', 'class': 'card-silk-blue-reb'},
                {'name': 'Total Collected', 'id': 'revenue_collected', 'class': 'card-navy-reb',
                 'value': self.env.company.currency_id.symbol + str(numerize.numerize(total_revenue)),
                 },
            ],

            'brochures': [{'id': rec.id, 'name': rec.name} for rec in brochure_ids],

            'sft_chart_data': [
                {
                    'name': 'Total SFT',
                    'value': numerize.numerize(sum(count_property_ids.mapped('property_area')))
                },
                {
                    'name': 'Available SFT',
                    'value': numerize.numerize(sum(count_free_property_ids.mapped('property_area')))
                },
                {
                    'name': 'Sold SFT',
                    'value': numerize.numerize(sum(count_sold_property_ids.mapped('property_area')))
                },
                {
                    'name': 'Rented SFT',
                    'value': numerize.numerize(sum(count_rented_property_ids.mapped('property_area')))
                },
                {
                    'name': 'Booked SFT',
                    'value': numerize.numerize(sum(count_booked_property_ids.mapped('property_area')))
                },
            ],

            'renting_revenue_data': [
                {
                    'name': 'Total Revenue',
                    'value': self.env.company.currency_id.symbol + str(numerize.numerize(total_revenue))
                },
                {
                    'name': 'Collected Revenue',
                    'value': self.env.company.currency_id.symbol + str(numerize.numerize(collected_revenue))
                },
            ],
        }
