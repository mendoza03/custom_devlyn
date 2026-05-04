from odoo import models, fields, api, _  # type: ignore
from odoo.exceptions import UserError  # type: ignore


class CrmLead(models.Model):
    _inherit = 'crm.lead'

    Recommended_by = fields.Char(string='Recommended_by')
    legal_personality = fields.Many2one('sign.template', string='legal personality')
    has_saleman_assigner_group = fields.Boolean(
        string='The user has the permission to assign the seller?',
        compute='_check_saleman_assigner_group',
    )
    project_worksite_id = fields.Many2one(
        'project.worksite', compute='_compute_property_attachments'
    )
    attachment_line_ids = fields.One2many(
        related='project_worksite_id.attachment_line_ids'
    )

    # * ---------------------------------------------------------
    # *  COMPUTED METHODS
    # * ---------------------------------------------------------
    @api.depends('property_id')
    def _compute_property_attachments(self):
        for record in self:
            record.project_worksite_id = record.property_id.worksite_id

    def _check_saleman_assigner_group(self) -> None:
        for record in self:
            record.has_saleman_assigner_group = self.env.user.has_group(
                'ccima.group_access_saleman_assigner'
            )

    # * ---------------------------------------------------------
    # *  ONCHANGE METHODS
    # * ---------------------------------------------------------
    @api.onchange('user_id')
    def _onchange_saleman_user(self):
        self.partner_id.user_id = self.user_id

    # * ---------------------------------------------------------
    # *  HELPERS
    # * ---------------------------------------------------------
    def _check_stage_restrictions(self, stage_id: models.Model) -> None:
        restrictions = stage_id._stage_restrictions()
        error_message = ''
        for restriction in restrictions:
            if not getattr(self, restriction):
                name_field = _(self.fields_get(restriction)[restriction]['string'])
                error_message += _(
                    'The field %(name_field)s, It is necessary to change to the stage %(stage_name)s\n',
                    name_field=name_field,
                    stage_name=stage_id.name,
                )
        if len(error_message) >= 1:
            raise UserError(error_message)

    @api.model
    def web_search_read(
        self, domain, specification, offset=0, limit=None, order=None, count_limit=None
    ):
        domain = domain or []
        if self.env.user.has_group('ccima.group_access_show_only_costumer_assigned'):
            domain.append(('user_id', '=', self.env.user.id))
        return super(CrmLead, self).web_search_read(
            domain=domain,
            specification=specification,
            offset=offset,
            limit=limit,
            order=order,
            count_limit=count_limit,
        )

    # * ---------------------------------------------------------
    # *  CRUD
    # * ---------------------------------------------------------

    def write(self, vals):
        records = super(CrmLead, self).write(vals)
        for record in self:
            record._check_stage_restrictions(record.stage_id)
        return records
