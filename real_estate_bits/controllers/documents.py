from odoo import http
from odoo.http import request
import io
import xlsxwriter
import zipfile

class SaleStatementExcelController(http.Controller):

    @http.route('/download/sale_statement/<int:record_id>', type='http', auth='user')
    def download_xlsx(self, record_id, **kwargs):
        record = request.env['property.contract'].sudo().browse(record_id)
        if not record:
            return request.not_found()

        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet("Statement")

        # FORMATS
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'bg_color': '#C8CEDA', 'align': 'center'})
        section_header = workbook.add_format({'bold': True, 'bg_color': '#C8CEDA', 'align': 'center'})
        label_format = workbook.add_format({'bold': True})
        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        percent_format = workbook.add_format({'num_format': '0.00%'})

        # Set column widths
        sheet.set_column("A:A", 12)
        sheet.set_column("B:B", 20)
        sheet.set_column("C:L", 18)

        row = 1

        # === TITLE from C to L ===
        sheet.merge_range(row, 2, row, 11, f"Estado de Cuenta: {record.partner_id.name}", title_format)
        row += 3

        # === HEADER BLOCK ===
        sheet.merge_range(row, 2, row, 4, "Datos de la Propiedad", section_header)
        sheet.merge_range(row, 8, row, 10, "Datos del Cliente", section_header)
        row += 1

        sheet.write(row, 2, "Desarrollo", label_format)
        sheet.write(row, 3, record.property_id.name or "")
        sheet.write(row, 8, "Nombre", label_format)
        sheet.write(row, 9, record.partner_id.name or "")
        row += 1

        sheet.write(row, 2, "Condominio", label_format)
        sheet.write(row, 3, record.property_id.condominium_worksite_id.name or "")
        sheet.write(row, 8, "Teléfono", label_format)
        sheet.write(row, 9, record.partner_id.phone or "")
        row += 1

        sheet.write(row, 2, "Cluster", label_format)
        sheet.write(row, 3, record.project_id.name or "")
        sheet.write(row, 8, "Correo Electrónico", label_format)
        sheet.write(row, 9, record.partner_id.email or "")
        row += 1

        sheet.write(row, 2, "Unidad", label_format)
        sheet.write(row, 3, record.property_id.name or "")
        row += 1

        sheet.write(row, 2, "Metraje", label_format)
        sheet.write(row, 3, f"{record.property_area or 0} m2")
        row += 2

        # === CONTRACT INFO ===
        sheet.merge_range(row, 2, row, 4, "Información del Contrato", section_header)
        sheet.merge_range(row, 8, row, 10, "Desarrollo del Financiamiento", section_header)
        row += 1

        sheet.write(row, 2, "Precio de Venta", label_format)
        sheet.write(row, 3, record.pricing or 0, currency_format)
        sheet.write(row, 8, "Pago adicional de enganche", label_format)
        sheet.write(row, 9, record.extra_down_payment or 0, currency_format)
        row += 1

        enganche_pct = record.advance_payment / record.pricing if record.pricing else 0
        sheet.write(row, 2, "Enganche %", label_format)
        sheet.write(row, 3, enganche_pct, percent_format)
        sheet.write(row, 8, "Monto a Pagar sin Intereses", label_format)
        monto_financiar = record.pricing - record.advance_payment
        sheet.write(row, 9, monto_financiar, currency_format)
        row += 1

        sheet.write(row, 2, "Enganche Pagado", label_format)
        sheet.write(row, 3, record.advance_payment or 0, currency_format)
        sheet.write(row, 8, "Monto Pagado", label_format)
        sheet.write(row, 9, record.paid or 0, currency_format)
        row += 1

        sheet.write(row, 2, "Monto a Financiar", label_format)
        sheet.write(row, 3, monto_financiar, currency_format)
        sheet.write(row, 8, "Monto restante a Pagar", label_format)
        sheet.write(row, 9, record.balance or 0, currency_format)
        row += 1

        sheet.write(row, 2, "Meses de Financiamiento", label_format)
        sheet.write(row, 3, record.template_id.duration_month or 0)
        sheet.write(row, 8, "Total del interés del financiamiento", label_format)
        sheet.write(row, 9, record.total_interests_to_pay or 0, currency_format)
        row += 2

        # === TABLE OF INSTALLMENTS ===
        lines = record.get_line_to_print()
        if lines:
            headers = [
                "Periodo", "Fecha de mensualidad", "Balance inicia", "Mensualidad",
                "Capital", "Pagos anticipados de capital", "Intereses", "Pagado",
                "Balance final", "Fecha de pago", "Interés Moratorio"
            ]
            for col, header in enumerate(headers):
                sheet.write(row, col+1, header, section_header)
            row += 1

            for line in lines:
                sheet.write(row, 1, line.get('count_line'))
                sheet.write(row, 2, str(line.get('date') or ""))
                sheet.write(row, 3, line.get('initial_balance', 0), currency_format)
                sheet.write(row, 4, line.get('amount', 0), currency_format)
                sheet.write(row, 5, line.get('amount_capital', 0), currency_format)
                sheet.write(row, 6, line.get('amount_to_capital', 0))
                sheet.write(row, 7, line.get('interest', 0))
                sheet.write(row, 8, line.get('amount_paid', 0), currency_format)
                sheet.write(row, 9, line.get('final_balance', 0), currency_format)
                sheet.write(row, 10, str(line.get('payment_date') or ""))
                sheet.write(row, 11, line.get('moratorium_interest', 0))
                row += 1

        row += 2

        # === MOVEMENT LOG STARTING AT COLUMN C ===
        payments = record.get_payment_to_print()
        if payments:
            sheet.merge_range(row, 4, row, 6, "REGISTRO DE MOVIMIENTOS", section_header)
            row += 1
            sheet.write(row, 4, "Fecha", section_header)
            sheet.write(row, 5, "Monto", section_header)
            sheet.write(row, 6, "Concepto", section_header)
            row += 1

            for pay in payments:
                sheet.write(row, 4, str(pay.get('date') or ""))
                sheet.write(row, 5, pay.get('amount', 0), currency_format)
                sheet.write(row, 6, pay.get('memo') or "")
                row += 1

        workbook.close()
        buffer.seek(0)
        return request.make_response(
            buffer.read(),
            headers=[
                ('Content-Disposition', 'attachment; filename=property_sale_statement.xlsx'),
                ('Content-Type', 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'),
            ]
        )

    def build_contract_excel(self, record):
        record = record[0]
        buffer = io.BytesIO()
        workbook = xlsxwriter.Workbook(buffer, {'in_memory': True})
        sheet = workbook.add_worksheet("Statement")

        # FORMATS
        title_format = workbook.add_format({'bold': True, 'font_size': 14, 'bg_color': '#C8CEDA', 'align': 'center'})
        section_header = workbook.add_format({'bold': True, 'bg_color': '#C8CEDA', 'align': 'center'})
        label_format = workbook.add_format({'bold': True})
        currency_format = workbook.add_format({'num_format': '$#,##0.00'})
        percent_format = workbook.add_format({'num_format': '0.00%'})

        # Set column widths
        sheet.set_column("A:A", 12)
        sheet.set_column("B:B", 20)
        sheet.set_column("C:L", 18)

        row = 1

        # === TITLE from C to L ===
        sheet.merge_range(row, 2, row, 11, f"Estado de Cuenta: {record.partner_id.name}", title_format)
        row += 3

        # === HEADER BLOCK ===
        sheet.merge_range(row, 2, row, 4, "Datos de la Propiedad", section_header)
        sheet.merge_range(row, 8, row, 10, "Datos del Cliente", section_header)
        row += 1

        sheet.write(row, 2, "Desarrollo", label_format)
        sheet.write(row, 3, record.property_id.name or "")
        sheet.write(row, 8, "Nombre", label_format)
        sheet.write(row, 9, record.partner_id.name or "")
        row += 1

        sheet.write(row, 2, "Condominio", label_format)
        sheet.write(row, 3, record.property_id.condominium_worksite_id.name or "")
        sheet.write(row, 8, "Teléfono", label_format)
        sheet.write(row, 9, record.partner_id.phone or "")
        row += 1

        sheet.write(row, 2, "Cluster", label_format)
        sheet.write(row, 3, record.project_id.name or "")
        sheet.write(row, 8, "Correo Electrónico", label_format)
        sheet.write(row, 9, record.partner_id.email or "")
        row += 1

        sheet.write(row, 2, "Unidad", label_format)
        sheet.write(row, 3, record.property_id.name or "")
        row += 1

        sheet.write(row, 2, "Metraje", label_format)
        sheet.write(row, 3, f"{record.property_area or 0} m2")
        row += 2

        # === CONTRACT INFO ===
        sheet.merge_range(row, 2, row, 4, "Información del Contrato", section_header)
        sheet.merge_range(row, 8, row, 10, "Desarrollo del Financiamiento", section_header)
        row += 1

        sheet.write(row, 2, "Precio de Venta", label_format)
        sheet.write(row, 3, record.pricing or 0, currency_format)
        sheet.write(row, 8, "Pago adicional de enganche", label_format)
        sheet.write(row, 9, record.extra_down_payment or 0, currency_format)
        row += 1

        enganche_pct = record.advance_payment / record.pricing if record.pricing else 0
        sheet.write(row, 2, "Enganche %", label_format)
        sheet.write(row, 3, enganche_pct, percent_format)
        sheet.write(row, 8, "Monto a Pagar sin Intereses", label_format)
        monto_financiar = record.pricing - record.advance_payment
        sheet.write(row, 9, monto_financiar, currency_format)
        row += 1

        sheet.write(row, 2, "Enganche Pagado", label_format)
        sheet.write(row, 3, record.advance_payment or 0, currency_format)
        sheet.write(row, 8, "Monto Pagado", label_format)
        sheet.write(row, 9, record.paid or 0, currency_format)
        row += 1

        sheet.write(row, 2, "Monto a Financiar", label_format)
        sheet.write(row, 3, monto_financiar, currency_format)
        sheet.write(row, 8, "Monto restante a Pagar", label_format)
        sheet.write(row, 9, record.balance or 0, currency_format)
        row += 1

        sheet.write(row, 2, "Meses de Financiamiento", label_format)
        sheet.write(row, 3, record.template_id.duration_month or 0)
        sheet.write(row, 8, "Total del interés del financiamiento", label_format)
        sheet.write(row, 9, record.total_interests_to_pay or 0, currency_format)
        row += 2

        # === TABLE OF INSTALLMENTS ===
        lines = record.get_line_to_print()
        if lines:
            headers = [
                "Periodo", "Fecha de mensualidad", "Balance inicia", "Mensualidad",
                "Capital", "Pagos anticipados de capital", "Intereses", "Pagado",
                "Balance final", "Fecha de pago", "Interés Moratorio"
            ]
            for col, header in enumerate(headers):
                sheet.write(row, col+1, header, section_header)
            row += 1

            for line in lines:
                sheet.write(row, 1, line.get('count_line'))
                sheet.write(row, 2, str(line.get('date') or ""))
                sheet.write(row, 3, line.get('initial_balance', 0), currency_format)
                sheet.write(row, 4, line.get('amount', 0), currency_format)
                sheet.write(row, 5, line.get('amount_capital', 0), currency_format)
                sheet.write(row, 6, line.get('amount_to_capital', 0))
                sheet.write(row, 7, line.get('interest', 0))
                sheet.write(row, 8, line.get('amount_paid', 0), currency_format)
                sheet.write(row, 9, line.get('final_balance', 0), currency_format)
                sheet.write(row, 10, str(line.get('payment_date') or ""))
                sheet.write(row, 11, line.get('moratorium_interest', 0))
                row += 1

        row += 2

        # === MOVEMENT LOG ===
        payments = record.get_payment_to_print()
        if payments:
            sheet.merge_range(row, 4, row, 6, "REGISTRO DE MOVIMIENTOS", section_header)
            row += 1
            sheet.write(row, 4, "Fecha", section_header)
            sheet.write(row, 5, "Monto", section_header)
            sheet.write(row, 6, "Concepto", section_header)
            row += 1

            for pay in payments:
                sheet.write(row, 4, str(pay.get('date') or ""))
                sheet.write(row, 5, pay.get('amount', 0), currency_format)
                sheet.write(row, 6, pay.get('memo') or "")
                row += 1

        workbook.close()
        buffer.seek(0)
        return buffer


    @http.route('/download/sale_statement_zip', type='http', auth='user')
    def download_xlsx_zip(self, **kwargs):
        ids = kwargs.get('ids')
        if not ids:
            return request.not_found()

        record_ids = [int(rid) for rid in ids.split(',') if rid.isdigit()]
        records = request.env['property.contract'].sudo().browse(record_ids)

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for record in records:
                xlsx_file = self.build_contract_excel(record)
                filename = f"{record.partner_id.name or 'contrato'}_{record.id}.xlsx".replace(" ", "_")
                zip_file.writestr(filename, xlsx_file.read())

        zip_buffer.seek(0)
        return request.make_response(
            zip_buffer.read(),
            headers=[
                ('Content-Disposition', 'attachment; filename=estado_cuenta_contratos.zip'),
                ('Content-Type', 'application/zip'),
            ]
        )
