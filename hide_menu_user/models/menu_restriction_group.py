# -*- coding: utf-8 -*-
#############################################################################
#
#    Cybrosys Technologies Pvt. Ltd.
#
#    Copyright (C) 2025-TODAY Cybrosys Technologies(<https://www.cybrosys.com>)
#    Author: Cybrosys Techno Solutions(<https://www.cybrosys.com>)
#
#    You can modify it under the terms of the GNU LESSER
#    GENERAL PUBLIC LICENSE (LGPL v3), Version 3.
#
#    This program is distributed in the hope that it will be useful,
#    but WITHOUT ANY WARRANTY; without even the implied warranty of
#    MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#    GNU LESSER GENERAL PUBLIC LICENSE (LGPL v3) for more details.
#
#    You should have received a copy of the GNU LESSER GENERAL PUBLIC LICENSE
#    (LGPL v3) along with this program.
#    If not, see <http://www.gnu.org/licenses/>.
#
#############################################################################

from odoo import api, fields, models


class MenuRestrictionGroup(models.Model):
    """
    Model to handle menu restrictions for groups of users.
    """
    _name = 'menu.restriction.group'
    _description = 'Menu Restriction Group'
    _order = 'name'

    name = fields.Char(
        string='Group Name',
        required=True,
        help='Name of the restriction group'
    )
    
    user_ids = fields.Many2many(
        'res.users',
        'menu_restriction_group_users_rel',
        'group_id',
        'user_id',
        string='Users',
        help='Users that belong to this restriction group'
    )
    
    hide_menu_ids = fields.Many2many(
        'ir.ui.menu',
        'menu_restriction_group_menus_rel',
        'group_id',
        'menu_id',
        string='Hidden Menus',
        help='Menus that will be hidden for users in this group'
    )
    
    active = fields.Boolean(
        string='Active',
        default=True,
        help='If unchecked, restrictions will not apply'
    )
    
    user_count = fields.Integer(
        string='Number of Users',
        compute='_compute_user_count',
        store=True
    )
    
    menu_count = fields.Integer(
        string='Number of Hidden Menus',
        compute='_compute_menu_count',
        store=True
    )

    @api.depends('user_ids')
    def _compute_user_count(self):
        """Compute the number of users in the group"""
        for record in self:
            record.user_count = len(record.user_ids)

    @api.depends('hide_menu_ids')
    def _compute_menu_count(self):
        """Compute the number of hidden menus"""
        for record in self:
            record.menu_count = len(record.hide_menu_ids)

    def write(self, vals):
        """
        Override write to update menu restrictions when users or menus change
        """
        # Store old values
        old_values = {}
        for record in self:
            old_values[record.id] = {
                'user_ids': record.user_ids,
                'hide_menu_ids': record.hide_menu_ids,
                'active': record.active
            }
        
        res = super().write(vals)
        
        # Update menu restrictions
        for record in self:
            old_data = old_values.get(record.id, {})
            old_users = old_data.get('user_ids', self.env['res.users'])
            old_menus = old_data.get('hide_menu_ids', self.env['ir.ui.menu'])
            old_active = old_data.get('active', True)
            
            # If group was deactivated, remove all restrictions
            if old_active and not record.active:
                for menu in record.hide_menu_ids:
                    for user in record.user_ids:
                        menu.sudo().write({'restrict_user_ids': [(3, user.id)]})
                continue
            
            # If group was activated, add all restrictions
            if not old_active and record.active:
                for menu in record.hide_menu_ids:
                    for user in record.user_ids:
                        menu.sudo().write({'restrict_user_ids': [(4, user.id)]})
                continue
            
            # If active, update restrictions based on changes
            if record.active:
                # Handle new menus
                new_menus = record.hide_menu_ids - old_menus
                for menu in new_menus:
                    for user in record.user_ids:
                        menu.sudo().write({'restrict_user_ids': [(4, user.id)]})
                
                # Handle removed menus
                removed_menus = old_menus - record.hide_menu_ids
                for menu in removed_menus:
                    for user in record.user_ids:
                        # Only remove if user doesn't have individual restriction
                        # and user is not in other active groups with this menu
                        if menu not in user.hide_menu_ids:
                            other_groups = self.search([
                                ('id', '!=', record.id),
                                ('active', '=', True),
                                ('user_ids', 'in', user.id),
                                ('hide_menu_ids', 'in', menu.id)
                            ])
                            if not other_groups:
                                menu.sudo().write({'restrict_user_ids': [(3, user.id)]})
                
                # Handle new users
                new_users = record.user_ids - old_users
                for user in new_users:
                    for menu in record.hide_menu_ids:
                        menu.sudo().write({'restrict_user_ids': [(4, user.id)]})
                
                # Handle removed users
                removed_users = old_users - record.user_ids
                for user in removed_users:
                    for menu in record.hide_menu_ids:
                        # Only remove if user doesn't have individual restriction
                        # and user is not in other active groups with this menu
                        if menu not in user.hide_menu_ids:
                            other_groups = self.search([
                                ('id', '!=', record.id),
                                ('active', '=', True),
                                ('user_ids', 'in', user.id),
                                ('hide_menu_ids', 'in', menu.id)
                            ])
                            if not other_groups:
                                menu.sudo().write({'restrict_user_ids': [(3, user.id)]})
        
        return res

    @api.model_create_multi
    def create(self, vals_list):
        """
        Override create to set up initial menu restrictions
        """
        records = super().create(vals_list)
        
        for record in records:
            if record.active:
                # Add restrictions for all users and menus in the new group
                for menu in record.hide_menu_ids:
                    for user in record.user_ids:
                        menu.sudo().write({'restrict_user_ids': [(4, user.id)]})
        
        return records

    def unlink(self):
        """
        Override unlink to clean up menu restrictions when group is deleted
        """
        for record in self:
            # Remove all menu restrictions for users in this group
            for menu in record.hide_menu_ids:
                for user in record.user_ids:
                    # Only remove if user doesn't have individual restriction
                    # and user is not in other active groups with this menu
                    if menu not in user.hide_menu_ids:
                        other_groups = self.search([
                            ('id', '!=', record.id),
                            ('active', '=', True),
                            ('user_ids', 'in', user.id),
                            ('hide_menu_ids', 'in', menu.id)
                        ])
                        if not other_groups:
                            menu.sudo().write({'restrict_user_ids': [(3, user.id)]})
        
        return super().unlink()

    def action_view_users(self):
        """Action to view users in this group"""
        self.ensure_one()
        return {
            'name': 'Users in ' + self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'res.users',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.user_ids.ids)],
            'context': {'create': False}
        }

    def action_view_menus(self):
        """Action to view hidden menus in this group"""
        self.ensure_one()
        return {
            'name': 'Hidden Menus in ' + self.name,
            'type': 'ir.actions.act_window',
            'res_model': 'ir.ui.menu',
            'view_mode': 'tree,form',
            'domain': [('id', 'in', self.hide_menu_ids.ids)],
            'context': {'create': False}
        }
