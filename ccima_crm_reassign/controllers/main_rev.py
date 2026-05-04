# -*- coding: utf-8 -*-
import base64
import re
from odoo import http
from odoo.http import request


class RevContractWebsite(http.Controller):

    def _get_uploaded_filename(self, uploaded_file):
        uploaded_filename = (getattr(uploaded_file, "filename", None) or "").strip()
        if uploaded_filename:
            return uploaded_filename

        content_disposition = ""
        if getattr(uploaded_file, "headers", None):
            content_disposition = uploaded_file.headers.get("Content-Disposition", "") or ""

        match = re.search(r"filename\*=(?:UTF-8'')?([^;]+)", content_disposition, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().strip('"')

        match = re.search(r"filename=([^;]+)", content_disposition, flags=re.IGNORECASE)
        if match:
            return match.group(1).strip().strip('"')

        return ""


    @http.route("/contract/upload", type="http", auth="public", website=True, methods=["GET"], csrf=True)
    def contract_upload_form(self, **kw):
        briefs = request.env["rev.crm.contract.brief"].sudo().search([])
        selected_rev_id = int(kw.get("rev_id") or 0)

        doc_map = [
            ("full_name_file_name", "Nombre completo (documento)"),
            ("official_id_file_name", "Identificación oficial"),
            ("address_file_name", "Comprobante de domicilio"),
            ("bank_statement_file_name", "Estado de cuenta bancario"),
            ("rfc_file_name", "RFC"),
            ("curp_file_name", "CURP"),
        ]

        contract_brief = False
        missing_fields = {}
        field_exists = {}
        all_done = False

        if selected_rev_id:
            contract_brief = request.env["rev.crm.contract.brief"].sudo().browse(selected_rev_id)

            if contract_brief.exists():
                model_fields = contract_brief._fields

                for field_name, _label in doc_map:
                    exists = field_name in model_fields
                    field_exists[field_name] = exists

                    if not exists:
                        missing_fields[field_name] = True
                    else:
                        missing_fields[field_name] = not bool(getattr(contract_brief, field_name))

                all_done = not any(missing_fields.values())
            else:
                selected_rev_id = 0


        print('missing_fields', missing_fields)


        return request.render(
            "ccima_crm_reassign.contract_upload_page",
            {
                "briefs": briefs,
                "selected_rev_id": selected_rev_id,
                "contract_brief": contract_brief,
                "missing_fields": missing_fields,
                "field_exists": field_exists,
                "all_done": all_done,
            },
        )

    @http.route("/contract/upload/submit", type="http", auth="public", website=True, methods=["POST"], csrf=True)
    def contract_upload_submit(self, **post):
        rev_id = int(post.get("rev_id") or 0)
        if not rev_id:
            return request.redirect("/contract/upload")

        brief = request.env["rev.crm.contract.brief"].sudo().browse(rev_id)
        if not brief.exists():
            return request.redirect("/contract/upload")

        file_fields = [
            "full_name_file",
            "official_id_file",
            "address_file",
            "bank_statement_file",
            "rfc_file",
            "curp_file",
        ]

        vals = {}
        for field_name in file_fields:
            file = post.get(field_name)
            if not file:
                continue

            content = file.read()
            if content:
                vals[field_name] = base64.b64encode(content)

        if vals:
            brief.write(vals)

        return request.redirect("/contract/upload/thanks")

    @http.route("/contract/upload/thanks", type="http", auth="public", website=True, methods=["GET"], csrf=False)
    def contract_upload_thanks(self, **kw):
        return request.render("ccima_crm_reassign.contract_upload_thanks_page", {})
