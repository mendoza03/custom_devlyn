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