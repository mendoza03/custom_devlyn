from odoo import api, models, fields
import base64
import mimetypes
from odoo.tools.mimetypes import guess_mimetype


class CrmLeadDocument(models.Model):
    _name = 'crm.lead.document'
    _description = 'CRM Lead Document'

    lead_id = fields.Many2one('crm.lead', string='Lead', ondelete='cascade')
    condominium_id = fields.Many2one('condominium.worksite', string="Condominium")
    project_id = fields.Many2one('project.worksite', string="Development")
    name = fields.Char(string='Document Name', required=True)

    file = fields.Binary(string='File', compute="_compute_file", inverse="_inverse_file", store=False)
    document_id = fields.Many2one('documents.document', string='Archivo en Documentos')
    file_name = fields.Char(string='File Name')

    user_ids = fields.Many2many('res.users', string="Users")
    partner_ids = fields.Many2many('res.partner', string="partner")

    document_type = fields.Selection([
        ('master', 'Master plan'), ('rules', 'Rules'), ('sunning', 'Sunning'),
        ('location', 'Location'), ('procedure', 'payment procedure'),
        ('flyers', 'Flyers'), ('amenities', 'Technical specifications amenities'),
        ('tour', 'Virtual tour'), ('videos', 'Videos'), ('work', 'Work progress'),
        ('contract', 'Draft contract'), ('availability', 'Availability'),
        ('presentation', 'Presentation'),
    ], string='Document type', required=True)

    filetype = fields.Selection(
        [('pdf', 'PDF'), ('image', 'Image'), ('other', 'Other')],
        compute="_compute_filetype",
        store=True
    )

    is_saved = fields.Boolean(compute="_compute_is_saved", store=False)

    file_preview_html = fields.Html(
        string="Vista previa (inline)",
        compute="_compute_file_preview_html",
        sanitize=False,
        store=False
    )

    def _compute_is_saved(self):
        for rec in self:
            rec.is_saved = bool(rec.id)

    def _get_document_binary(self):
        self.ensure_one()
        doc = self.document_id
        if not doc:
            return False

        attachment = getattr(doc, 'attachment_id', False)
        if attachment and getattr(attachment, 'datas', False):
            return attachment.datas

        if hasattr(doc, 'datas') and getattr(doc, 'datas', False):
            return doc.datas

        return False

    def _set_document_binary(self, value):
        self.ensure_one()
        doc = self.document_id
        if not doc:
            return

        attachment = getattr(doc, 'attachment_id', False)
        if attachment and hasattr(attachment, 'write'):
            attachment.write({'datas': value})
            return

        if hasattr(doc, 'write') and hasattr(doc, 'datas'):
            doc.write({'datas': value})

    @api.depends(
        'file_name',
        'document_id',
        'document_id.name',
        'document_id.attachment_id',
        'document_id.attachment_id.datas',
    )
    def _compute_filetype(self):
        for rec in self:
            rec.filetype = 'other'
            fname = (rec.file_name or (rec.document_id.name if rec.document_id else '') or '').lower()
            ext = fname.split('.')[-1] if '.' in fname else ''

            if ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                rec.filetype = 'image'
                continue
            if ext == 'pdf':
                rec.filetype = 'pdf'
                continue

            try:
                raw = rec._get_document_binary() or rec.file
                if raw:
                    if isinstance(raw, str):
                        raw = raw.encode('utf-8')
                    mime = guess_mimetype(base64.b64decode(raw))
                    if mime and mime.startswith('image/'):
                        rec.filetype = 'image'
                    elif mime == 'application/pdf':
                        rec.filetype = 'pdf'
            except Exception:
                pass

    @api.depends('file', 'file_name')
    def _compute_file_preview_html(self):
        for rec in self:
            rec.file_preview_html = ""
            if rec.id:
                continue
            if not rec.file:
                continue

            fname = (rec.file_name or '').lower()
            ext = fname.split('.')[-1] if '.' in fname else ''
            try:
                fb = rec.file
                if isinstance(fb, str):
                    fb = fb.encode('utf-8')
                base64_bytes = base64.b64encode(base64.b64decode(fb)).decode('utf-8')
            except Exception:
                continue

            if ext == 'pdf':
                rec.file_preview_html = (
                    f'<embed src="data:application/pdf;base64,{base64_bytes}" '
                    f'width="100%" height="600px" type="application/pdf" />'
                )
            elif ext in ('jpg', 'jpeg', 'png', 'gif', 'webp'):
                mime = 'image/jpeg' if ext in ('jpg', 'jpeg') else ('image/png' if ext == 'png' else f'image/{ext}')
                rec.file_preview_html = (
                    f'<img src="data:{mime};base64,{base64_bytes}" '
                    f'style="max-width:100%; max-height:500px;" />'
                )
            else:
                rec.file_preview_html = (
                    f'<p>No preview available for this file type.</p>'
                    f'<a download="{rec.file_name or "archivo"}" '
                    f'href="data:application/octet-stream;base64,{base64_bytes}">Descargar archivo</a>'
                )

    @api.onchange('file', 'file_name')
    def _onchange_complete_filename_and_preview(self):
        for rec in self:
            if rec.file and not rec.file_name:
                try:
                    raw = base64.b64decode(rec.file or b'')
                    mime = guess_mimetype(raw)
                    ext = mimetypes.guess_extension(mime) or '.bin'
                    rec.file_name = f"archivo{ext}"
                except Exception:
                    pass
            rec._compute_file_preview_html()
            rec._compute_filetype()

    def _compute_file(self):
        for rec in self:
            rec.file = rec._get_document_binary() if rec.document_id else False

    def _inverse_file(self):
        for rec in self:
            if not rec.file:
                continue

            if rec.project_id:
                folder_id = rec.project_id.carpet_id.id or False
            else:
                folder_id = rec.condominium_id.carpet_id.id if rec.condominium_id else False

            filename = rec.file_name or rec.name or 'archivo'
            if '.' not in (filename or ''):
                try:
                    raw = base64.b64decode(rec.file or b'')
                    mime = guess_mimetype(raw)
                    ext = mimetypes.guess_extension(mime) or ''
                    filename = f"{filename}{ext}"
                except Exception:
                    pass

            doc_vals = {
                'name': filename,
                'datas': rec.file,
                'res_model': 'crm.lead.document',
                'res_id': rec.id,
                'folder_id': folder_id,
                "owner_id": self.env.ref('base.user_root').id,
                "type": "binary",
                "access_internal": "view",
            }
            doc = self.env['documents.document'].create(doc_vals)
            rec.document_id = doc
            rec.file_name = filename

    def _compute_file_name(self):
        for rec in self:
            rec.file_name = rec.document_id.name if rec.document_id else False

    def _inverse_file_name(self):
        for rec in self:
            if rec.document_id and rec.file_name:
                rec.document_id.name = rec.file_name