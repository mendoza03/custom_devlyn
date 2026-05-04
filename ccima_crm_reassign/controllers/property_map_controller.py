# -*- coding: utf-8 -*-
from odoo import http
from odoo.http import request


class PropertyMapController(http.Controller):

    @http.route("/property/map/<int:map_id>", type="http", auth="user", website=True)
    def property_map_page(self, map_id, **kwargs):
        rec = request.env["property.map"].sudo().browse(map_id)
        if not rec.exists():
            return request.not_found()
        image_url = f"/web/image/property.map/{rec.id}/image"
        values = {"record": rec, "image_url": image_url}
        # OJO: usa el XMLID del módulo donde está el template
        return request.render("ccima_crm_reassign.property_map_public_page", values)
