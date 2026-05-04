# -*- coding: utf-8 -*-
import logging
from odoo import api, models

_logger = logging.getLogger(__name__)

PERM_COL_MAP = {
    "read": 1,
    "write": 2,
    "create": 3,
    "unlink": 4,
}

SKIP_MODELS = ("ir.", "base.", "menu.restriction")


class IrModelAccess(models.Model):
    _inherit = "ir.model.access"

    @api.model
    def check(self, model, mode="read", raise_exception=True):
        if self.env.su:
            return True

        assert isinstance(model, str), "Not a model name: %s" % (model,)

        has_access = model in self._get_allowed_models(mode)

        try:
            col_index = PERM_COL_MAP.get(mode)
            skip = any(model.startswith(prefix) for prefix in SKIP_MODELS)

            if col_index and not skip and self.env.user:
                self.env.cr.execute("""
                    SELECT mrp.id,
                           mrp.perm_read,
                           mrp.perm_write,
                           mrp.perm_create,
                           mrp.perm_unlink,
                           mrp.apply_to_all_users
                    FROM menu_restriction_permission mrp
                    JOIN menu_restriction_group mrg ON mrp.restriction_group_id = mrg.id
                    JOIN menu_restriction_group_users_rel rel ON rel.group_id = mrg.id
                    WHERE mrp.model_name = %s
                      AND mrp.active = true
                      AND mrg.active = true
                      AND rel.user_id = %s
                """, (model, self.env.user.id))

                rows = self.env.cr.fetchall()

                if rows:
                    valid_rows = self._filter_valid_rows(rows)

                    if valid_rows:
                        permission_granted = any(row[col_index] for row in valid_rows)

                        _logger.warning(
                            "MENU RESTRICTION CHECK: user=%s model=%s mode=%s granted=%s",
                            self.env.user.name, model, mode, permission_granted
                        )

                        if not permission_granted:
                            has_access = False

        except Exception as e:
            _logger.error(
                "MENU RESTRICTION ERROR: model=%s mode=%s error=%s",
                model, mode, str(e)
            )

        if not has_access and raise_exception:
            raise self._make_access_error(model, mode) from None

        return has_access

    def _filter_valid_rows(self, rows):
        valid_rows = []
        for row in rows:
            perm_id, apply_to_all = row[0], row[5]
            if apply_to_all:
                valid_rows.append(row)
            else:
                self.env.cr.execute("""
                    SELECT 1
                    FROM menu_restriction_permission_users_rel
                    WHERE permission_id = %s
                      AND user_id = %s
                """, (perm_id, self.env.user.id))
                if self.env.cr.fetchone():
                    valid_rows.append(row)
        return valid_rows