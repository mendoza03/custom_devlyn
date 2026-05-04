# -*- coding: utf-8 -*-

from odoo import _, api, fields, models
from odoo.exceptions import UserError
from odoo.tools.image import image_process
from base64 import b64decode, b64encode
from io import BytesIO
from xlsxwriter import Workbook
from xlsxwriter.utility import xl_rowcol_to_cell
import logging

_logger = logging.getLogger(__name__)


class CcimaCrmFolloupReport(models.TransientModel):
    _name = 'ccima.crm.followup.report'
    _description = 'CRM Follow-Up Report'

    file = fields.Binary(string='File')
    filename = fields.Char(string='Filename')
    state = fields.Selection([
        ('get', 'Pending'),
        ('done', 'Done'),
    ], string='State', default='get')

    @api.model
    def default_get(self, fields_list):
        result = super().default_get(fields_list)
        leads = self.env['crm.lead'].search([('user_id', '=', self.env.user.id)])
        if not leads:
            raise UserError('No tienes leads para dar seguimiento')
        file = self._create_report(leads)
        result.update({
            'file': file,
            'filename': 'Seguimiento.xlsx',
        })
        return result

    def _create_report(self, leads):
        FILE = BytesIO()
        WB = Workbook(FILE, {
            'in_memory': True,
        })
        WS = WB.add_worksheet('Seguimiento')
        image_data = BytesIO(image_process(b64decode(self.env.company.logo), size=(0, 180)))
        header_style = WB.add_format({
            'bg_color': '#003F73',
            'align': 'center',
            'valign': 'vcenter',
            'bold': 1,
            'color': '#FFFFF',
            'border': 1,
            'border_color': '#FFFFFF',
        })
        body_gray_style = WB.add_format({
            'bg_color': '#D9D9D9',
            'valign': 'vcenter',
            'bold': 1,
            'border': 1,
            'border_color': '#FFFFFF',
        })
        body_date_style = WB.add_format({
            'align': 'center',
            'valign': 'vcenter',
            'border': 1,
            'border_color': '#FFFFFF',
        })
        WS.insert_image('A1:B2', 'Logo.png', {'image_data': image_data, 'x_scale': 0.30, 'y_scale': 0.30, 'object_position': 1})
        WS.write(3, 0, 'NOMBRE', header_style)
        WS.write(3, 1, 'F RECIBIDO', header_style)
        WS.merge_range('%s:%s' % (xl_rowcol_to_cell(3, 2), xl_rowcol_to_cell(3, 6)), 'TOQUES', header_style)
        WS.write(3, 7, 'ESTATUS', header_style)
        WS.write(3, 8, 'INTERÉS', header_style)
        WS.write(3, 9, 'COMENTARIO', header_style)
        WS.write(3, 10, 'ACCIÓN', header_style)
        WS.set_column(0, 0, 25)
        WS.set_column(1, 1, 15)
        WS.set_column(2, 6, 4)
        WS.set_column(7, 8, 15)
        WS.set_column(9, 9, 35)
        WS.set_column(10, 10, 15)
        WS.freeze_panes(4, 0)
        rowcount = 4
        for lead in leads:
            activities = lead.activity_ids.sorted('create_date', True)
            last_5_activities = activities[:5]
            WS.write(rowcount, 0, lead.partner_id.name if lead.partner_id else lead.partner_name if lead.partner_name else '', body_gray_style)
            WS.write(rowcount, 1, lead.create_date.strftime('%d/%m/%Y'), body_date_style)
            body_content_values = {
                'align': 'center',
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#FFFFFF',
            }
            if lead.stage_id.background_color:
                body_content_values.update({
                    'bg_color': lead.stage_id.background_color,
                })
            if lead.stage_id.text_color:
                body_content_values.update({
                    'color': lead.stage_id.text_color,
                })
            body_content_large_values = {
                'valign': 'vcenter',
                'border': 1,
                'border_color': '#FFFFFF',
            }
            if lead.stage_id.background_color:
                body_content_large_values.update({
                    'bg_color': lead.stage_id.background_color,
                })
            if lead.stage_id.text_color:
                body_content_large_values.update({
                    'color': lead.stage_id.text_color,
                })
            body_content_style = WB.add_format(body_content_values)
            body_content_large_style = WB.add_format(body_content_large_values)
            for col, activity in enumerate(last_5_activities, start=2):
                values_format = {
                    'align': 'center',
                    'valign': 'vcenter',
                    'font_size': 8,
                    'border': 1,
                    'border_color': '#FFFFFF',
                }
                if activity.activity_type_id.background_color:
                    values_format.update({
                        'bg_color': activity.activity_type_id.background_color,
                    })
                color_format = WB.add_format(values_format)
                WS.write(rowcount, col, activity.activity_type_id.short_name if activity.activity_type_id.short_name else '', color_format)
            WS.write(rowcount, 7, lead.stage_id.name if lead.stage_id else '', body_content_style)
            WS.write(rowcount, 8, lead.property_id.worksite_id.name if lead.property_id and lead.property_id.worksite_id else '', body_content_style)
            WS.write(rowcount, 9, last_5_activities[-1].note if last_5_activities else '', body_content_large_style)
            WS.write(rowcount, 10, last_5_activities[-1].summary if last_5_activities else 'NA', body_content_style)
            rowcount += 1
        WB.close()
        FILE.seek(0)
        return b64encode(FILE.getvalue())

    def action_generate(self):
        self.write({
            'state': 'done',
        })
        return {
            'type': 'ir.actions.act_window',
            'name': 'Reporte de seguimiento',
            'res_model': 'ccima.crm.followup.report',
            'res_id': self.id,
            'view_mode': 'form',
            'view_type': 'form',
            'target': 'new',
        }