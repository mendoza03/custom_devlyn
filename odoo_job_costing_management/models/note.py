# -*- coding: utf-8 -*-

from odoo import api, fields, models, _
from odoo.tools import html2plaintext


class Task(models.Model):
    # _inherit = 'note.note'
    _inherit = 'project.task'

    @api.onchange('task_id')
    def onchange_task(self):
        for rec in self:
            # rec.project_id = rec.task_id.project_id.id
            rec.custom_note_project_id = rec.task_id.project_id.id


    custom_note_project_id = fields.Many2one(
        'project.project',
        string='Construction Project',
    )
    task_id = fields.Many2one(
        'project.task',
        string='Task / Job Order',
    )
    # is_task = fields.Boolean(
    #     string='Is Job Order?',
    # )
    is_task_custom = fields.Boolean(
        string='Is Job Order?',
        oldname='is_task',
    )
    # is_project = fields.Boolean(
    #     string='Is Project?',
    # )
    is_project_custom = fields.Boolean(
        string='Is Project?',
        oldname='is_project',
    )
