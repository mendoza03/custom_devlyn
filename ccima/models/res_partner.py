# -*- coding: utf-8 -*-

from odoo import fields, models, api  # type: ignore

import logging

_logger = logging.getLogger(__name__)


class ResPartner(models.Model):
    _inherit = 'res.partner'
    _sql_constraints = [
        (
            'uniq_res_partner_name',
            'unique(name)',
            'There is already another contact with the same name',
        ),
    ]

    vat = fields.Char(string='RFC')
    colony = fields.Char(string='Colony')
    colony_number = fields.Char(string='Colony number')
    company_type_business = fields.Char(string='Type of business')
    company_activity = fields.Char(string='Activity')
    company_articles_incorporation = fields.Binary(string='Articles of Incorporation')
    company_registry_number = fields.Char(string='Registry Number')
    company_date_registration = fields.Date(string='Date of registration')
    company_notary_number = fields.Char(string='Notary No.')
    company_notary_name = fields.Char(string='Name of the Notary')
    company_city_registration = fields.Char(string='City of Registration')
    company_purpose = fields.Char(string='Corporate Purpose')
    company_commercial_registry_number = fields.Char(
        string='Commercial Registry Number'
    )
    company_legal_representatives = fields.Char(
        string="Legal Representative's Information"
    )
    individual_nationality = fields.Many2one(
        comodel_name='res.country', string='Nationality'
    )
    individual_dwelling_type = fields.Selection(
        [
            ('own', 'Own'),
            ('rented', 'Rented'),
            ('borrowed', 'Borrowed'),
        ],
        string='Dwelling Type',
    )
    individual_level_education = fields.Selection(
        [
            ('primary', 'Primary school'),
            ('secondary', 'Secondary school'),
            ('high_school', 'High school'),
            ('tsu', 'TSU'),
            ('bachelors_degree', 'Bachelors degree'),
            ('engineering', 'Bachelors degree in Engineering'),
            ('masters_degree', 'Masters degree'),
            ('phd', 'PhD'),
        ]
    )
    individual_marital_status = fields.Selection(
        [
            ('single', 'Single'),
            ('married', 'Married'),
            ('divorced', 'Divorced'),
            ('widower', 'Widower'),
        ],
        string='Marital Status',
    )

    individual_birth_place_nationality = fields.Many2one(
        'res.country', string='Nationality'
    )
    individual_birth_place_state_id = fields.Many2one(
        'res.country.state',
        string='state',
        domain="[('country_id','=', individual_birth_place_nationality)]",
    )
    individual_birth_place_city_id = fields.Many2one(
        'res.custom.city',
        string='city',
        domain="[('state_id','=', individual_birth_place_state_id)]",
    )

    individual_apply_goods = fields.Boolean(string='Aplica Bienes')
    individual_spouses_name = fields.Char(string="Spouse's Name")
    individual_date_birth = fields.Date(string='Date of birth')
    individual_curp = fields.Char(string='CURP')
    individual_company_work = fields.Char(string='Company where they work')
    individual_company_job_position = fields.Char(string='Job position')
    individual_company_seniority = fields.Integer(string='Seniority')
    individual_company_seniority_tx = fields.Char(string='Seniority')
    individual_company_mobile = fields.Char(string='Company mobile')
    has_saleman_assigner_group = fields.Boolean(
        string='The user has the permission to assign the seller?',
        compute='_check_saleman_assigner_group',
    )

    def _check_saleman_assigner_group(self) -> None:
        for record in self:
            record.has_saleman_assigner_group = self.env.user.has_group(
                'ccima.group_access_saleman_assigner'
            )

    @api.onchange('individual_birth_place_nationality')
    def _onchange_individual_birth_place_nationality(self):
        for rec in self:
            rec.individual_birth_place_state_id = False
            rec.individual_birth_place_city_id = False

    @api.onchange('individual_birth_place_state_id')
    def _onchange_individual_birth_place_state_id(self):
        for rec in self:
            rec.individual_birth_place_city_id = False

    @api.model
    def web_search_read(
        self, domain, specification, offset=0, limit=None, order=None, count_limit=None
    ):
        domain = domain or []
        if self.env.user.has_group('ccima.group_access_show_only_costumer_assigned'):
            domain.append(('user_id', '=', self.env.user.id))
        return super(ResPartner, self).web_search_read(
            domain=domain,
            specification=specification,
            offset=offset,
            limit=limit,
            order=order,
            count_limit=count_limit,
        )
