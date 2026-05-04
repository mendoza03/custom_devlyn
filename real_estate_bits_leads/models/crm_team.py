# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.osv import expression
from ast import literal_eval
from datetime import timedelta

import logging
import random
import threading

_logger = logging.getLogger(__name__)


class CrmTeam(models.Model):
    _inherit = 'crm.team'

    # -------------------------------------------------------------------------
    # NEW FIELDS
    # -------------------------------------------------------------------------

    campaign_ids = fields.One2many(comodel_name='utm.campaign', inverse_name='crm_team_id', string='Campaigns')
    tolerance_minutes = fields.Integer(string='Minutes of tolerance')
    type = fields.Selection(selection=[
        ('average', 'Average'),
        ('percentage', 'Percentage'),
        # ('utilization', 'Utilization'),
    ], string='Type', default='average')
    assign_percentage_ids = fields.One2many(comodel_name='crm.team.member.percentage', inverse_name='crm_team_id', string='Assign Percentage', copy=False, auto_join=True)

    # -------------------------------------------------------------------------
    # CRUD
    # -------------------------------------------------------------------------

    def write(self, vals):
        if ('tolerance_minutes' in vals and vals['tolerance_minutes'] <= 0) or ('tolerance_minutes' not in vals and self.tolerance_minutes <= 0):
            raise UserError(_('The minutes are incorrect'))
        return super().write(vals)

    # -------------------------------------------------------------------------
    # OVERRIDE METHODS
    # -------------------------------------------------------------------------

    @api.model
    def _cron_assign_leads(self, force_quota=False, creation_delta_days=7):
        leads = self.env['crm.lead'].search([('type', '=', 'lead'), ('team_id', '!=', False), ('campaign_id', '!=', False)])
        for lead in leads:
            if ((lead.write_date + timedelta(minutes=lead.team_id.tolerance_minutes)) < fields.Datetime.now()) and lead.write_uid != lead.user_id:
                lead.message_post(body='Reassignment enabled', message_type='comment', subtype_xmlid='mail.mt_comment')
                lead.update({
                    'user_id': False,
                })
        return super()._cron_assign_leads(force_quota, creation_delta_days)

    def _assign_and_convert_leads(self, force_quota=False):
        """ Main processing method to assign leads to sales team members. It also
        converts them into opportunities. This method should be called after
        ``_allocate_leads`` as this method assigns leads already allocated to
        the member's team. Its main purpose is therefore to distribute team
        workload on its members based on their capacity.

        Preparation

        * prepare lead domain for each member. It is done using a logical
            AND with team's domain and member's domain. Member domains further
            restricts team domain;
        * prepare a set of available leads for each member by searching for
            leads matching domain with a sufficient limit to ensure all members
            will receive leads;
        * prepare a weighted population sample. Population are members that
            should received leads. Initial weight is the number of leads to
            assign to that specific member. This is minimum value between
            * remaining this month: assignment_max - number of lead already
            assigned this month;
            * days-based assignment: assignment_max with a ratio based on
            ``work_days`` parameter (see ``CrmTeam.action_assign_leads()``)
            * e.g. Michel Poilvache (max: 30 - currently assigned: 15) limit
            for 2 work days: min(30-15, 30/15) -> 2 leads assigned
            * e.g. Michel Tartopoil (max: 30 - currently assigned: 26) limit
            for 10 work days: min(30-26, 30/3) -> 4 leads assigned

        This method then follows the following heuristic

        * take a weighted random choice in population;
        * find first available (not yet assigned) lead in its lead set;
        * if found:
            * convert it into an opportunity and assign member as salesperson;
            * lessen member's weight so that other members have an higher
            probability of being picked up next;
        * if not found: consider this member is out of assignment process,
            remove it from population so that it is not picked up anymore;

        Assignment is performed one lead at a time for fairness purpose. Indeed
        members may have overlapping domains within a given team. To ensure
        some fairness in process once a member receives a lead, a new choice is
        performed with updated weights. This is not optimal from performance
        point of view but increases probability leads are correctly distributed
        within the team.

        :param float work_days: see ``CrmTeam.action_assign_leads()``;

        :return members_data: dict() with each member assignment result:
        membership: {
            'assigned': set of lead IDs directly assigned to the member;
        }, ...

        """

        members_data, population, weights = dict(), list(), list()
        members = self.crm_team_member_ids.filtered(lambda member: not member.assignment_optout and member._get_assignment_max() > 0)
        if not members:
            return members_data

        # prepare a global lead count based on total leads to assign to salespersons

        lead_limit = sum(
            member._get_assignment_quota(force_quota=False)
            for member in members
        )

        # could probably be optimized
        for member in members:
            lead_domain = expression.AND([
                literal_eval(member.assignment_domain or '[]'),
                ['&', '&', '&', '&', ('user_id', '=', False), ('date_open', '=', False), ('team_id', '=', member.crm_team_id.id), ('campaign_id', '!=', False), ('campaign_id.crm_team_member_ids', 'in', member.ids)]
            ])

            leads = self.env["crm.lead"].search(lead_domain, order='probability DESC, id', limit=lead_limit)

            assignment_max = member._get_assignment_max()
            to_assign = member.with_context(assignment_max=assignment_max)._get_assignment_quota(force_quota=False)
            members_data[member.id] = {
                "team_member": member,
                "max": assignment_max,
                "to_assign": to_assign,
                "leads": leads,
                "assigned": self.env["crm.lead"],
            }
            population.append(member.id)
            weights.append(to_assign)

        leads_done_ids = set()
        counter = 0
        # auto-commit except in testing mode
        auto_commit = not getattr(threading.current_thread(), 'testing', False)
        commit_bundle_size = int(self.env['ir.config_parameter'].sudo().get_param('crm.assignment.commit.bundle', 100))
        while population and any(weights):
            counter += 1
            member_id = random.choices(population, weights=weights, k=1)[0]
            member_index = population.index(member_id)
            member_data = members_data[member_id]

            lead = next((lead for lead in member_data['leads'] if lead.id not in leads_done_ids), False)
            if lead:
                leads_done_ids.add(lead.id)
                members_data[member_id]["assigned"] += lead
                weights[member_index] = weights[member_index] - 1

                lead.with_context(mail_auto_subscribe_no_notify=True, assignment_leads=True).convert_opportunity(
                    lead.partner_id,
                    user_ids=member_data['team_member'].user_id.ids
                )

                if auto_commit and counter % commit_bundle_size == 0:
                    self._cr.commit()
            else:
                weights[member_index] = 0

            if weights[member_index] <= 0:
                population.pop(member_index)
                weights.pop(member_index)

            # failsafe
            if counter > 100000:
                population = list()

        if auto_commit:
            self._cr.commit()
        # log results and return
        result_data = dict(
            (member_info["team_member"], {"assigned": member_info["assigned"]})
            for member_id, member_info in members_data.items()
        )
        _logger.info('Assigned %s leads to %s salesmen', len(leads_done_ids), len(members))
        for member, member_info in result_data.items():
            _logger.info('-> member %s: assigned %d leads (%s)', member.id, len(member_info["assigned"]), member_info["assigned"])
        return result_data

    # -------------------------------------------------------------------------
    # HELPERS
    # -------------------------------------------------------------------------

    @api.model
    def _cron_disable_assignment(self):
        teams = self.search([
            '&', '|', ('use_leads', '=', True), ('use_opportunities', '=', True),
            ('assignment_optout', '=', False)
        ])
        teams._disable_team_members()
        return True

    def _disable_team_members(self):
        for record in self:
            for member in record.crm_team_member_ids.filtered(lambda member: not member.assignment_optout):
                member.write({
                    'assignment_optout': True,
                })