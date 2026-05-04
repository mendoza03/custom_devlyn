# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError


class CondominiumInherit(models.Model):
    _inherit = "condominium.worksite"


    documents_master = fields.One2many('crm.lead.document', 'condominium_id',
                                       domain=[('document_type', '=', 'master')])
    documents_rules = fields.One2many('crm.lead.document', 'condominium_id',
                                      domain=[('document_type', '=', 'rules')])
    documents_sunning = fields.One2many('crm.lead.document', 'condominium_id',
                                        domain=[('document_type', '=', 'sunning')])
    documents_location = fields.One2many('crm.lead.document', 'condominium_id',
                                         domain=[('document_type', '=', 'location')])
    documents_procedure = fields.One2many('crm.lead.document', 'condominium_id',
                                          domain=[('document_type', '=', 'procedure')])
    documents_presentation = fields.One2many('crm.lead.document', 'condominium_id',
                                             domain=[('document_type', '=', 'presentation')])
    documents_flyers = fields.One2many('crm.lead.document', 'condominium_id',
                                       domain=[('document_type', '=', 'flyers')])
    documents_amenities = fields.One2many('crm.lead.document', 'condominium_id',
                                          domain=[('document_type', '=', 'amenities')])
    documents_tour = fields.One2many('crm.lead.document', 'condominium_id',
                                     domain=[('document_type', '=', 'tour')])
    documents_videos = fields.One2many('crm.lead.document', 'condominium_id',
                                       domain=[('document_type', '=', 'videos')])
    documents_work = fields.One2many('crm.lead.document', 'condominium_id',
                                     domain=[('document_type', '=', 'work')])
    documents_contract = fields.One2many('crm.lead.document', 'condominium_id',
                                         domain=[('document_type', '=', 'contract')])
    documents_availability = fields.One2many('crm.lead.document', 'condominium_id',
                                             domain=[('document_type', '=', 'availability')])

    carpet_id = fields.Many2one('documents.document', string='Document', ondelete='cascade')

    url = fields.Char(string="URL")
    url_inter = fields.Char(string="URL Intera")

    no_config_product_count = fields.Integer(
        string="No Config Products",
        compute="_compute_no_config_product_count",
        readonly=True,
    )

    total_area = fields.Float(
        string="Area total",
        compute="_compute_total_area_custom",
        store=False,
    )

    @api.depends('property_ids', 'property_ids.property_area', 'property_ids.condominium_worksite_id')
    def _compute_total_area_custom(self):
        ProductTmpl = self.env['product.template'].sudo()
        for record in self:
            products = ProductTmpl.search([
                ('condominium_worksite_id', '=', record.id),
            ])
            record.total_area = sum(products.mapped('property_area') or [])

    def _get_no_config_products_domain(self):
        self.ensure_one()
        # Adjust this if your linkage field name is different
        return [
            ("condominium_worksite_id", "=", self.id),
            ("no_config", "=", True),
        ]

    def _compute_no_config_product_count(self):
        ProductTmpl = self.env["product.template"].sudo()
        for rec in self:
            rec.no_config_product_count = ProductTmpl.search_count(
                rec._get_no_config_products_domain()
            )

    def action_open_no_config_products(self):
        self.ensure_one()

        action = self.env.ref(
            "real_estate_bits.action_property_act_window"
        ).read()[0]

        action["domain"] = [
            ("condominium_worksite_id", "=", self.id),
            ("no_config", "=", True),
        ]

        action["context"] = {
            "default_no_config": True,
            "default_condominium_worksite_id": self.id,
        }

        return action

    def action_open_url(self):
        for record in self:
            if not record.url:
                raise UserError(_("No URL."))
            url = record.url
            if not url.startswith(('http://', 'https://')):
                url = f'https://{url}'
            return {
                'type': 'ir.actions.act_url',
                'url': url,
                'target': 'new',
            }

    @api.model_create_multi
    def create(self, vals):
        clusters = super().create(vals)
        for cluster in clusters:
            doc_id = self.env['documents.document'].create({
                'name': cluster.name,
                "owner_id": self.env.ref('base.user_root').id,
                "type": "folder",
                "access_internal": "view",
            })
            if cluster.parent_id:
                if cluster.parent_id.carpet_id:
                    doc_id.update({
                        'folder_id': cluster.parent_id.carpet_id.id
                    })
            cluster.update({
                'carpet_id': doc_id.id,
            })
        return clusters
