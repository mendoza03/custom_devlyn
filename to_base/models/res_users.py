import threading

from odoo import api, fields, models, modules


class ResUsers(models.Model):
    _inherit = 'res.users'

    # this field is for the SaaS to charge instances having marketplace users. See the module viin_marketplace
    marketplace_merchant = fields.Boolean(
        compute='_compute_marketplace_merchant', string='Marketplace Merchant User', store=True,
        help="External user with limited access to marketplace merchant functionalities"
        )

    @api.depends('all_group_ids')
    def _compute_marketplace_merchant(self):
        self.marketplace_merchant = False

    def _default_groups(self):
        """
        Skip in other tests
        """
        if modules.module.current_test or getattr(threading.current_thread(), 'testing', False):
            self.env['ir.config_parameter'].sudo().set_param("base_setup.default_user_rights_minimal", False)
        return super()._default_groups()
