from odoo import models, api, fields, _
from odoo.exceptions import ValidationError, UserError
from logging import getLogger
import openpyxl
import binascii
import tempfile
_log = getLogger(__name__)

class MassiveImporter(models.TransientModel):
    _name = 'massive.importer'
    _description = 'Massive Importer for XLSX File'

    name = fields.Binary(string="Upload File")
    file_name = fields.Char(string="Filename Name")

    @api.onchange('name')
    def _onchange_upload_file(self):
        if self.name:
            file_exte = self.file_name.split('.')
            extension = f".{file_exte[-1]}"
            if not extension == '.xlsx':
                raise ValidationError('The type file required is .xlsx')


    def action_submit(self):
        create_items = []
        if self.name:
            file = tempfile.NamedTemporaryFile(suffix=".xlsx")
            file.write(binascii.a2b_base64(self.name))
            file.seek(0)
            workbook = openpyxl.load_workbook(file.name)
            sheet = workbook.active
            rows = sheet.rows
            headers = [cell.value for cell in next(rows)]
            for row in rows:
                data = [cell.value for cell in row]
                if data:
                    search_product = self.env['product.template'].search([('name','=',data[0])])
                    if not search_product:
                        continue
                    search_product.write({
                        'default_code': data[1],
                        'property_area': data[2],
                        'price_per_m':data[3],
                    })