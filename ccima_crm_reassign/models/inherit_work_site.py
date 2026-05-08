# -*- coding: utf-8 -*-
from odoo import models, fields, api, _
from odoo.exceptions import UserError
import base64

class WorksiteInherit(models.Model):
    _inherit = "project.worksite"


    documents_master = fields.One2many('crm.lead.document', 'project_id',
                                       domain=[('document_type', '=', 'master')])
    documents_rules = fields.One2many('crm.lead.document', 'project_id',
                                      domain=[('document_type', '=', 'rules')])
    documents_sunning = fields.One2many('crm.lead.document', 'project_id',
                                        domain=[('document_type', '=', 'sunning')])
    documents_location = fields.One2many('crm.lead.document', 'project_id',
                                         domain=[('document_type', '=', 'location')])
    documents_procedure = fields.One2many('crm.lead.document', 'project_id',
                                          domain=[('document_type', '=', 'procedure')])
    documents_presentation = fields.One2many('crm.lead.document', 'project_id',
                                             domain=[('document_type', '=', 'presentation')])
    documents_flyers = fields.One2many('crm.lead.document', 'project_id',
                                       domain=[('document_type', '=', 'flyers')])
    documents_amenities = fields.One2many('crm.lead.document', 'project_id',
                                          domain=[('document_type', '=', 'amenities')])
    documents_tour = fields.One2many('crm.lead.document', 'project_id',
                                     domain=[('document_type', '=', 'tour')])
    documents_videos = fields.One2many('crm.lead.document', 'project_id',
                                       domain=[('document_type', '=', 'videos')])
    documents_work = fields.One2many('crm.lead.document', 'project_id',
                                     domain=[('document_type', '=', 'work')])
    documents_contract = fields.One2many('crm.lead.document', 'project_id',
                                         domain=[('document_type', '=', 'contract')])
    documents_availability = fields.One2many('crm.lead.document', 'project_id',
                                             domain=[('document_type', '=', 'availability')])

    carpet_id = fields.Many2one('documents.document', string='Document', ondelete='cascade')

    url = fields.Char(string="URL")
    url_inter = fields.Char(string="URL")


    analytic_line_ids = fields.One2many(
        comodel_name='account.analytic.line',
        inverse_name='worksite_id',
        string='Analytic Lines',
    )

    analytic_distribution = fields.Json(
        string='Analytic Distribution',
        inverse='_inverse_analytic_distribution',
    )

    analytic_precision = fields.Integer(
        string='Analytic Precision',
        default=2,
    )

    related_public_deeds = fields.Char(string="Related Public Deeds")
    recent_public_deed = fields.Char(string="Recent Public Deed")
    otherwise_clause = fields.Char(string="Otherwise Clause")
    compliance_clause = fields.Char(string="If Payment is Made According to the Scheme and All Receipts are Delivered")

    company_legal_name = fields.Char(string="Legal Name")
    company_legal_rep = fields.Char(string="Legal Representative")
    company_constitutive_act = fields.Char(string="Constitutive Deed")
    company_notary = fields.Char(string="Current Notary")
    company_address = fields.Char(string="Address")
    company_email = fields.Char(string="Email")

    goal = fields.Float(string="Meta")

    total_goal = fields.Float(string="Total goal", compute="_compute_sales_kpis", store=False)
    total_sell = fields.Float(string="Total sell", compute="_compute_sales_kpis", store=False)
    sell = fields.Float(string="Sell", compute="_compute_sales_kpis", store=False)
    to_sell = fields.Float(string="To sell", compute="_compute_sales_kpis", store=False)
    total_units_kpi = fields.Float(string="Unidades totales", compute="_compute_sales_kpis", store=False)
    total_area_kpi = fields.Float(string="Area total", compute="_compute_sales_kpis", store=False)
    sold_amount = fields.Float(string="Importe vendido", compute="_compute_sales_kpis", store=False)
    amount_to_sell = fields.Float(string="Por vender", compute="_compute_sales_kpis", store=False)

    inventory = fields.Float(string="Inventory", compute="_compute_sales_kpis", store=False)
    total_available = fields.Float(string="Total available", compute="_compute_sales_kpis", store=False)

    percent_sell_l = fields.Float(string="% sell L", compute="_compute_sales_kpis", store=False)
    percent_sell = fields.Float(string="% sell", compute="_compute_sales_kpis", store=False)

    prom = fields.Float(string="Prom", compute="_compute_sales_kpis", store=False)
    total_income = fields.Float(string="Total income", compute="_compute_sales_kpis", store=False)

    total_condominios = fields.Integer(
        string="Total Condominios",
        compute="_compute_sales_kpis",
        store=False,
    )

    total_property_area = fields.Float(
        string="Total Property Area",
        compute="_compute_sales_kpis",
        store=False
    )

    total_area = fields.Float(
        string="Total Area",
        compute="_compute_total_area_custom",
        store=True
    )

    def _compute_total_area_custom(self):
        for record in self:
            record.total_area = (
                    (record.sold_area or 0.0) +
                    (record.available_area or 0.0)
            )

    def _safe_div(self, num, den):
        return num / den if den else 0.0

    def _get_products_domain(self):
        self.ensure_one()
        if self.parent_id:
            # CHILD
            return [('project_worksite_id', '=', self.id)]
        # PARENT
        return [('worksite_id', '=', self.id)]

    def _get_kpi_products(self):
        self.ensure_one()
        return self.env['product.template'].sudo().search(self._get_products_domain())

    def _compute_sales_kpis(self):
        Worksite = self.env['project.worksite'].sudo()
        Condo = self.env['condominium.worksite'].sudo()

        final_amount_field = 'final_amount'
        list_amount_field = 'list_amount'
        paid_amount_field = 'total_paid'

        for rec in self:
            child_worksites = Worksite.search([('parent_id', '=', rec.id)]).ids

            rec.total_condominios = (
                Condo.search_count([('parent_id', 'in', child_worksites)])
                if child_worksites else 0
            )

            rec.total_goal = sum(rec.child_ids.mapped('goal')) if rec.child_ids else (rec.goal or 0.0)

            products = rec._get_kpi_products()

            free_products = products.filtered(lambda p: (p.state or '') == 'free')
            sold_products = products.filtered(lambda p: (p.state or '') == 'sold')
            reserved_products = products.filtered(lambda p: (p.state or '') == 'reserved')
            sold_reserved_products = sold_products | reserved_products

            rec.total_units_kpi = len(sold_products | free_products)

            rec.total_area_kpi = (rec.sold_area or 0.0) + (rec.available_area or 0.0)
            rec.total_property_area = rec.total_area_kpi

            rec.sell = sum(sold_reserved_products.mapped(final_amount_field) or [])
            rec.sold_amount = rec.sell
            rec.total_sell = rec.sold_amount

            rec.total_available = sum(free_products.mapped(list_amount_field) or [])
            rec.inventory = rec.total_available

            rec.amount_to_sell = (rec.total_goal or 0.0) - (rec.sold_amount or 0.0)
            rec.to_sell = rec.amount_to_sell

            rec.percent_sell_l = rec._safe_div(rec.sold_units, rec.total_units)
            rec.percent_sell = rec._safe_div(rec.sold_amount, rec.total_goal)

            rec.prom = rec._safe_div(rec.sold_amount, rec.sold_area)

            if paid_amount_field in self.env['product.template']._fields:
                rec.total_income = sum(sold_reserved_products.mapped(paid_amount_field) or [])
            else:
                rec.total_income = 0.0

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

    def _inverse_analytic_distribution(self):
        for worksite in self:
            worksite.analytic_line_ids.unlink()
            worksite._create_analytic_lines()

    def _create_analytic_lines(self):
        self.ensure_one()
        lines = []
        distribution = self.analytic_distribution or {}
        for account_id_str, amount in distribution.items():
            try:
                account_id = int(account_id_str)
            except ValueError:
                continue  # ignorar claves inválidas como '6,17'

            if amount:
                lines.append((0, 0, {
                    'name': self.name or '/',
                    'account_id': account_id,
                    'amount': amount,
                    'worksite_id': self.id,
                    'date': fields.Date.today(),
                    'unit_amount': 1,
                }))
        self.analytic_line_ids = lines



    @api.model_create_multi
    def create(self, vals):
        worksites = super().create(vals)
        for site in worksites:
            doc_id = self.env['documents.document'].create({
                'name': site.name,
                "owner_id": self.env.ref('base.user_root').id,
                "type": "folder",
                "access_internal": "view",
            })
            if site.parent_id:
                if site.parent_id.carpet_id:
                    doc_id.update({
                        'folder_id': site.parent_id.carpet_id.id
                    })

            site.update({
                'carpet_id': doc_id.id,
            })
        return worksites

    @api.model
    def create_missing_carpet_documents_full_chain(self):

        DocumentsDocument = self.env["documents.document"].sudo()

        def _ensure_carpet_document(record, name, parent_carpet_doc=False):
            if getattr(record, "carpet_id", False):
                return record.carpet_id

            folder_id = parent_carpet_doc.id if parent_carpet_doc else False

            doc = DocumentsDocument.create({
                "name": name or "",
                "folder_id": folder_id,
                "owner_id": self.env.ref("base.user_root").id,
                "type": "folder",
                "access_internal": "view",
            })
            record.sudo().write({"carpet_id": doc.id})

            return doc

        root_worksites = self.search([
            ("carpet_id", "=", False),
            ("parent_id", "=", False),
        ])

        root_carpet_by_ws = {}
        for ws in root_worksites:
            root_carpet_by_ws[ws.id] = _ensure_carpet_document(ws, ws.name)

        child_worksites = self.search([
            ("parent_id", "in", root_worksites.ids),
            ("carpet_id", "=", False),
        ])

        child_carpet_by_ws = {}
        for ws in child_worksites:
            parent_carpet = root_carpet_by_ws.get(ws.parent_id.id) or ws.parent_id.carpet_id
            child_carpet_by_ws[ws.id] = _ensure_carpet_document(ws, ws.name, parent_carpet_doc=parent_carpet)

        Condo = self.env["condominium.worksite"].sudo()
        condos = Condo.search([
            ("parent_id", "in", child_worksites.ids),
            ("carpet_id", "=", False),
        ])

        if not condos:
            print("NO condominium.worksite")
        else:
            condo_carpet_by_id = {}
            for cw in condos:
                parent_carpet = child_carpet_by_ws.get(cw.parent_id.id) or cw.parent_id.carpet_id
                if not parent_carpet:
                    print(f"WARNING: condominium.worksite({cw.id}) parent worksite has no carpet_id. parent_id={cw.parent_id.id}")
                condo_carpet_by_id[cw.id] = _ensure_carpet_document(cw, cw.name, parent_carpet_doc=parent_carpet)

        Product = self.env["product.template"].sudo()
        products = Product.search([
            ("condominium_worksite_id", "in", condos.ids),
            ("carpet_id", "=", False),
        ])

        for pt in products:
            parent_carpet = pt.condominium_worksite_id.carpet_id if pt.condominium_worksite_id else False
            if not parent_carpet:
                print(f"WARNING: parent worksite has no parent_carpet ={parent_carpet}")
            _ensure_carpet_document(pt, pt.name, parent_carpet_doc=parent_carpet)
