from odoo import api, fields, models


class HelpdeskTicket(models.Model):
    _inherit = "helpdesk.ticket"

    x_general_description = fields.Char(string="Descripción General", required=True)
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

    x_subcategory_code = fields.Char(related="x_subcategory_id.code", store=True, readonly=True)

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
    x_lab_indicated = fields.Char(string="LAB indicado en portal de seguimiento de trabajos", copy=False)

    x_shipping_guide_number = fields.Char(string="Número de guía de envío de armazón", copy=False)
    x_frame_bag_number = fields.Char(string="Número de bolsa de envío de armazón", copy=False)
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
    x_email_issue_type_2 = fields.Char(string="Tipo de Error, Envio o Recepción",copy=False)
    x_contact_number = fields.Char(string="Número de contacto", copy=False)

    x_internal_folio_number = fields.Char(string="Número de folio interno.", copy=False)

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

    x_printer_model = fields.Char(
        string="Modelo de impresora",
        copy=False,
    )

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


    x_is_facturacion_reenvio = fields.Boolean(compute="_compute_x_is_facturacion_reenvio", store=False)
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
    x_refac_order_number = fields.Char(string="Pedido (*)", copy=False)
    x_refac_sale_order = fields.Char(string="Orden de Venta (*)", copy=False)
    x_refac_legal_name = fields.Char(string="Nombre o denominación social (*)", copy=False)
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

    x_card_number_16_digits = fields.Char(string="N° completo de la tarjeta 16 dígitos (*)", copy=False)
    x_card_expiration_mmaa = fields.Char(string="Fecha de Vencimiento MMAA (*)", copy=False)
    x_card_authorization_number = fields.Char(string="Número de Autorización (*)", copy=False)
    x_card_holder_relationship = fields.Char(string="Parentesco Titular de la tarjeta con nombre r (*)", copy=False)

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

    x_duplicate_affiliation = fields.Char(string="Afiliación (Tarjeta y duplicados)", copy=False)
    x_duplicate_tracking_id = fields.Char(string="No. de seguimiento o ID (Tarjeta y duplicados)", copy=False)
    x_duplicate_internal_terminal = fields.Char(string="Terminal Interna (Tarjeta y duplicados)", copy=False)

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
    x_cash_banamex_branch_number = fields.Char(string="Número de sucursal Banamex (*)", copy=False)
    x_cash_beneficiary_name = fields.Char(string="Nombre del beneficiario (*)", copy=False)
    x_transfer_clabe_18 = fields.Char(string="Cuenta Clabe 18 dígitos (*)", copy=False)
    x_transfer_account_holder = fields.Char(string="Titular de la cuenta (*)", copy=False)
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

    x_eval_policies_employee_name = fields.Char(string="Nombre del empleado (*)", copy=False)
    x_eval_policies_employee_number = fields.Char(string="N° de empleado (*)", copy=False)
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
            rec.x_is_dev_real_tc_db = bool(tc_db_id and rec.x_category_id.id == tc_db_id)
            rec.x_is_dev_real_cash_order = bool(cash_order_id and rec.x_category_id.id == cash_order_id)
            rec.x_is_dev_real_cash_transfer = bool(cash_transfer_id and rec.x_category_id.id == cash_transfer_id)

    @api.depends("x_category_id")
    def _compute_x_is_facturacion_reenvio(self):
        target = self.env.ref(
            "helpdesk_custom_datos.helpdesk_ticket_category_facturacion_reenvio_pdf_xml",
            raise_if_not_found=False,
        )
        target_id = target.id if target else False
        for rec in self:
            rec.x_is_facturacion_reenvio = bool(target_id and rec.x_category_id.id == target_id)