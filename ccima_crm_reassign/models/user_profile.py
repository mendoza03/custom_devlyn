from odoo import models, fields


class UserProfile(models.Model):
    _name = 'biosman.user.profile'
    _description = 'User Profile'

    name = fields.Char(string='Name', required=True)

    profile_group_id = fields.Many2one(
        comodel_name='res.groups',
        string='Profile Group',
    )

    user_ids = fields.Many2many(
        comodel_name='res.users',
        relation='biosman_user_profile_res_users_rel',
        column1='profile_id',
        column2='user_id',
        string='Users',
    )

    group_ids = fields.Many2many(
        comodel_name='res.groups',
        relation='biosman_user_profile_res_groups_rel',
        column1='profile_id',
        column2='group_id',
        string='Groups',
    )

    rules_ids = fields.Many2many(
        comodel_name='ir.rule',
        relation='biosman_user_profile_ir_rule_rel',
        column1='profile_id',
        column2='rule_id',
        string='Rules',
    )

    def action_apply_profile(self):
        """
        - A cada usuario en user_ids le agrega todos los grupos de group_ids.
        - A profile_group_id le agrega todas las reglas de rules_ids.
        """
        for profile in self:
            # agregar grupos a todos los usuarios
            if profile.group_ids:
                group_commands = [(4, g.id) for g in profile.group_ids]
                for user in profile.user_ids:
                    user.write({'groups_id': group_commands})

            # agregar reglas al grupo de perfil
            if profile.profile_group_id and profile.rules_ids:
                rule_commands = [(4, r.id) for r in profile.rules_ids]
                profile.profile_group_id.write({'rule_groups': rule_commands})
