from odoo import fields, models
from odoo.exceptions import ValidationError


class DevlynAttendanceBranchReportWizard(models.TransientModel):
    _name = "devlyn.attendance.branch.report.wizard"
    _description = "Asistente de Asistencias por Sucursal"

    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    def _default_date_to(self):
        return fields.Date.context_today(self)

    date_from = fields.Date(required=True, default=_default_date_from, string="Fecha inicial")
    date_to = fields.Date(required=True, default=_default_date_to, string="Fecha final")
    employee_ids = fields.Many2many(
        "hr.employee",
        "devlyn_att_branch_rep_emp_rel",
        "wizard_id",
        "employee_id",
        string="Empleados",
    )
    region_ids = fields.Many2many(
        "devlyn.catalog.region",
        "devlyn_att_branch_rep_reg_rel",
        "wizard_id",
        "region_id",
        string="Regiones",
    )
    zone_ids = fields.Many2many(
        "devlyn.catalog.zone",
        "devlyn_att_branch_rep_zone_rel",
        "wizard_id",
        "zone_id",
        string="Zonas",
    )
    district_ids = fields.Many2many(
        "devlyn.catalog.district",
        "devlyn_att_branch_rep_dist_rel",
        "wizard_id",
        "district_id",
        string="Distritos",
    )
    branch_ids = fields.Many2many(
        "devlyn.catalog.branch",
        "devlyn_att_branch_rep_branch_rel",
        "wizard_id",
        "branch_id",
        string="Sucursales",
    )
    format_ids = fields.Many2many(
        "devlyn.catalog.format",
        "devlyn_att_branch_rep_fmt_rel",
        "wizard_id",
        "format_id",
        string="Formatos",
    )
    status_ids = fields.Many2many(
        "devlyn.catalog.status",
        "devlyn_att_branch_rep_status_rel",
        "wizard_id",
        "status_id",
        string="Estatus",
    )
    optical_level_ids = fields.Many2many(
        "devlyn.catalog.optical.level",
        "devlyn_att_branch_rep_optlvl_rel",
        "wizard_id",
        "optical_level_id",
        string="Nivel Óptica Ventas",
    )
    resolution_scope = fields.Selection(
        [
            ("all", "Todos"),
            ("mapped_only", "Solo mapeados"),
            ("sin_sucursal_only", "Solo sin sucursal"),
        ],
        required=True,
        default="all",
        string="Cobertura de sucursal",
    )
    show_intermitencias = fields.Boolean(default=False, string="Mostrar intermitencias")

    def action_export_xlsx(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValidationError("La fecha final no puede ser menor a la fecha inicial.")
        file_name, payload = self.env["devlyn.attendance.branch.report.service"].export_payload(self)
        attachment = self.env["ir.attachment"].create(
            {
                "name": file_name,
                "type": "binary",
                "datas": payload,
                "res_model": self._name,
                "res_id": self.id,
                "mimetype": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            }
        )
        return {
            "type": "ir.actions.act_url",
            "url": f"/web/content/{attachment.id}?download=1",
            "target": "self",
        }
