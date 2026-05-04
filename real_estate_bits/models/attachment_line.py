from odoo.exceptions import UserError, ValidationError
from odoo import _, api, fields, models, tools

from odoo.addons.web_editor.tools import get_video_embed_code, get_video_thumbnail


class AttachmentLine(models.Model):
    _name = "attachment.line"
    _description = "Attachment Lines"
    _inherit = ["image.mixin"]
    _order = "sequence, id"

    name = fields.Char("Name", required=True)
    sequence = fields.Integer(default=10, index=True)
    mimetype = fields.Char(compute="_compute_mimetype")

    is_visible = fields.Boolean(default=True)

    filetype = fields.Selection([('pdf', 'PDF'), ('image', 'Image')], default='image', required=True)

    project_worksite_id = fields.Many2one("project.worksite", ondelete="cascade", readonly=True)
    condominium_worksite_id = fields.Many2one("condominium.worksite", ondelete="cascade", readonly=True)
    project_plan_id = fields.Many2one("project.worksite", ondelete="cascade", readonly=True)
    property_id = fields.Many2one("product.template", "Property", ondelete="cascade", readonly=True)
    # pro_brochure_id = fields.Many2one("product.template", "Property Brochure", ondelete="cascade", readonly=True)
    contract_id = fields.Many2one("property.contract", "Contract", ondelete="cascade", readonly=True)

    is_brochure = fields.Boolean()

    file = fields.Binary("File")
    image_1920 = fields.Image()
    video_url = fields.Char("Video URL", help="URL of a video for showcasing your property.")
    embed_code = fields.Char(compute="_compute_embed_code")
    can_image_1024_be_zoomed = fields.Boolean("Can Image 1024 be zoomed",
                                              compute="_compute_can_image_1024_be_zoomed", store=True)

    def _compute_mimetype(self):
        for rec in self:
            if rec.filetype and rec.filetype != 'image':
                rec.mimetype = 'application/pdf'
            else:
                rec.mimetype = False

    @api.depends("image_1920", "image_1024")
    def _compute_can_image_1024_be_zoomed(self):
        for image in self:
            image.can_image_1024_be_zoomed = (
                    image.image_1920 and tools.is_image_size_above(image.image_1920, image.image_1024))

    @api.depends("video_url")
    def _compute_embed_code(self):
        for image in self:
            image.embed_code = get_video_embed_code(image.video_url)

    @api.constrains("video_url")
    def _check_valid_video_url(self):
        for image in self:
            if image.video_url and not image.embed_code:
                raise ValidationError(
                    _(
                        "Provided video URL for '%s' is not valid. Please enter a valid video URL.",
                        image.name,
                    )
                )
