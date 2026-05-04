# -*- coding: utf-8 -*-

from odoo import models, fields, api


class ProjectProject(models.Model):
    _inherit = 'project.project'

    type_of_construction = fields.Selection(
        [('agricultural','Agricultural'),
        ('residential','Residential'),
        ('commercial','Commercial'),
        ('institutional','Institutional'),
        ('industrial','Industrial'),
        ('heavy_civil','Heavy civil'),
        ('environmental','Environmental'),
        ('other','other')],
        string='Types of Construction'
    )
    location_id = fields.Many2one(
        'res.partner',
        string='Location'
    )
    notes_ids = fields.One2many(
        # 'note.note', 
        'project.task', 
        # 'project_id', 
        'custom_note_project_id',
        string='Notes Id',
    )
    notes_count = fields.Integer(
        compute='_compute_notes_count', 
        string="Notes",
        #store=True,
    )

    @api.depends()
    def _compute_notes_count(self):
        for project in self:
            project.notes_count = len(project.notes_ids)
    
    #@api.multi
    def view_notes(self):
        self.ensure_one()
        # for rec in self:
        #res = self.env.ref('odoo_job_costing_management.action_project_note_note')
        res = self.env["ir.actions.actions"]._for_xml_id("odoo_job_costing_management.action_project_note_note")
        # res = res.sudo().read()[0]
        # res['domain'] = str([('project_id','in',self.ids)])
        # res['domain'] = str([('custom_note_project_id','in',self.ids)])
        res['domain'] = str([('custom_note_project_id','=',self.id)])
        res['context'] = {'default_custom_note_project_id': self.id, 'default_is_project_custom': True}
        return res
