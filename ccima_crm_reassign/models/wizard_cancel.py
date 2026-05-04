from odoo import models, fields
from odoo.exceptions import UserError
import re
from markupsafe import Markup

# -*- coding: utf-8 -*-
from odoo import api, fields, models, _


class ProductCancelSequence(models.Model):
    _name = "product.cancel.sequence"
    _description = "Product Cancel Sequence"
    _rec_name = "display_name"

    product_name = fields.Char(required=True, index=True)
    base_code = fields.Char(required=True, index=True)
    next_number = fields.Integer(default=1, required=True)

    display_name = fields.Char(compute="_compute_display_name", store=False)


    def _compute_display_name(self):
        for rec in self:
            rec.display_name = f"{rec.product_name} | {rec.base_code} -> next {rec.next_number}"

    @api.model
    def get_and_increment(self, product_name, base_code):
        Seq = self.sudo()
        rec = Seq.search([
            ("product_name", "=", product_name),
            ("base_code", "=", base_code),
        ], limit=1)

        if not rec:
            rec = Seq.create({
                "product_name": product_name,
                "base_code": base_code,
                "next_number": 1,
            })

        current = rec.next_number
        rec.next_number = current + 1
        return current


class ProductCancelWizard(models.TransientModel):
    _name = 'product.cancel.wizard'
    _description = 'Product Cancel Wizard'

    cancel_type_id = fields.Many2one(
        'cancel.types',
        string='Cancel Type',
        required=True
    )

    cancel_reason = fields.Selection(
        [
            ("cancelaciones", "Cancelaciones"),
            ("reubicaciones", "Reubicaciones"),
            ("recesiones", "Recesiones"),
        ],
        string="Dwelling Type",
    )

    upload_files = fields.Boolean(string="Upload files to product folder")
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "product_cancel_wizard_ir_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="Files",
        help="Upload files that will be stored in the product folder (Documents).",
    )

    # ----------------------------
    # Helpers (NEW) - do not change existing logic, only add workspace_id if available
    # ----------------------------
    def _mm_get_doc_workspace_id(self, doc):
        """Return workspace_id of a documents.document record if field exists, else False."""
        try:
            if doc and "workspace_id" in doc._fields and doc.workspace_id:
                return doc.workspace_id.id
        except Exception:
            pass
        return False

    def _mm_prepare_folder_vals(self, parent_folder, name, owner_id=False):
        """Build vals for a folder, inheriting workspace_id from parent when possible."""
        vals = {
            "name": name or "Unnamed",
            "owner_id": owner_id or False,
            "type": "folder",
            "access_internal": "view",
            "folder_id": parent_folder.id,
        }
        ws_id = self._mm_get_doc_workspace_id(parent_folder)
        if ws_id:
            vals["workspace_id"] = ws_id
        return vals

    def _mm_prepare_file_vals(self, folder, attachment, owner_id=False):
        """Build vals for a file document, inheriting workspace_id from folder when possible."""
        vals = {
            "name": attachment.name or "Cancelación",
            "type": "binary",
            "folder_id": folder.id,
            "attachment_id": attachment.id,
            "owner_id": owner_id or False,
            "access_internal": "view",
        }
        ws_id = self._mm_get_doc_workspace_id(folder)
        if ws_id:
            vals["workspace_id"] = ws_id
        return vals


    def action_confirm(self):
        self.ensure_one()

        # ---- Get brief from context (as you already changed) ----
        active_model = self.env.context.get("active_model")
        active_id = self.env.context.get("active_id")

        if active_model != "rev.crm.contract.brief" or not active_id:
            return {"type": "ir.actions.act_window_close"}

        brief = self.env["rev.crm.contract.brief"].browse(active_id).exists()
        if not brief:
            return {"type": "ir.actions.act_window_close"}

        sale_order = brief.sale_order_id
        if not sale_order or not sale_order.order_line:
            return {"type": "ir.actions.act_window_close"}

        product = sale_order.order_line[0].product_template_id.exists()
        if not product:
            return {"type": "ir.actions.act_window_close"}

        # ---- Your original logic (kept, shortened here for clarity) ----
        Seq = self.env["product.cancel.sequence"].sudo()
        Product = self.env["product.template"].sudo()
        Doc = self.env["documents.document"].sudo()
        root_user = self.env.ref("base.user_root", raise_if_not_found=False)

        def _get_ws_parent_folder(product):
            if "condominium_worksite_id" not in product._fields:
                return False
            ws = product.condominium_worksite_id
            if not ws:
                return False
            if "carpet_id" in ws._fields and ws.carpet_id:
                return ws.carpet_id
            if "carpert_id" in ws._fields and ws.carpert_id:
                return ws.carpert_id
            return False

        def _folder_create(name, parent_folder):
            if not parent_folder:
                return False
            vals = {
                "name": name or "Unnamed",
                "owner_id": root_user.id if root_user else False,
                "type": "folder",
                "access_internal": "view",
                "folder_id": parent_folder.id,
            }
            return Doc.create(vals)

        def _folder_find_or_create_child(parent_folder, child_name):
            if not parent_folder:
                return False
            found = Doc.search(
                [
                    ("type", "=", "folder"),
                    ("name", "=", child_name),
                    ("folder_id", "=", parent_folder.id),
                ],
                limit=1,
            )
            return found or _folder_create(child_name, parent_folder)

        # ---------- Process the product ----------
        base_ref = (product.default_code or "").strip() or str(product.id)
        seq_number = Seq.get_and_increment(product.name, base_ref)
        canceled_code = f"{base_ref}-cancelado-{seq_number}"

        reason_key = self.cancel_reason
        original_folder = product.carpet_id if "carpet_id" in product._fields else False
        original_folder_name = original_folder.name if original_folder else False
        ws_parent_folder = _get_ws_parent_folder(product)

        product.write(
            {
                "active": False,
                "cancel_type_id": self.cancel_type_id.id,
                "default_code": canceled_code,
            }
        )

        #Reservation = self.env["property.reservation"].sudo()

        #reservations = Reservation.search([("property_id", "=", product.id)])

        #if reservations:
        #    reservations.write({
        #        "property_id": False,
        #    })

        if original_folder and original_folder_name and reason_key:
            original_folder.write({"name": f"{original_folder_name}-{reason_key}"})

        if original_folder and ws_parent_folder and reason_key:
            reason_folder = _folder_find_or_create_child(ws_parent_folder, reason_key)
            if reason_folder:
                original_folder.write({"folder_id": reason_folder.id})

        vals = {
            "name": product.name,
            "active": True,
            "cancel_type_id": False,
            "default_code": base_ref,
        }

        def add(field):
            if field in product._fields:
                value = product[field]
                if value:
                    vals[field] = value.id if hasattr(value, "id") else value

        for field in [
            "partner_id",
            "second_partner_id",
            "worksite_id",
            "project_worksite_id",
            "condominium_worksite_id",
            "project_type",
            "lot",
            "terrain_type",
            "property_area",
            "price_per_m",
            "list_amount",
            "capital_gains",
            "net_price",
        ]:
            add(field)

        for field, default in {
            "property_date": False,
            "discount": 0.0,
            "price_unit": 0.0,
            "net_amount": 0.0,
            "down_payment_percent": 0.0,
            "down_payment_amount": 0.0,
            "early_payment_percent": 0.0,
            "early_payment_amount": 0.0,
            "final_down_payment": 0.0,
            "amount_to_finance": 0.0,
            "date_deliver": False,
            "month_financing": 0,
            "final_amount": 0.0,
            "delivery_date": False,
            "msi": False,
            "month_0": 0.0,
            "monthly_percent_m": 0.0,
            "month_1": 0.0,
            "monthly_percent": 0.0,
            "month_125": 0.0,
            "total_paid": 0.0,
            "asesor": False,
            "gerente": False,
            "dvn": False,
            "cco": False,
            "is_property": True,
        }.items():
            if field in product._fields:
                vals[field] = default

        if "code_new" in Product._fields:
            vals["code_new"] = base_ref

        if "no_config" in Product._fields:
            vals["no_config"] = True

        new_product = Product.create(vals)

        if ws_parent_folder and original_folder_name and "carpet_id" in new_product._fields:
            new_folder = _folder_create(original_folder_name, ws_parent_folder)
            if new_folder:
                new_product.write({"carpet_id": new_folder.id})

                docs_folder = _folder_find_or_create_child(new_folder, "Documentos")
                contracts_folder = _folder_find_or_create_child(new_folder, "Contratos")

                vals_brief = {}
                if docs_folder and "brief_folder_id" in brief._fields:
                    vals_brief["brief_folder_id"] = docs_folder.id
                if contracts_folder and "contract_folder_id" in brief._fields:
                    vals_brief["contract_folder_id"] = contracts_folder.id

                if vals_brief:
                    brief.sudo().write(vals_brief)

        if not self.upload_files:
            print("UPLOAD FILES is FALSE → skipping upload")
        elif not self.attachment_ids:
            print("UPLOAD FILES is TRUE but NO attachments provided")
        else:
            if "brief_folder_id" not in brief._fields:
                target_folder = False
            else:
                target_folder = brief.brief_folder_id

            if not target_folder:
                print("ERROR: target_folder is EMPTY → cannot create documents")
            else:
                for att in self.attachment_ids:
                    try:
                        att.sudo().write({
                            "res_model": "product.template",
                            "res_id": new_product.id,
                        })
                    except Exception as e:
                        print("ERROR while relinking attachment:", e)

                    existing = Doc.sudo().search([
                        ("folder_id", "=", target_folder.id),
                        ("attachment_id", "=", att.id),
                    ], limit=1)

                    if existing:
                        continue

                    try:
                        doc = Doc.sudo().create({
                            "name": att.name or "Unnamed",
                            "type": "binary",  # IMPORTANT
                            "folder_id": target_folder.id,  # brief folder
                            "attachment_id": att.id,
                            "owner_id": root_user.id if root_user else False,
                            "access_internal": "view",
                        })
                        print("Document CREATED successfully → ID:", doc.id)

                    except Exception as e:
                        print("ERROR while creating documents.document:", e)

            Contract = self.env["property.contract"].sudo()
            contract = Contract.search([("order_id", "=", sale_order.id)], limit=1)

            if contract and self.attachment_ids:

                parent_folder = brief.brief_folder_id if "brief_folder_id" in brief._fields else False


                if not parent_folder:
                    print("ERROR: brief_folder_id is missing/empty -> cannot store contract cancel documents")
                else:
                    cancel_folder = contract.cancel_folder_id if "cancel_folder_id" in contract._fields else False

                    if not cancel_folder:
                        folder_name = f"Cancelaciones - {contract.display_name or contract.name or contract.id}"

                        cancel_folder = _folder_find_or_create_child(parent_folder, folder_name)

                        if cancel_folder and "workspace_id" in cancel_folder._fields and not cancel_folder.workspace_id:
                            ws_id = self._mm_get_doc_workspace_id(parent_folder)
                            if ws_id:
                                try:
                                    cancel_folder.sudo().write({"workspace_id": ws_id})
                                    print("Folder workspace_id set to:", ws_id)
                                except Exception as e:
                                    print("WARN: could not set folder workspace_id:", e)


                        if cancel_folder and "cancel_folder_id" in contract._fields:
                            contract.write({"cancel_folder_id": cancel_folder.id})

                    if cancel_folder:

                        for att in self.attachment_ids:

                            new_att = att.sudo().copy({
                                "res_model": "property.contract",
                                "res_id": contract.id,
                            })


                            existing_doc = Doc.sudo().search([
                                ("folder_id", "=", cancel_folder.id),
                                ("attachment_id", "=", new_att.id),
                            ], limit=1)


                            if existing_doc:
                                continue

                            doc_vals = self._mm_prepare_file_vals(
                                cancel_folder,
                                new_att,
                                owner_id=(root_user.id if root_user else False),
                            )
                            doc = Doc.sudo().create(doc_vals)


        return {"type": "ir.actions.act_window_close"}


class MissingDocumentsEmailWizard(models.TransientModel):
    _name = "missing.documents.email.wizard"
    _description = "Missing Documents Email Wizard"

    rev_id = fields.Many2one("rev.crm.contract.brief", required=True)
    extra_message = fields.Text(string="Additional message")

    contract_body = fields.Text(string="Mensaje envío de contrato")

    # NEW: attachments to send with the email
    attachment_ids = fields.Many2many(
        "ir.attachment",
        "missing_docs_email_wizard_ir_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="Attachments",
        help="Files added here will be sent as email attachments.",
    )

    def action_send(self):
        self.ensure_one()
        rev = self.rev_id

        partner = rev.lead_id.partner_id
        if not partner or not partner.email:
            raise UserError(_("The customer does not have an email address."))

        doc_map = [
            ("full_name_file_name", "Nombre completo (documento)"),
            ("official_id_file_name", "Identificación oficial"),
            ("address_file_name", "Comprobante de domicilio"),
            ("bank_statement_file_name", "Estado de cuenta bancario"),
            ("rfc_file_name", "RFC"),
            ("curp_file_name", "CURP"),
        ]

        missing = []
        for field_name, label in doc_map:
            if not hasattr(rev, field_name) or not getattr(rev, field_name):
                missing.append(f"• {label}")

        if not missing:
            raise UserError(_("All documents are already uploaded."))

        nombre_cliente = rev.lead_id.partner_id.name or ""
        nombre_unidad = rev.lot or ""
        nombre_desarrollo = rev.worksite_id.name if rev.worksite_id else ""

        missing_html = "<br/>".join(missing)

        extra_html = ""
        if self.extra_message:
            msg = (self.extra_message or "").strip().replace("\n", "<br/>")
            extra_html = f"""
                <p><b>Notas adicionales:</b><br/>{msg}</p>
            """

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        upload_url = f"{base_url}/contract/upload?rev_id={rev.id}"
        banner_url = f"{base_url}/ccima_crm_reassign/static/src/img/cintillo.png"

        body_html = f"""
        <div style="margin:0;padding:0;">
          <style>
            /* Roboto: algunos clientes lo bloquean, pero no afecta si no carga */
            @import url('https://fonts.googleapis.com/css2?family=Roboto:wght@400;700&display=swap');
          </style>

          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
                 style="border-collapse:collapse;font-family:'Roboto', Arial, sans-serif;">
            <tr>
              <td align="center" style="padding:0;margin:0;">
                <table role="presentation" width="700" cellspacing="0" cellpadding="0" border="0"
                       style="border-collapse:collapse;width:700px;max-width:700px;background:#ffffff;">

                  <!-- Cintillo -->
                  <tr>
                    <td style="padding:0;margin:0;">
                      <img src="{banner_url}" alt="Header"
                           style="display:block;width:100%;max-width:700px;height:auto;border:0;outline:none;text-decoration:none;" />
                    </td>
                  </tr>

                  <!-- Contenido -->
                  <tr>
                    <td style="padding:18px 18px 8px 18px;">
                      <p style="margin:0 0 12px 0;font-size:12px;line-height:18px;color:#111;">
                        Hola <b>{nombre_cliente}</b>,
                      </p>

                      <p style="margin:0 0 12px 0;font-size:12px;line-height:18px;color:#111;">
                        Espero que te encuentres muy bien.
                      </p>

                      <p style="margin:0 0 12px 0;font-size:12px;line-height:18px;color:#111;">
                        Queremos recordarte que aún tenemos pendiente la recepción de tus documentos
                        para continuar con la integración de tu expediente correspondiente al lote
                        <b>{nombre_unidad}</b> en el desarrollo <b>{nombre_desarrollo}</b>.
                      </p>

                      <p style="margin:0 0 12px 0;font-size:12px;line-height:18px;color:#111;">
                        Este paso es indispensable para avanzar hacia la elaboración de tu contrato y asegurar
                        que tu proceso continúe sin contratiempos, cuentas con 8 días para concluir con tu proceso de inversión.
                      </p>

                      <!-- Título 16px -->
                      <p style="margin:16px 0 6px 0;font-size:16px;line-height:20px;color:#111;font-weight:700;">
                        Documentos pendientes por enviar
                      </p>

                      <div style="margin:0 0 12px 0;font-size:12px;line-height:18px;color:#111;">
                        {missing_html}
                      </div>

                      {extra_html}

                      <p style="margin:14px 0 6px 0;font-size:12px;line-height:18px;color:#111;">
                        <b>Sube tus archivos aquí:</b>
                      </p>

                      <p style="margin:0 0 14px 0;font-size:12px;line-height:18px;">
                        <a href="{upload_url}" target="_blank"
                           style="color:#0b57d0;text-decoration:underline;word-break:break-word;">
                          {upload_url}
                        </a>
                      </p>

                      <p style="margin:0 0 10px 0;font-size:12px;line-height:18px;color:#111;">
                        Quedo atento(a) a tu confirmación para avanzar.
                      </p>

                      <p style="margin:0;font-size:12px;line-height:18px;color:#111;">
                        Saludos cordiales.
                      </p>
                    </td>
                  </tr>

                </table>
              </td>
            </tr>
          </table>
        </div>
        """

        mail_vals = {
            "subject": "Recordatorio de documentación pendiente para tu apartado",
            "email_to": partner.email,
            "body_html": body_html,
            "auto_delete": False,
        }

        if self.attachment_ids:
            mail_vals["attachment_ids"] = [(6, 0, self.attachment_ids.ids)]

        mail = self.env["mail.mail"].sudo().create(mail_vals)
        mail.send()

        missing_chatter_html = "<br/>".join(missing)

        chatter_body = Markup(f"""
            <p><b>Se envió correo de recordatorio</b> a: {partner.email}</p>
            <p><b>Documentos solicitados:</b><br/>{missing_chatter_html}</p>
            <p><b>Link de carga:</b>
                <a href="{upload_url}" target="_blank">{upload_url}</a>
            </p>
        """)

        rev.message_post(
            body=chatter_body,
            subject="Recordatorio enviado (documentos pendientes)",
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {"type": "ir.actions.act_window_close"}


class ContractSendEmailWizard(models.TransientModel):
    _name = "contract.send.email.wizard"
    _description = "Contract Send Email Wizard"

    rev_id = fields.Many2one("rev.crm.contract.brief", required=True)
    body_text = fields.Text(string="Email body", required=True)

    attachment_ids = fields.Many2many(
        "ir.attachment",
        "contract_send_email_wizard_ir_attachment_rel",
        "wizard_id",
        "attachment_id",
        string="Attachments",
        help="Files added here will be sent as email attachments.",
    )

    def action_send_contract_email(self):
        self.ensure_one()
        rev = self.rev_id

        partner = rev.lead_id.partner_id
        if not partner or not partner.email:
            raise UserError(_("The customer does not have an email address."))

        body_text = (self.body_text or "").strip()
        if not body_text:
            raise UserError(_("Please write the email body."))

        # Convert line breaks to HTML
        body_html_text = body_text.replace("\n", "<br/>")

        base_url = self.env["ir.config_parameter"].sudo().get_param("web.base.url")
        banner_url = f"{base_url}/ccima_crm_reassign/static/src/img/cintillo.png"

        customer_name = partner.name or ""

        body_html = f"""
        <div style="margin:0;padding:0;">
          <table role="presentation" width="100%" cellspacing="0" cellpadding="0" border="0"
                 style="border-collapse:collapse;font-family:Arial, sans-serif;">
            <tr>
              <td align="center" style="padding:0;margin:0;">
                <table role="presentation" width="700" cellspacing="0" cellpadding="0" border="0"
                       style="border-collapse:collapse;width:700px;max-width:700px;background:#ffffff;">
                  <tr>
                    <td style="padding:0;margin:0;">
                      <img src="{banner_url}" alt="Header"
                           style="display:block;width:100%;max-width:700px;height:auto;border:0;outline:none;text-decoration:none;" />
                    </td>
                  </tr>

                  <tr>
                    <td style="padding:18px 18px 18px 18px;font-size:12px;line-height:18px;color:#111;">
                      <p style="margin:0 0 12px 0;">Hola <b>{customer_name}</b>,</p>
                      <p style="margin:0 0 12px 0;">{body_html_text}</p>
                      <p style="margin:0;">Saludos cordiales.</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>
          </table>
        </div>
        """

        mail_vals = {
            "subject": "Envío de contrato",
            "email_to": partner.email,
            "body_html": body_html,
            "auto_delete": False,
        }

        if self.attachment_ids:
            mail_vals["attachment_ids"] = [(6, 0, self.attachment_ids.ids)]

        mail = self.env["mail.mail"].sudo().create(mail_vals)
        mail.send()

        # Chatter on rev
        rev.message_post(
            body=Markup(
                f"""
                <p><b>Se envió correo de contrato</b> a: {partner.email}</p>
                <p><b>Mensaje:</b><br/>{body_html_text}</p>
                """
            ),
            subject="Contrato enviado por correo",
            message_type="comment",
            subtype_xmlid="mail.mt_note",
        )

        return {"type": "ir.actions.act_window_close"}