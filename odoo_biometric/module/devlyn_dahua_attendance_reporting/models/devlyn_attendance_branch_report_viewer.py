from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError

from ..services.report_utils import DAY_STATE_SELECTION


class DevlynAttendanceBranchReportViewer(models.TransientModel):
    _name = "devlyn.attendance.branch.report.viewer"
    _description = "Visor de Asistencias por Sucursal"
    _rec_name = "title"

    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    def _default_date_to(self):
        return fields.Date.context_today(self)

    title = fields.Char(default="Asistencias por Sucursal", readonly=True, string="Título")
    date_from = fields.Date(required=True, default=_default_date_from, string="Fecha inicial")
    date_to = fields.Date(required=True, default=_default_date_to, string="Fecha final")
    employee_ids = fields.Many2many(
        "hr.employee",
        "devlyn_att_branch_view_emp_rel",
        "viewer_id",
        "employee_id",
        string="Empleados",
    )
    region_ids = fields.Many2many(
        "devlyn.catalog.region",
        "devlyn_att_branch_view_reg_rel",
        "viewer_id",
        "region_id",
        string="Regiones",
    )
    zone_ids = fields.Many2many(
        "devlyn.catalog.zone",
        "devlyn_att_branch_view_zone_rel",
        "viewer_id",
        "zone_id",
        string="Zonas",
    )
    district_ids = fields.Many2many(
        "devlyn.catalog.district",
        "devlyn_att_branch_view_dist_rel",
        "viewer_id",
        "district_id",
        string="Distritos",
    )
    branch_ids = fields.Many2many(
        "devlyn.catalog.branch",
        "devlyn_att_branch_view_branch_rel",
        "viewer_id",
        "branch_id",
        string="Sucursales",
    )
    format_ids = fields.Many2many(
        "devlyn.catalog.format",
        "devlyn_att_branch_view_fmt_rel",
        "viewer_id",
        "format_id",
        string="Formatos",
    )
    status_ids = fields.Many2many(
        "devlyn.catalog.status",
        "devlyn_att_branch_view_status_rel",
        "viewer_id",
        "status_id",
        string="Estatus",
    )
    optical_level_ids = fields.Many2many(
        "devlyn.catalog.optical.level",
        "devlyn_att_branch_view_optlvl_rel",
        "viewer_id",
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
    generated_at = fields.Datetime(readonly=True, string="Última actualización")
    total_rows = fields.Integer(readonly=True, string="Total")
    mapped_rows = fields.Integer(readonly=True, string="Mapeados")
    unmapped_rows = fields.Integer(readonly=True, string="Sin Sucursal")
    line_ids = fields.One2many(
        "devlyn.attendance.branch.report.line",
        "viewer_id",
        string="Resultados",
        readonly=True,
        copy=False,
    )

    @api.model
    def default_get(self, fields_list):
        values = super().default_get(fields_list)
        def _normalize_m2m(default_value):
            if not default_value:
                return [(6, 0, [])]
            if isinstance(default_value, list) and all(isinstance(item, int) for item in default_value):
                return [(6, 0, default_value)]
            return default_value

        seed_values = {
            "date_from": values.get("date_from") or self._default_date_from(),
            "date_to": values.get("date_to") or self._default_date_to(),
            "resolution_scope": values.get("resolution_scope") or "all",
            "show_intermitencias": bool(values.get("show_intermitencias")),
            "employee_ids": _normalize_m2m(values.get("employee_ids")),
            "region_ids": _normalize_m2m(values.get("region_ids")),
            "zone_ids": _normalize_m2m(values.get("zone_ids")),
            "district_ids": _normalize_m2m(values.get("district_ids")),
            "branch_ids": _normalize_m2m(values.get("branch_ids")),
            "format_ids": _normalize_m2m(values.get("format_ids")),
            "status_ids": _normalize_m2m(values.get("status_ids")),
            "optical_level_ids": _normalize_m2m(values.get("optical_level_ids")),
        }
        viewer = self.new(seed_values)
        refresh_values = viewer._build_refresh_values()
        refresh_values["line_ids"] = refresh_values["line_ids"][1:]
        values.update(seed_values)
        values.update(refresh_values)
        return values

    def _validate_date_range(self):
        self.ensure_one()
        if self.date_from and self.date_to and self.date_to < self.date_from:
            raise ValidationError("La fecha final no puede ser menor a la fecha inicial.")

    def _build_refresh_values(self) -> dict:
        self.ensure_one()
        self._validate_date_range()
        line_values, summary = self.env["devlyn.attendance.branch.report.service"].build_viewer_payload(self)
        return {
            "generated_at": fields.Datetime.now(),
            "total_rows": summary["total_rows"],
            "mapped_rows": summary["mapped_rows"],
            "unmapped_rows": summary["unmapped_rows"],
            "line_ids": [Command.clear(), *[Command.create(values) for values in line_values]],
        }

    def _current_action(self):
        self.ensure_one()
        action = self.env.ref(
            "devlyn_dahua_attendance_reporting.action_devlyn_attendance_branch_report_viewer"
        ).read()[0]
        action.update({"res_id": self.id, "view_mode": "form", "target": "current"})
        return action

    def action_refresh_view(self):
        self.ensure_one()
        self.write(self._build_refresh_values())
        return self._current_action()

    def action_clear_filters(self):
        self.ensure_one()
        today = fields.Date.context_today(self)
        self.write(
            {
                "date_from": today.replace(day=1),
                "date_to": today,
                "resolution_scope": "all",
                "show_intermitencias": False,
                "employee_ids": [Command.clear()],
                "region_ids": [Command.clear()],
                "zone_ids": [Command.clear()],
                "district_ids": [Command.clear()],
                "branch_ids": [Command.clear()],
                "format_ids": [Command.clear()],
                "status_ids": [Command.clear()],
                "optical_level_ids": [Command.clear()],
            }
        )
        return self.action_refresh_view()

    def action_open_export_wizard(self):
        self.ensure_one()
        self._validate_date_range()
        return {
            "type": "ir.actions.act_window",
            "name": "Exportar Asistencias por Sucursal",
            "res_model": "devlyn.attendance.branch.report.wizard",
            "view_mode": "form",
            "view_id": self.env.ref(
                "devlyn_dahua_attendance_reporting.view_devlyn_attendance_branch_report_wizard_form"
            ).id,
            "target": "new",
            "context": {
                "default_date_from": self.date_from,
                "default_date_to": self.date_to,
                "default_resolution_scope": self.resolution_scope,
                "default_show_intermitencias": self.show_intermitencias,
                "default_employee_ids": [(6, 0, self.employee_ids.ids)],
                "default_region_ids": [(6, 0, self.region_ids.ids)],
                "default_zone_ids": [(6, 0, self.zone_ids.ids)],
                "default_district_ids": [(6, 0, self.district_ids.ids)],
                "default_branch_ids": [(6, 0, self.branch_ids.ids)],
                "default_format_ids": [(6, 0, self.format_ids.ids)],
                "default_status_ids": [(6, 0, self.status_ids.ids)],
                "default_optical_level_ids": [(6, 0, self.optical_level_ids.ids)],
            },
        }

    def action_open_segment_viewer(self):
        self.ensure_one()
        self._validate_date_range()
        return {
            "type": "ir.actions.act_window",
            "name": "Detalle de Intermitencias",
            "res_model": "devlyn.attendance.branch.segment.viewer",
            "view_mode": "form",
            "view_id": self.env.ref(
                "devlyn_dahua_attendance_reporting.view_devlyn_attendance_branch_segment_viewer_form"
            ).id,
            "target": "current",
            "context": {
                "default_date_from": self.date_from,
                "default_date_to": self.date_to,
                "default_resolution_scope": self.resolution_scope,
                "default_employee_ids": [(6, 0, self.employee_ids.ids)],
                "default_region_ids": [(6, 0, self.region_ids.ids)],
                "default_zone_ids": [(6, 0, self.zone_ids.ids)],
                "default_district_ids": [(6, 0, self.district_ids.ids)],
                "default_branch_ids": [(6, 0, self.branch_ids.ids)],
                "default_format_ids": [(6, 0, self.format_ids.ids)],
                "default_status_ids": [(6, 0, self.status_ids.ids)],
                "default_optical_level_ids": [(6, 0, self.optical_level_ids.ids)],
            },
        }


class DevlynAttendanceBranchReportLine(models.TransientModel):
    _name = "devlyn.attendance.branch.report.line"
    _description = "Línea del Reporte de Asistencias por Sucursal"
    _order = "report_date desc, region_name, zone_name, district_name, center_code, employee_name"

    viewer_id = fields.Many2one(
        "devlyn.attendance.branch.report.viewer",
        required=True,
        ondelete="cascade",
        index=True,
        string="Visor",
    )
    report_date = fields.Date(required=True, index=True, string="Fecha")
    employee_id = fields.Many2one("hr.employee", readonly=True, ondelete="set null", string="Empleado")
    employee_number = fields.Char(readonly=True, string="Id Empleado")
    employee_name = fields.Char(readonly=True, string="Nombre Completo")
    center_code = fields.Char(readonly=True, string="Id Centro")
    branch_id = fields.Many2one(
        "devlyn.catalog.branch",
        readonly=True,
        ondelete="set null",
        string="Sucursal catálogo",
    )
    branch_code = fields.Char(readonly=True, string="Sucursal")
    branch_name = fields.Char(readonly=True, string="Nombre Sucursal")
    optical_level_id = fields.Many2one(
        "devlyn.catalog.optical.level",
        readonly=True,
        ondelete="set null",
        string="Nivel Óptica Ventas catálogo",
    )
    optical_level_display = fields.Char(readonly=True, string="Nivel Óptica Ventas")
    format_id = fields.Many2one(
        "devlyn.catalog.format",
        readonly=True,
        ondelete="set null",
        string="Formato",
    )
    status_id = fields.Many2one(
        "devlyn.catalog.status",
        readonly=True,
        ondelete="set null",
        string="Estatus",
    )
    region_id = fields.Many2one(
        "devlyn.catalog.region",
        readonly=True,
        ondelete="set null",
        string="Región",
    )
    zone_id = fields.Many2one(
        "devlyn.catalog.zone",
        readonly=True,
        ondelete="set null",
        string="Zona",
    )
    district_id = fields.Many2one(
        "devlyn.catalog.district",
        readonly=True,
        ondelete="set null",
        string="Distrito",
    )
    region_name = fields.Char(readonly=True, string="Región nombre")
    zone_name = fields.Char(readonly=True, string="Zona nombre")
    district_name = fields.Char(readonly=True, string="Distrito nombre")
    first_check_in_display = fields.Char(readonly=True, string="Hora Entrada")
    last_check_out_display = fields.Char(readonly=True, string="Hora Salida")
    worked_hours = fields.Float(readonly=True, string="Horas trabajadas")
    worked_hours_display = fields.Char(readonly=True, string="Tiempo efectivo")
    intermittence_count = fields.Integer(readonly=True, string="Intermitencias")
    total_gap_minutes = fields.Integer(readonly=True, string="Minutos intermitentes")
    total_gap_display = fields.Char(readonly=True, string="Tiempo intermitente")
    day_state = fields.Selection(DAY_STATE_SELECTION, readonly=True, string="Estado del día")
    is_unmapped = fields.Boolean(readonly=True, string="Sin sucursal")
