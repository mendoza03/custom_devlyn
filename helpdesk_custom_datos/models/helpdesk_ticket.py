import logging
from datetime import datetime, time, timedelta

import pytz

from odoo import api, fields, models, _
from odoo.exceptions import UserError, ValidationError

_logger = logging.getLogger(__name__)


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    _AUTO_CLOSE_WEEKDAY_HOURS = 24.0

    def action_open_form_new_tab(self):
        self.ensure_one()
        menu = self.env.ref("helpdesk.helpdesk_ticket_menu_all")
        url = f"/odoo/helpdesk.ticket/{self.id}?menu_id={menu.id}"
        return {
            "type": "ir.actions.act_url",
            "url": url,
            "target": "new",
        }

    def _get_locked_fields_outside_new_stage(self):
        return {
            "user_id",
            "name",
            "x_general_description",
            "x_centro_sap",
            "x_branch_id",
            "x_numero_telefonico",
            "x_correo",
            "x_section_id",
            "x_category_id",
            "x_subcategory_id",
            "x_detailed_description",
            "x_attachment_line_ids",
        }

    def _is_new_stage(self):
        self.ensure_one()
        stage_name = (self.stage_id.name or "").strip().lower()
        return not self.stage_id or self.stage_id.sequence == 0 or stage_name in ("nuevo", "new")

    @api.model
    def _default_creator_email(self):
        return self.env.user.email or self.env.user.partner_id.email or False

    @api.model
    def _default_creator_phone(self):
        user = self.env.user
        if "work_phone" in user._fields and user.work_phone:
            return user.work_phone
        return user.partner_id.phone or False

    @api.model
    def _default_creator_branch(self):
        return self.env.user.x_branch_id

    @api.model
    def _get_inactivity_timezone(self, ticket):
        return (
            ticket.team_id.resource_calendar_id.tz
            or ticket.user_id.tz
            or ticket.create_uid.tz
            or self.env.user.tz
            or "UTC"
        )

    @api.model
    def _get_weekday_hours_between(self, start_dt, end_dt, tz_name="UTC"):
        if not start_dt or not end_dt or end_dt <= start_dt:
            return 0.0

        tz = pytz.timezone(tz_name or "UTC")
        utc = pytz.UTC
        start_local = utc.localize(start_dt).astimezone(tz)
        end_local = utc.localize(end_dt).astimezone(tz)
        total_seconds = 0.0
        current = start_local

        while current.date() < end_local.date():
            next_midnight = tz.localize(datetime.combine(current.date() + timedelta(days=1), time.min))
            if current.weekday() < 5:
                total_seconds += (next_midnight - current).total_seconds()
            current = next_midnight

        if current.weekday() < 5:
            total_seconds += (end_local - current).total_seconds()

        return total_seconds / 3600.0

    def _get_last_inactivity_datetime(self):
        self.ensure_one()
        return self.write_date or self.create_date or fields.Datetime.now()

    def _get_auto_close_inactive_tickets(self, now=None):
        now = now or fields.Datetime.now()
        threshold = now - timedelta(hours=self._AUTO_CLOSE_WEEKDAY_HOURS)
        tickets = self.search([
            ("stage_id.fold", "=", False),
            ("team_id", "!=", False),
            ("write_date", "<=", threshold),
        ])
        return tickets.filtered(
            lambda ticket: ticket._get_weekday_hours_between(
                ticket._get_last_inactivity_datetime(),
                now,
                ticket._get_inactivity_timezone(ticket),
            ) >= ticket._AUTO_CLOSE_WEEKDAY_HOURS
        )

    @api.model
    def _cron_auto_close_inactive_weekday_tickets(self):
        inactive_tickets = self._get_auto_close_inactive_tickets()
        for ticket in inactive_tickets:
            closing_stage = ticket.team_id._get_closing_stage()[:1]
            if not closing_stage or ticket.stage_id == closing_stage:
                continue
            ticket.write({"stage_id": closing_stage.id})
            ticket.message_post(
                body=_("Ticket cerrado automáticamente tras 24 horas de inactividad en días hábiles."),
                subtype_xmlid="mail.mt_note",
            )

    x_general_description = fields.Char(string="Descripción General", required=True)
    x_centro_sap = fields.Char(string="Centro SAP", copy=False)
    x_branch_id = fields.Many2one(
        "devlyn.catalog.branch",
        string="Sucursal",
        domain=[("active", "=", True)],
        copy=False,
        ondelete="restrict",
        default=lambda self: self._default_creator_branch(),
    )
    x_numero_telefonico = fields.Char(
        string="Número telefónico",
        copy=False,
        default=lambda self: self._default_creator_phone(),
    )
    x_correo = fields.Char(
        string="Correo",
        copy=False,
        default=lambda self: self._default_creator_email(),
    )
    x_is_stage_new = fields.Boolean(
        compute="_compute_x_is_stage_new",
        store=False,
    )


    @api.onchange("x_general_description")
    def _onchange_x_general_description_set_name(self):
        for rec in self:
            if rec.x_general_description:
                rec.name = rec.x_general_description

    @api.onchange("user_id")
    def _onchange_user_id_set_branch(self):
        for rec in self:
            if rec.user_id and not rec.x_branch_id:
                rec.x_branch_id = rec.user_id.x_branch_id

    @api.depends("stage_id.sequence")
    def _compute_x_is_stage_new(self):
        for rec in self:
            rec.x_is_stage_new = not rec.stage_id or rec.stage_id.sequence == 0

    @api.model_create_multi
    def create(self, vals_list):
        for vals in vals_list:
            if vals.get("x_general_description") and not vals.get("name"):
                vals["name"] = vals["x_general_description"]
            if not vals.get("x_numero_telefonico"):
                vals["x_numero_telefonico"] = self._default_creator_phone()
            if not vals.get("x_correo"):
                vals["x_correo"] = self._default_creator_email()
            if not vals.get("x_branch_id"):
                ticket_user = self.env["res.users"].browse(vals.get("user_id")) if vals.get("user_id") else self.env.user
                if ticket_user.x_branch_id:
                    vals["x_branch_id"] = ticket_user.x_branch_id.id
        tickets = super().create(vals_list)

        for ticket in tickets.filtered("user_id"):
            _logger.warning(
                "HELPDESK DEBUG user_id create: ticket_id=%s ticket_ref=%s changed_by_id=%s changed_by=%s old_user_id=%s old_user=%s new_user_id=%s new_user=%s",
                ticket.id,
                ticket.ticket_ref or "",
                self.env.user.id,
                self.env.user.display_name,
                False,
                "",
                ticket.user_id.id,
                ticket.user_id.display_name,
            )

        return tickets

    def write(self, vals):
        blocked_fields = self._get_locked_fields_outside_new_stage().intersection(vals)
        blocked_tickets = self.filtered(lambda ticket: not ticket._is_new_stage())
        if blocked_fields and blocked_tickets:
            raise UserError(
                _(
                    "Solo se pueden modificar estos campos cuando el ticket esta en estado Nuevo."
                )
            )

        previous_user_by_ticket = {}
        if "user_id" in vals:
            for ticket in self:
                previous_user_by_ticket[ticket.id] = ticket.user_id

        if vals.get("x_general_description") and not vals.get("name"):
            vals["name"] = vals["x_general_description"]
        result = super().write(vals)

        if previous_user_by_ticket:
            for ticket in self:
                old_user = previous_user_by_ticket.get(ticket.id)
                new_user = ticket.user_id
                if old_user != new_user:
                    _logger.warning(
                        "HELPDESK DEBUG user_id write: ticket_id=%s ticket_ref=%s changed_by_id=%s changed_by=%s old_user_id=%s old_user=%s new_user_id=%s new_user=%s",
                        ticket.id,
                        ticket.ticket_ref or "",
                        self.env.user.id,
                        self.env.user.display_name,
                        old_user.id if old_user else False,
                        old_user.display_name if old_user else "",
                        new_user.id if new_user else False,
                        new_user.display_name if new_user else "",
                    )

        return result
    
    x_section_id = fields.Many2one("helpdesk.section", string="Sección", required=True)

    x_category_id = fields.Many2one(
        "helpdesk.ticket.category",
        string="Categoría",
        required=True,
        domain="[('section_id', '=', x_section_id)]",
    )

    x_subcategory_id = fields.Many2one(
        "helpdesk.ticket.subcategory",
        string="Subcategoría",
        required=True,
        domain="[('category_id', '=', x_category_id)]",
    )

    x_subcategory_code = fields.Char(
        related="x_subcategory_id.code",
        store=True,
        readonly=True,
    )

    x_detailed_description = fields.Html(string="Descripción Detallada")

    x_attachment_line_ids = fields.One2many(
        "helpdesk.ticket.attachment.line",
        "ticket_id",
        string="Anexos",
        copy=False,
    )

    x_order_number = fields.Char(string="Pedido", copy=False)
    x_bag = fields.Char(string="Bolsa", copy=False)
    x_customer_warehouse = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Armazón del cliente?",
        default="select",
        copy=False,
    )
    x_order_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("retallado", "Retallado"),
            ("garantia_calidad", "Garantía de calidad"),
            ("satisfaccion_adaptacion", "Satisfacción total de adaptación"),
            ("satisfaccion_imagen", "Satisfacción total de imagen"),
            ("captura_primera_vez", "Captura primera vez"),
        ],
        string="Tipo de pedido",
        default="select",
        copy=False,
    )
    x_lab_indicated = fields.Char(
        string="LAB indicado en portal de seguimiento de trabajos",
        copy=False,
    )

    x_shipping_guide_number = fields.Char(
        string="Número de guía de envío de armazón",
        copy=False,
    )
    x_frame_bag_number = fields.Char(
        string="Número de bolsa de envío de armazón",
        copy=False,
    )
    x_authorized_by = fields.Char(string="Persona que Autoriza", copy=False)
    x_order_type_adaptation = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("lab_indicated", "LAB indicado en portal de seguimiento de trabajo"),
            ("shipping_guide_number", "Número de guía de envío de armazón"),
            ("frame_bag_number", "Número de bolsa de envío de armazón"),
        ],
        string="Tipo de pedido",
        default="select",
        copy=False,
    )
    x_original_order_number = fields.Char(string="N° de pedido original", copy=False)
    x_job_type = fields.Char(string="Tipo de Trabajo", copy=False)
    x_order_type_imagen = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("lab_indicated", "LAB indicado en portal de seguimiento de trabajo"),
            ("shipping_guide_number", "Número de guía de envío de armazón"),
            ("frame_bag_number", "Número de bolsa de envío de armazón"),
        ],
        string="Tipo de pedido",
        default="select",
        copy=False,
    )

    x_branch_email = fields.Char(string="Correo electronico de Sucursal", copy=False)
    x_email_issue_type_2 = fields.Char(
        string="Tipo de Error, Envio o Recepción",
        copy=False,
    )
    x_contact_number = fields.Char(string="Número de contacto", copy=False)

    x_internal_folio_number = fields.Char(
        string="Número de folio interno.",
        copy=False,
    )

    x_equipment_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("scanner", "Scanner"),
            ("impresora", "Impresora"),
            ("cpu", "CPU"),
            ("transfer", "Transfer"),
            ("no_break", "No break"),
            ("monitor", "Monitor"),
            ("otro", "Otro"),
        ],
        string="Tipo de equipo",
        default="select",
        copy=False,
    )

    x_model_or_brand = fields.Char(string="Modelo y/o marca", copy=False)
    x_serial_number = fields.Char(string="Número de Serie", copy=False)
    x_fixed_asset_number = fields.Char(string="N° de activo fijo", copy=False)
    x_shipping_guide = fields.Char(string="N° de guía", copy=False)
    x_courier = fields.Char(string="Mensajería", copy=False)

    x_store_number = fields.Char(string="N° de comercio", copy=False)
    x_interredes_user = fields.Char(string="Usuario de Interredes", copy=False)

    x_printer_model = fields.Char(string="Modelo de impresora", copy=False)

    x_contact_person_name = fields.Char(
        string="Nombre de la persona que nos contactó",
        copy=False,
    )

    x_toner_below_15 = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="¿El tóner es menor o igual al 15%?",
        default="select",
        copy=False,
    )

    x_cleaning_area = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("aparadores", "Aparadores"),
            ("piso", "Piso"),
            ("bano", "Baño"),
            ("anuncios", "Anuncios"),
        ],
        string="Área",
        default="select",
        copy=False,
    )

    x_fact_busco_portal = fields.Selection(
        [("select", "-- seleccionar --"), ("si", "Si"), ("no", "No")],
        default="select",
        copy=False,
    )
    x_fact_encontraste = fields.Selection(
        [("select", "-- seleccionar --"), ("si", "Si"), ("no", "No")],
        default="select",
        copy=False,
    )
    x_fact_pdf_xml_incorrectos = fields.Selection(
        [("select", "-- seleccionar --"), ("si", "Si"), ("no", "No")],
        default="select",
        copy=False,
    )

    x_is_facturacion_reenvio = fields.Boolean(
        compute="_compute_x_is_facturacion_reenvio",
        store=False,
    )
    x_is_dev_real_tc_db = fields.Boolean(
        compute="_compute_x_devolucion_category_flags",
        store=False,
    )
    x_is_dev_real_cash_order = fields.Boolean(
        compute="_compute_x_devolucion_category_flags",
        store=False,
    )
    x_is_dev_real_cash_transfer = fields.Boolean(
        compute="_compute_x_devolucion_category_flags",
        store=False,
    )

    x_is_receta_lc = fields.Boolean(
        compute="_compute_x_category_flags_extra",
        store=False,
    )
    x_is_papeleria_seguimiento = fields.Boolean(
        compute="_compute_x_category_flags_extra",
        store=False,
    )
    x_is_resurtido_consumibles_seguimiento = fields.Boolean(
        compute="_compute_x_category_flags_extra",
        store=False,
    )

    # Flags específicos para evitar bloques repetidos en la vista
    x_is_atraso_lente_contacto_online = fields.Boolean(
        compute="_compute_x_view_context_flags",
        store=False,
    )
    x_is_atraso_lente_contacto_receta = fields.Boolean(
        compute="_compute_x_view_context_flags",
        store=False,
    )
    x_is_seguimiento_solicitud_papeleria = fields.Boolean(
        compute="_compute_x_view_context_flags",
        store=False,
    )
    x_is_seguimiento_solicitud_resurtido = fields.Boolean(
        compute="_compute_x_view_context_flags",
        store=False,
    )

    x_refac_order_number = fields.Char(string="Pedido (*)", copy=False)
    x_refac_sale_order = fields.Char(string="Orden de Venta (*)", copy=False)
    x_refac_legal_name = fields.Char(
        string="Nombre o denominación social (*)",
        copy=False,
    )
    x_refac_rfc = fields.Char(string="RFC (*)", copy=False)

    x_refac_sat_screen_attached = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Dar click una vez que se adjunte la pantalla",
        default="select",
        copy=False,
    )

    x_refac_payment_method = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("efectivo", "Efectivo"),
            ("tarjeta_debito", "Tarjeta de Débito"),
            ("tarjeta_credito", "Tarjeta de crédito"),
            ("cheque_nominativo", "Cheque nominativo"),
            ("monedero_electronico", "Monedero electrónico"),
        ],
        string="Forma de Pago (*)",
        default="select",
        copy=False,
    )

    x_refac_person_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("fisica", "Fisica"),
            ("moral", "Moral"),
        ],
        string="Tipo persona (*)",
        default="select",
        copy=False,
    )

    x_refac_cfdi_use = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("g01", "G01 Adquisición de mercancías."),
            ("g02", "G02 Devoluciones, descuentos o bonificaciones."),
            ("g03", "G03 Gastos en general."),
            ("i01", "I01 Construcciones."),
            ("i02", "I02 Mobiliario y equipo de oficina por inversiones."),
            ("i03", "I03 Equipo de transporte."),
            ("i04", "I04 Equipo de computo y accesorios."),
            ("i05", "I05 Dados, troqueles, moldes, matrices y herramental."),
            ("i06", "I06 Comunicaciones telefónicas."),
            ("i07", "I07 Comunicaciones satelitales."),
            ("i08", "I08 Otra maquinaria y equipo."),
            ("d01", "D01 Honorarios médicos, dentales y gastos hospitalarios."),
            ("d02", "D02 Gastos médicos por incapacidad o discapacidad."),
            ("d03", "D03 Gastos funerales."),
            ("d04", "D04 Donativos."),
            ("d05", "D05 Intereses reales efectivamente pagados por créditos hipotecarios (casa habitación)."),
            ("d06", "D06 Aportaciones voluntarias al SAR."),
            ("d07", "D07 Primas por seguros de gastos médicos."),
            ("d08", "D08 Gastos de transportación escolar obligatoria."),
            ("d09", "D09 Depósitos en cuentas para el ahorro, primas que tengan como base planes de pensiones."),
            ("d10", "D10 Pagos por servicios educativos (colegiaturas)."),
            ("s01", "S01 Sin efectos fiscales."),
            ("cp01", "CP01 Pagos"),
            ("cn01", "CN01 Nómina"),
        ],
        string="Uso CFDI (*)",
        default="select",
        copy=False,
    )

    x_refac_fiscal_regime = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("601", "601 General de Ley Personas Morales"),
            ("603", "603 Personas Morales con Fines no Lucrativos"),
            ("606", "606 Arrendamiento"),
            ("612", "612 Personas Físicas con Actividades Empresariales y Profesionales"),
            ("620", "620 Sociedades Cooperativas de Producción que optan por Diferir sus Ingresos"),
            ("621", "621 Incorporación Fiscal"),
            ("622", "622 Actividades Agrícolas, Ganaderas, Silvícolas y Pesqueras"),
            ("623", "623 Opcional para Grupos de Sociedades"),
            ("624", "624 Coordinados"),
            ("625", "625 Régimen de las Actividades Empresariales con ingresos a través de Plataformas Tecnológicas"),
            ("626", "626 Régimen Simplificado de Confianza (RESICO)"),
        ],
        string="Régimen Fiscal (*)",
        default="select",
        copy=False,
    )

    x_refac_fiscal_address = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("solo_cp", "Solo CP"),
        ],
        string="Dirección fiscal (*)",
        default="select",
        copy=False,
    )

    x_refac_cp = fields.Char(string="CP (*)", copy=False)

    x_card_client_name = fields.Char(string="Nombre del Cliente (*)", copy=False)
    x_card_sap_center = fields.Char(string="Centro SAP (*)", copy=False)
    x_card_sale_order = fields.Char(string="Orden de Venta (*)", copy=False)
    x_card_order_number = fields.Char(string="Pedido (*)", copy=False)

    x_card_sale_date = fields.Date(string="Fecha de Venta (*)", copy=False)
    x_card_sale_amount = fields.Float(string="Monto de la venta (*)", copy=False)
    x_card_refund_amount = fields.Float(string="Monto a devolver (*)", copy=False)
    x_card_refund_reason = fields.Char(string="Motivo de devolución (*)", copy=False)

    x_card_number_16_digits = fields.Char(
        string="N° completo de la tarjeta 16 dígitos (*)",
        copy=False,
    )
    x_card_expiration_mmaa = fields.Char(
        string="Fecha de Vencimiento MMAA (*)",
        copy=False,
    )
    x_card_authorization_number = fields.Char(
        string="Número de Autorización (*)",
        copy=False,
    )
    x_card_holder_relationship = fields.Char(
        string="Parentesco Titular de la tarjeta con nombre r (*)",
        copy=False,
    )

    x_card_client_received_product = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="¿El cliente recibió su producto? (*)",
        default="select",
        copy=False,
    )

    x_duplicate_affiliation = fields.Char(
        string="Afiliación (Tarjeta y duplicados)",
        copy=False,
    )
    x_duplicate_tracking_id = fields.Char(
        string="No. de seguimiento o ID (Tarjeta y duplicados)",
        copy=False,
    )
    x_duplicate_internal_terminal = fields.Char(
        string="Terminal Interna (Tarjeta y duplicados)",
        copy=False,
    )

    x_duplicate_refund_request_attached = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="¿Solicitud de devolución adjunta?",
        copy=False,
    )

    x_exam_ov_cancelled = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="OV Cancelada",
        copy=False,
    )

    x_exam_refund_request_attached = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Solicitud de devolución adjunta?",
        copy=False,
    )

    x_cash_society = fields.Char(string="Sociedad (*)", copy=False)
    x_cash_banamex_branch_number = fields.Char(
        string="Número de sucursal Banamex (*)",
        copy=False,
    )
    x_cash_beneficiary_name = fields.Char(
        string="Nombre del beneficiario (*)",
        copy=False,
    )
    x_transfer_clabe_18 = fields.Char(
        string="Cuenta Clabe 18 dígitos (*)",
        copy=False,
    )
    x_transfer_account_holder = fields.Char(
        string="Titular de la cuenta (*)",
        copy=False,
    )
    x_transfer_bank = fields.Char(string="Banco (*)", copy=False)

    x_ale_incident_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("alta_sucursal", "Alta de Sucursal"),
            ("captura_minimo", "Captura de Mínimo"),
            ("reinicio_contrasena", "Reinicio de Contraseña"),
            ("otros", "Otros"),
        ],
        string="¿Que incidente tienes con la página ALE? (*)",
        default="select",
        copy=False,
    )

    x_ale_employee_name = fields.Char(string="Nombre del empleado (*)", copy=False)
    x_ale_branch = fields.Char(string="Sucursal (*)", copy=False)
    x_ale_region = fields.Char(string="Región (*)", copy=False)
    x_ale_district = fields.Char(string="Distrito (*)", copy=False)

    x_university_incident_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("alta_usuario", "Alta de usuario"),
            ("nuevo_intento", "Nuevo intento"),
            ("validacion_curso", "Validación de curso"),
            ("no_cambia_estatus_curso_completo", "No cambia estatus de curso completo"),
            ("no_habilita_siguiente_puesto", "No me habilita el siguiente puesto"),
            ("otros", "Otros"),
        ],
        string="¿Qué incidente tuviste con el curso Online? (*)",
        default="select",
        copy=False,
    )

    x_university_employee_name = fields.Char(
        string="Nombre del empleado a consultar (*)",
        copy=False,
    )
    x_university_employee_number = fields.Char(
        string="N° de empleado (*)",
        copy=False,
    )
    x_university_branch = fields.Char(string="Sucursal (*)", copy=False)
    x_university_zone = fields.Char(string="Zona. (*)", copy=False)
    x_university_district = fields.Char(string="Distrito (*)", copy=False)
    x_university_course_name = fields.Char(
        string="Nombre del curso en línea (*)",
        copy=False,
    )
    x_university_real_position = fields.Char(string="Puesto real (*)", copy=False)

    x_eval_request_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("carpeta_producto", "Carpeta de Producto"),
            ("credito_devlyn", "Credito Devlyn"),
            ("garantias_10", "Garantias de 10"),
        ],
        string="Tipo de Solicitud (*)",
        default="select",
        copy=False,
    )

    x_eval_ale_incident = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("alta_sucursal", "Alta de Sucursal"),
            ("captura_minimo", "Captura de Mínimo"),
            ("reinicio_contrasena", "Reinicio de Contraseña"),
            ("otros", "Otros"),
        ],
        string="¿Que incidente tienes con la página ALE? (*)",
        default="select",
        copy=False,
    )

    x_eval_employee_name = fields.Char(string="Nombre del empleado (*)", copy=False)
    x_eval_employee_number = fields.Char(string="N° de empleado (*)", copy=False)
    x_eval_branch = fields.Char(string="Sucursal (*)", copy=False)

    x_eval_policies_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("activar_cuestionario_no_aprobado", "Activar nuevamente el cuestionario no aprobado"),
            ("atencion_personalizada_ext_4271", "Atención personalizada marca Ext.:4271"),
            ("no_estoy_registrado", "No estoy registrado"),
            ("no_recuerdo_contrasena", "No recuerdo mi contraseña"),
            ("no_considero_plan_carrera", "Por que no se considero en plan de carrera"),
        ],
        string="Página de Evaluaciones (*)",
        default="select",
        copy=False,
    )

    x_eval_policies_employee_name = fields.Char(
        string="Nombre del empleado (*)",
        copy=False,
    )
    x_eval_policies_employee_number = fields.Char(
        string="N° de empleado (*)",
        copy=False,
    )
    x_eval_policies_branch = fields.Char(string="Sucursal (*)", copy=False)

    x_promotion_is_responsible = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Soy Responsable (*)",
        default="select",
        copy=False,
    )

    x_promotion_interested_name = fields.Char(
        string="Nombre del interesado (*)",
        copy=False,
    )
    x_promotion_employee_numbers = fields.Char(
        string="Numero(s) de empleados (*)",
        copy=False,
    )

    x_display_missing_promo_campaign = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("barnner_50x150", "Barnner de .50x1.50"),
            ("barnner_75x175", "Barnner de .75x1.75"),
            ("paquete_no_llego", "El paquete no llego"),
            ("identificador_30x30", "Identificador de 30cm x 30cm"),
            ("identificador_35x17", "Identificador de 35cm x 17cm"),
            ("poster_sin_ojillos", "Poster sin Ojillos (Porta Promociones)"),
            ("poster_con_ojillos", "Poster con ojillos (Aparador)"),
            ("regleta_promocion_secundaria", "Regleta promoción secundaria"),
            ("solicitud_adicional", "Solicitud Adicional"),
            ("ten_card", "Ten Card"),
            ("vinil_jitomatazo", "Vinil Jitomatazo"),
        ],
        string="Faltante de Campaña Promociones",
        default="select",
        copy=False,
    )

    x_display_manual_read = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Lei el manual (*)",
        default="select",
        copy=False,
    )

    x_display_aparador_type = fields.Char(string="Tipo de Aparador (*)", copy=False)

    x_display_checklist_review = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Revise Check List (*)",
        default="select",
        copy=False,
    )

    x_display_missing_campaign_aparador = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("cenefa_repisa", "Cenefa de repisa"),
            ("colgante", "Colgante"),
            ("paquete_no_llego", "El paquete no llego"),
            ("lona_aparador", "Lona de Aparador"),
            ("solicitud_adicional", "Solicitud Adicional"),
            ("vinil_aparador", "Vinil de Aparador"),
        ],
        string="Faltante de Campaña en Aparador",
        default="select",
        copy=False,
    )

    x_display_other = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Otro",
        copy=False,
    )

    x_display_checklist_attached = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Es obligatorio añadir el check list donde se señale el elemento faltante.",
        copy=False,
    )

    x_damaged_element_to_replace = fields.Char(
        string="Elemento dañado a reponer (*)",
        copy=False,
    )
    x_damaged_brief_description = fields.Char(
        string="Breve Descripción (*)",
        copy=False,
    )
    x_damaged_quantity = fields.Char(string="Cantidad (*)", copy=False)
    x_damaged_measurements = fields.Char(string="Medidas (*)", copy=False)

    x_damaged_photo_attached = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Agregar en anexos la foto de material dañado (*)",
        copy=False,
    )

    x_agreement_support_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("001_999_zona_metro", "001_999 Zona Metro"),
            ("6000_6499_zona_metro", "6000_6499 Zona Metro"),
            ("3000_3999_zona_foranea", "3000_3999 Zona Foranea"),
        ],
        string="Convenios (*)",
        default="select",
        copy=False,
    )

    x_agreement_number = fields.Char(string="N° de Convenio (*)", copy=False)
    x_agreement_social_name = fields.Char(
        string="Nombre o denominación social (*)",
        copy=False,
    )

    x_payment_center = fields.Char(string="Centro (*)", copy=False)
    x_payment_pos_order = fields.Char(string="Pedido POS. (*)", copy=False)
    x_payment_sale_date = fields.Date(string="Fecha de Venta (*)", copy=False)
    x_payment_sale_total = fields.Float(string="Total de Venta (*)", copy=False)
    x_payment_number_1 = fields.Char(string="Pago N°1 (*)", copy=False)
    x_payment_receipt_1 = fields.Char(string="Recibo N°1 (*)", copy=False)
    x_payment_date_1 = fields.Date(string="Fecha de pago N°1 (*)", copy=False)

    x_capture_ov_error_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("error_precio_ceros", "Error en precio $0.0 (Ceros)"),
            ("error_recuperacion_medidas", "Error de recuperación en medidas"),
            ("error_cierre_venta", "Error de cierre de Venta"),
            ("otros", "Otros"),
        ],
        string="Tipo de Error (*)",
        default="select",
        copy=False,
    )

    x_capture_ov_sphere_od = fields.Char(string="Esfera OD (*)", copy=False)
    x_capture_ov_sphere_oi = fields.Char(string="Esfera OI (*)", copy=False)
    x_capture_ov_material_type = fields.Char(string="Tipo de Material (*)", copy=False)
    x_capture_ov_work_type = fields.Char(string="Tipo de Trabajo (*)", copy=False)
    x_capture_ov_discount_type = fields.Char(string="Tipo de Descuento (*)", copy=False)
    x_capture_ov_payment_type = fields.Char(string="Tipo de Pago (*)", copy=False)
    x_capture_ov_employee_number = fields.Char(string="N° de empleado (*)", copy=False)

    x_bag_number = fields.Char(string="Bolsa (*)", copy=False)
    x_bag_key = fields.Char(string="Clave de la bolsa (*)", copy=False)

    x_sap_branch_send = fields.Char(
        string="N° de sucursal SAP que envía traspaso (Ejem.: A303) (*)",
        copy=False,
    )
    x_sap_branch_receive = fields.Char(
        string="N° de sucursal SAP que recibe traspaso (Ejem.: A304) (*)",
        copy=False,
    )

    x_transport_number = fields.Char(string="N° de Transporte (*)", copy=False)
    x_transfer = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Traspaso (*)",
        default="select",
        copy=False,
    )

    x_order_without_packaging_pos_order = fields.Char(
        string="Pedido POS. (*)",
        copy=False,
    )
    x_order_without_packaging_date = fields.Date(string="Fecha (*)", copy=False)
    x_order_without_packaging_branch = fields.Char(
        string="Centro o Sucursal (*)",
        copy=False,
    )

    x_return_capture_error_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("error_precio_ceros", "Error en precio $0.0 (Ceros)"),
            ("error_recuperacion_medidas", "Error de recuperación en medidas"),
            ("error_cierre_venta", "Error de cierre de Venta"),
            ("otros", "Otros"),
        ],
        string="Tipo de Error (*)",
        default="select",
        copy=False,
    )

    x_return_capture_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("devolucion", "Devolucion"),
            ("garantia_10", "Garantia de 10"),
            ("retallado", "Retallado"),
        ],
        string="Tipo de Devolución (*)",
        default="select",
        copy=False,
    )

    x_return_capture_sale_order = fields.Char(
        string="Orden de Venta (*)",
        copy=False,
    )
    x_return_capture_order = fields.Char(string="Pedido (*)", copy=False)
    x_return_capture_cause_number = fields.Char(
        string="Causa Número (*)",
        copy=False,
    )

    x_rescue_client_name = fields.Char(string="Nombre del cliente (*)", copy=False)
    x_rescue_client_phone = fields.Char(
        string="Teléfono del cliente. (*)",
        copy=False,
    )
    x_rescue_sale_order = fields.Char(string="Orden de Venta (*)", copy=False)
    x_rescue_order_number = fields.Char(string="Pedido (*)", copy=False)
    x_rescue_client_email = fields.Char(
        string="Correo electronico del cliente (*)",
        copy=False,
    )

    x_online_fulfillment = fields.Char(string="Fullfilment (*)", copy=False)
    x_online_sale_date = fields.Date(string="Fecha de Venta (*)", copy=False)
    x_online_customer_email = fields.Char(
        string="Correo Electronico del Cliente",
        copy=False,
    )
    x_online_pos_order = fields.Char(string="Pedido POS. (*)", copy=False)
    x_online_customer_name = fields.Char(string="Nombre del Cliente (*)", copy=False)

    x_online_attachment_capture = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Adjuntar Captura cliente, producto recibido y Captura POS (*)",
        copy=False,
    )

    x_online_missing_product = fields.Char(
        string="Producto faltante (*)",
        copy=False,
    )
    x_online_requested_graduation = fields.Char(
        string="Graduación solicitada (*)",
        copy=False,
    )
    x_online_received_graduation = fields.Char(
        string="Graduación recibida (*)",
        copy=False,
    )
    x_online_return_sap_center = fields.Char(
        string="Centro SAP en el que el cliente devolverá (*)",
        copy=False,
    )
    x_online_return_bag_cedis = fields.Char(
        string="Bolsa en la que se retorna el pedido a CeDIs (*)",
        copy=False,
    )

    x_online_reported_customer_vtex = fields.Char(
        string="Vtex de cliente que reporta (*)",
        copy=False,
    )
    x_online_arrived_order_vtex = fields.Char(
        string="Vtex de pedido que le llegó al cliente (*)",
        copy=False,
    )
    x_online_received_order_name = fields.Char(
        string="A nombre de quién está el pedido recibido: (*)",
        copy=False,
    )
    x_online_received_product = fields.Char(
        string="Producto recibido (*)",
        copy=False,
    )

    x_online_return_reason = fields.Char(
        string="Razón por la que solicita devolución (*)",
        copy=False,
    )
    x_online_payment_reference = fields.Char(
        string="Referencia de pago (*)",
        copy=False,
    )

    x_online_payment_platform = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("mercado_pago", "Mercado pago"),
            ("kueskipay", "Kueskipay"),
            ("paypal", "Paypal"),
        ],
        string="Plataforma de pago (*)",
        default="select",
        copy=False,
    )

    x_online_correct_graduation = fields.Char(
        string="Graduación correcta (*)",
        copy=False,
    )
    x_online_promised_date = fields.Date(string="Fecha Promesa", copy=False)
    x_online_guide_number = fields.Char(string="N° de guía (*)", copy=False)
    x_online_receiver_name = fields.Char(
        string="Nombre de persona que puede recibir el paquete además del titular.",
        copy=False,
    )
    x_online_contact_phone = fields.Char(string="Teléfono de contacto", copy=False)

    x_online_client_phone = fields.Char(
        string="Teléfono del cliente. (*)",
        copy=False,
    )
    x_online_new_address = fields.Char(
        string="Nuevo domicilio completo.",
        copy=False,
    )
    x_online_additional_references = fields.Char(
        string="Referencias adicionales (*)",
        copy=False,
    )

    x_online_exam_sap_center = fields.Char(
        string="CentroSAP donde se realizó examen de la vista",
        copy=False,
    )
    x_online_exam_date = fields.Date(
        string="Fecha en que se realizó el examen de la vista",
        copy=False,
    )
    x_online_exam_employee_number = fields.Char(
        string="Número de empleado de quien realiza el examen de la vista",
        copy=False,
    )
    x_online_exam_employee_name = fields.Char(
        string="Nombre de quien realiza el examen de la vista",
        copy=False,
    )
    x_online_payment_method = fields.Char(string="Método de pago", copy=False)

    x_online_sphere_od = fields.Char(string="Esfera OD (*)", copy=False)
    x_online_sphere_oi = fields.Char(string="Esfera OI (*)", copy=False)
    x_online_cylinder_od = fields.Char(string="Cilindro OD", copy=False)
    x_online_cylinder_oi = fields.Char(string="Cilindro OI", copy=False)
    x_online_axis_od = fields.Char(string="Eje OD", copy=False)
    x_online_axis_oi = fields.Char(string="Eje OI", copy=False)
    x_online_ipd_od = fields.Char(
        string="Distancia interpupilar OD",
        copy=False,
    )
    x_online_ipd_oi = fields.Char(
        string="Distancia interpupilar OI",
        copy=False,
    )

    x_online_unshipped_order = fields.Char(string="Pedido (*)", copy=False)
    x_online_work_order_number = fields.Char(
        string="N° de Orden de Trabajo (*)",
        copy=False,
    )

    x_frame_search_sale_order = fields.Char(
        string="Orden de Venta (*)",
        copy=False,
    )
    x_frame_search_frame_code = fields.Char(
        string="Código de Armazón",
        copy=False,
    )
    x_frame_search_packaging_bag = fields.Char(
        string="Bolsa de embalaje",
        copy=False,
    )
    x_frame_search_shipping_date = fields.Date(
        string="Fecha de envío",
        copy=False,
    )
    x_frame_search_courier = fields.Char(
        string="Mensajería. (*)",
        copy=False,
    )

    x_frame_search_cause = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("perdida_laboratorio_essilor", "Pédida laboratorio Essilor"),
            ("perdida_laboratorio_local", "Pérdida laboratorio local"),
            ("perdida_mensajeria", "Pérdida mensajería"),
            ("dano_laboratorio_essilor", "Daño laboratorio Essilor"),
            ("dano_laboratorio_local", "Daño laboratorio local"),
            ("dano_mensajeria", "Daño mensajería"),
        ],
        string="Causa (*)",
        default="select",
        copy=False,
    )

    x_frame_search_other_specify = fields.Char(
        string="Otro (especificar) (*)",
        copy=False,
    )

    x_lc_recipe_name = fields.Char(
        string="Receta lente de Contacto",
        copy=False,
    )
    x_lc_ot_number = fields.Char(string="OT (*)", copy=False)
    x_lc_order_number = fields.Char(string="Pedido (*)", copy=False)

    x_lc_provider = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("alcon", "Alcon"),
            ("ciba", "Ciba"),
            ("novartis", "Novartis"),
            ("otro", "Otro"),
        ],
        string="Proveedor (*)",
        default="select",
        copy=False,
    )

    x_quality_order_number = fields.Char(string="Pedido (*)", copy=False)
    x_quality_customer_name = fields.Char(
        string="Nombre del Cliente (*)",
        copy=False,
    )
    x_quality_customer_phone = fields.Char(
        string="Teléfono del cliente. (*)",
        copy=False,
    )
    x_quality_shipping_bag = fields.Char(
        string="Bolsa de envío (*)",
        copy=False,
    )
    x_quality_courier_guide = fields.Char(
        string="Guia de Paquetería (*)",
        copy=False,
    )

    x_quality_evidence_attached = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Es necesario adjuntar imagen como evidencia. (*)",
        copy=False,
    )

    x_medallia_employee_number = fields.Char(
        string="N° de empleado (*)",
        copy=False,
    )
    x_medallia_employee_name = fields.Char(
        string="Nombre del empleado (*)",
        copy=False,
    )

    x_bag_arrival = fields.Char(string="Bolsa de arribo (*)", copy=False)
    x_delivery_oc = fields.Char(string="Entrega | OC", copy=False)
    x_paq_pos_order = fields.Char(string="Pedido POS. (*)", copy=False)

    x_shipping_noncompliance_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("visita", "Visita"),
            ("recoleccion", "Recolección"),
        ],
        string="Tipo (*)",
        default="select",
        copy=False,
    )

    x_shipping_assigned_courier = fields.Char(
        string="Mensajería asignada (*)",
        copy=False,
    )
    x_shipping_arrival_bag = fields.Char(
        string="Bolsa de arribo (*)",
        copy=False,
    )
    x_shipping_guide_number_detail = fields.Char(
        string="N° de guía (*)",
        copy=False,
    )
    x_shipping_content_detail = fields.Char(
        string="Detalle de contenido (*)",
        copy=False,
    )

    x_shipping_photo_evidence_confirmed = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Evidencia fotográfica (Confirmar) (*)",
        copy=False,
    )

    x_shipping_unreceived_pos_order = fields.Char(
        string="Pedido POS. (*)",
        copy=False,
    )
    x_shipping_unreceived_arrival_bag = fields.Char(
        string="Bolsa de arribo (*)",
        copy=False,
    )
    x_shipping_unreceived_transport = fields.Char(
        string="Transporte (*)",
        copy=False,
    )

    x_shipping_lab_followup_pos_order = fields.Char(
        string="Pedido POS. (*)",
        copy=False,
    )

    x_shipping_extraordinary_pos_order = fields.Char(
        string="Pedido POS. (*)",
        copy=False,
    )
    x_shipping_extraordinary_sap_center = fields.Char(
        string="Centro SAP a donde se redirecciona la entrega (*)",
        copy=False,
    )

    x_shipping_extraordinary_manager_authorization = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Autorización de gerente (Confirmar) (*)",
        copy=False,
    )

    x_shipping_missing_accessory_order = fields.Char(
        string="Pedido. (*)",
        copy=False,
    )
    x_shipping_missing_accessory_bag = fields.Char(
        string="Bolsa (*)",
        copy=False,
    )
    x_shipping_missing_accessory_brand = fields.Char(
        string="Marca del armazón (*)",
        copy=False,
    )
    x_shipping_missing_accessory_arrival_date = fields.Date(
        string="Fecha de llegada a sucursal (*)",
        copy=False,
    )

    x_shipping_missing_accessory_supplier = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("fulljob", "Fulljob"),
            ("surte_almacen", "Surte almacén"),
            ("surte_proveedor", "Surte proveedor"),
            ("surte_optica", "Surte óptica"),
            ("airborn", "Airborn"),
        ],
        string="¿Quién surte el armazón? (*)",
        default="select",
        copy=False,
    )

    x_shipping_missing_accessory_cloth = fields.Boolean(
        string="Paño",
        copy=False,
    )
    x_shipping_missing_accessory_case = fields.Boolean(
        string="Estuche",
        copy=False,
    )
    x_shipping_missing_accessory_clipon = fields.Boolean(
        string="Clip on",
        copy=False,
    )
    x_shipping_missing_accessory_certificate = fields.Boolean(
        string="Certificado de autenticidad",
        copy=False,
    )

    x_prev_guide_number = fields.Char(string="N° de guía (*)", copy=False)

    x_prev_courier_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("estafeta", "Estafeta"),
            ("dhl", "DHL"),
            ("mensajeria_interna", "Mensajería interna"),
            ("otros", "Otros"),
        ],
        string="Mensajería (*)",
        default="select",
        copy=False,
    )

    x_prev_photo_evidence_confirm = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Evidencia fotográfica (Confirmar) (*)",
        copy=False,
    )

    x_report_whatsapp_date = fields.Date(
        string="Fecha de reporte por WhatsApp",
        copy=False,
    )
    x_report_marketing_date = fields.Date(
        string="Fecha de reporte Marketing producto",
        copy=False,
    )

    x_report_attached = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="Confirmar que se adjuntó el reporte",
        copy=False,
    )

    x_supply_material_code = fields.Char(
        string="Código del material",
        copy=False,
    )
    x_supply_material_description = fields.Char(
        string="Descripción del Material (*)",
        copy=False,
    )
    x_supply_quantity = fields.Char(string="Cantidad (*)", copy=False)

    x_supply_unit_measure = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("pzs", "Pzs"),
            ("lto", "Lto"),
            ("hojas", "Hojas"),
            ("cuadernillo", "Cuadernillo"),
        ],
        string="Unidad de medida",
        default="select",
        copy=False,
    )

    x_supply_center = fields.Char(string="Centro (*)", copy=False)

    x_supply_manager_approval_attached = fields.Selection(
        [
            ("si", "Sí"),
            ("no", "No"),
        ],
        string="¿Se tiene VoBo de gerente distrital? Adjuntar",
        copy=False,
    )

    x_lab_local_pos_order = fields.Char(
        string="Pedido POS. (*)",
        copy=False,
    )
    x_lab_local_promise_date = fields.Date(
        string="Fecha Promesa",
        copy=False,
    )
    x_lab_local_name = fields.Char(
        string="Laboratorio local",
        copy=False,
    )

    x_supply_sku_code = fields.Char(
        string="Codigo SKU (*)",
        copy=False,
    )

    x_supply_frame_type = fields.Selection(
        [
            ("select", "-- seleccionar --"),
            ("abasto_armazones", "Abasto de armazones"),
        ],
        string="*",
        default="select",
        copy=False,
    )

    x_supply_frame_brand_basic = fields.Char(
        string="Marca con Base al Cuadro Basico (*)",
        copy=False,
    )
    x_supply_return_folio = fields.Char(
        string="Folio de la Devolución (*)",
        copy=False,
    )

    @api.depends("x_category_id")
    def _compute_x_is_facturacion_reenvio(self):
        target = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_facturacion_reenvio_pdf_xml",
            raise_if_not_found=False,
        )
        target_id = target.id if target else False
        for rec in self:
            rec.x_is_facturacion_reenvio = bool(
                target_id and rec.x_category_id.id == target_id
            )

    @api.depends("x_category_id")
    def _compute_x_devolucion_category_flags(self):
        tc_db_category = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_devoluciones_reales_tarjeta_credito_debito",
            raise_if_not_found=False,
        )
        cash_order_category = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_devoluciones_reales_efectivo_orden_pago",
            raise_if_not_found=False,
        )
        cash_transfer_category = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_devoluciones_reales_efectivo_transferencia",
            raise_if_not_found=False,
        )

        tc_db_id = tc_db_category.id if tc_db_category else False
        cash_order_id = cash_order_category.id if cash_order_category else False
        cash_transfer_id = cash_transfer_category.id if cash_transfer_category else False

        for rec in self:
            rec.x_is_dev_real_tc_db = bool(
                tc_db_id and rec.x_category_id.id == tc_db_id
            )
            rec.x_is_dev_real_cash_order = bool(
                cash_order_id and rec.x_category_id.id == cash_order_id
            )
            rec.x_is_dev_real_cash_transfer = bool(
                cash_transfer_id and rec.x_category_id.id == cash_transfer_id
            )

    @api.depends("x_category_id")
    def _compute_x_category_flags_extra(self):
        receta_lc_category = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_receta_lc_lente_contacto",
            raise_if_not_found=False,
        )
        papeleria_category = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_papeleria_seguimiento",
            raise_if_not_found=False,
        )
        resurtido_category = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_resurtido_consumibles_seguimiento",
            raise_if_not_found=False,
        )

        receta_lc_id = receta_lc_category.id if receta_lc_category else False
        papeleria_id = papeleria_category.id if papeleria_category else False
        resurtido_id = resurtido_category.id if resurtido_category else False

        for rec in self:
            rec.x_is_receta_lc = bool(
                receta_lc_id and rec.x_category_id.id == receta_lc_id
            )
            rec.x_is_papeleria_seguimiento = bool(
                papeleria_id and rec.x_category_id.id == papeleria_id
            )
            rec.x_is_resurtido_consumibles_seguimiento = bool(
                resurtido_id and rec.x_category_id.id == resurtido_id
            )

    @api.depends("x_category_id", "x_subcategory_code")
    def _compute_x_view_context_flags(self):
        category_online_sin_entregar = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_fullfilment_online_sin_entregar",
            raise_if_not_found=False,
        )
        category_receta_lc = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_receta_lc_lente_contacto",
            raise_if_not_found=False,
        )
        category_papeleria = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_papeleria_seguimiento",
            raise_if_not_found=False,
        )
        category_resurtido = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_resurtido_consumibles_seguimiento",
            raise_if_not_found=False,
        )

        online_id = category_online_sin_entregar.id if category_online_sin_entregar else False
        receta_id = category_receta_lc.id if category_receta_lc else False
        papeleria_id = category_papeleria.id if category_papeleria else False
        resurtido_id = category_resurtido.id if category_resurtido else False

        for rec in self:
            rec.x_is_atraso_lente_contacto_online = bool(
                rec.x_subcategory_code == "atraso_lente_contacto"
                and online_id
                and rec.x_category_id.id == online_id
            )
            rec.x_is_atraso_lente_contacto_receta = bool(
                rec.x_subcategory_code == "atraso_lente_contacto"
                and receta_id
                and rec.x_category_id.id == receta_id
            )
            rec.x_is_seguimiento_solicitud_papeleria = bool(
                rec.x_subcategory_code == "seguimiento_solicitud"
                and papeleria_id
                and rec.x_category_id.id == papeleria_id
            )
            rec.x_is_seguimiento_solicitud_resurtido = bool(
                rec.x_subcategory_code == "seguimiento_solicitud"
                and resurtido_id
                and rec.x_category_id.id == resurtido_id
            )

    def _is_empty_required_value(self, value):
        if value in (False, None, "", []):
            return True
        if isinstance(value, str) and not value.strip():
            return True
        if value == "select":
            return True
        return False

    def _get_missing_required_field_labels(self, field_names):
        self.ensure_one()
        missing = []
        for field_name in field_names:
            field = self._fields.get(field_name)
            if not field:
                continue
            value = self[field_name]
            if self._is_empty_required_value(value):
                missing.append(field.string or field_name)
        return missing

    def _get_required_fields_error(self, field_names, section_name):
        self.ensure_one()
        missing = self._get_missing_required_field_labels(field_names)
        if not missing:
            return False
        return _(
            "Para la sección '%s' faltan los siguientes campos obligatorios:\n- %s"
        ) % (section_name, "\n- ".join(missing))

    def _validate_required_fields(self, field_names, section_name):
        for rec in self:
            error_message = rec._get_required_fields_error(field_names, section_name)
            if error_message:
                raise ValidationError(error_message)

    def _get_dynamic_required_fields_error(self):
        self.ensure_one()
        code = self.x_subcategory_code or ""

        if self.x_is_atraso_lente_contacto_online:
            return self._get_required_fields_error(
                ["x_online_pos_order", "x_online_work_order_number"],
                "Atraso lente de contacto - Online",
            )

        if self.x_is_atraso_lente_contacto_receta:
            return self._get_required_fields_error(
                ["x_lc_recipe_name", "x_lc_ot_number", "x_lc_order_number", "x_lc_provider"],
                "Atraso lente de contacto - Receta LC",
            )

        if self.x_is_seguimiento_solicitud_resurtido:
            return self._get_required_fields_error(
                [
                    "x_supply_material_code",
                    "x_supply_material_description",
                    "x_supply_quantity",
                    "x_supply_unit_measure",
                    "x_supply_center",
                    "x_supply_manager_approval_attached",
                ],
                "Seguimiento de solicitud - Resurtido de consumibles",
            )

        if self.x_is_seguimiento_solicitud_papeleria:
            return self._get_required_fields_error(
                [
                    "x_supply_material_description",
                    "x_supply_quantity",
                    "x_supply_unit_measure",
                    "x_supply_center",
                    "x_supply_manager_approval_attached",
                ],
                "Seguimiento de solicitud - Papelería",
            )

        if code == "micas_sin_cortar":
            return self._get_required_fields_error(
                [
                    "x_order_number",
                    "x_bag",
                    "x_customer_warehouse",
                    "x_authorized_by",
                    "x_lab_indicated",
                    "x_order_type",
                ],
                "Micas sin cortar",
            )

        if code == "trabajos_atrasados":
            return self._get_required_fields_error(
                [
                    "x_job_type",
                    "x_original_order_number",
                    "x_order_number",
                    "x_customer_warehouse",
                    "x_lab_indicated",
                    "x_shipping_guide_number",
                    "x_frame_bag_number",
                    "x_order_type",
                ],
                "Trabajos atrasados",
            )

        if code == "correo_electronico":
            return self._get_required_fields_error(
                ["x_branch_email", "x_email_issue_type_2", "x_contact_number"],
                "Correo electrónico",
            )

        if code == "equipo_computo":
            return self._get_required_fields_error(
                [
                    "x_internal_folio_number",
                    "x_equipment_type",
                    "x_model_or_brand",
                    "x_serial_number",
                    "x_fixed_asset_number",
                    "x_shipping_guide",
                    "x_courier",
                ],
                "Equipo de cómputo",
            )

        if code == "problema_pagos_anticipos":
            return self._get_required_fields_error(
                [
                    "x_payment_center",
                    "x_payment_pos_order",
                    "x_payment_sale_date",
                    "x_payment_sale_total",
                    "x_payment_number_1",
                    "x_payment_receipt_1",
                    "x_payment_date_1",
                ],
                "Problema de pagos (anticipos)",
            )

        if code == "pedidos_incompletos":
            return self._get_required_fields_error(
                [
                    "x_online_fulfillment",
                    "x_online_sale_date",
                    "x_online_customer_email",
                    "x_online_pos_order",
                    "x_online_customer_name",
                    "x_online_missing_product",
                    "x_online_attachment_capture",
                ],
                "Pedidos incompletos",
            )

        if code == "graduacion_incorrecta":
            return self._get_required_fields_error(
                [
                    "x_online_fulfillment",
                    "x_online_sale_date",
                    "x_online_customer_email",
                    "x_online_pos_order",
                    "x_online_customer_name",
                    "x_online_requested_graduation",
                    "x_online_received_graduation",
                    "x_online_attachment_capture",
                    "x_online_return_sap_center",
                    "x_online_return_bag_cedis",
                ],
                "Pedidos con graduación incorrecta",
            )

        return False

    @api.constrains(
        "x_subcategory_code",
        "x_category_id",
        "x_subcategory_id",
        "x_order_type",
        "x_is_receta_lc",
        "x_is_dev_real_tc_db",
        "x_is_dev_real_cash_order",
        "x_is_dev_real_cash_transfer",
        "x_is_papeleria_seguimiento",
        "x_is_resurtido_consumibles_seguimiento",
        "x_is_atraso_lente_contacto_online",
        "x_is_atraso_lente_contacto_receta",
        "x_is_seguimiento_solicitud_papeleria",
        "x_is_seguimiento_solicitud_resurtido",
        "x_lc_recipe_name",
        "x_lc_ot_number",
        "x_lc_order_number",
        "x_lc_provider",
        "x_online_fulfillment",
        "x_online_sale_date",
        "x_online_customer_email",
        "x_online_pos_order",
        "x_online_customer_name",
        "x_online_missing_product",
        "x_online_requested_graduation",
        "x_online_received_graduation",
        "x_online_return_sap_center",
        "x_online_return_bag_cedis",
        "x_online_work_order_number",
        "x_online_attachment_capture",
        "x_payment_center",
        "x_payment_pos_order",
        "x_payment_sale_date",
        "x_payment_sale_total",
        "x_payment_number_1",
        "x_payment_receipt_1",
        "x_payment_date_1",
        "x_order_number",
        "x_bag",
        "x_customer_warehouse",
        "x_authorized_by",
        "x_lab_indicated",
        "x_job_type",
        "x_original_order_number",
        "x_shipping_guide_number",
        "x_frame_bag_number",
        "x_branch_email",
        "x_email_issue_type_2",
        "x_contact_number",
        "x_internal_folio_number",
        "x_equipment_type",
        "x_model_or_brand",
        "x_serial_number",
        "x_fixed_asset_number",
        "x_shipping_guide",
        "x_courier",
        "x_supply_material_code",
        "x_supply_material_description",
        "x_supply_quantity",
        "x_supply_unit_measure",
        "x_supply_center",
        "x_supply_manager_approval_attached",
    )
    def _check_dynamic_required_fields(self):
        for rec in self:
            error_message = rec._get_dynamic_required_fields_error()
            if error_message:
                raise ValidationError(error_message)
