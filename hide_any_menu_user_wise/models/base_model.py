# -*- coding: utf-8 -*-
import logging
from lxml import etree
from odoo import api, models

_logger = logging.getLogger(__name__)

SKIP_MODELS = ("ir.", "base.", "menu.restriction")


class Base(models.AbstractModel):
    _inherit = "base"

    @api.model
    def get_views(self, views, options=None):
        result = super().get_views(views, options=options)

        if self.env.su or self.env.user.has_group("base.group_system"):
            return result

        model_name = self._name
        if any(model_name.startswith(prefix) for prefix in SKIP_MODELS):
            return result

        try:
            hidden_buttons = self.env["menu.restriction.button"].sudo().search([
                ("active", "=", True),
                ("model_name", "=", model_name),
            ])
            if not hidden_buttons:
                return result

            user_id = self.env.user.id
            applicable_button_names = set()
            for btn in hidden_buttons:
                group = btn.restriction_group_id
                if not group.active:
                    continue
                if user_id in group.user_ids.ids:
                    applicable_button_names.add(btn.button_name)

            if not applicable_button_names:
                return result

            for view_type, view_data in result.get("views", {}).items():
                arch_str = view_data.get("arch")
                if not arch_str:
                    continue
                arch = etree.fromstring(arch_str)
                modified = False
                for btn_name in applicable_button_names:
                    for btn_node in arch.xpath("//button[@name='%s']" % btn_name):
                        btn_node.set("invisible", "True")
                        modified = True
                if modified:
                    view_data["arch"] = etree.tostring(arch, encoding="unicode")

        except Exception as e:
            _logger.error("MENU RESTRICTION BUTTON ERROR: model=%s error=%s", model_name, str(e))

        return result
