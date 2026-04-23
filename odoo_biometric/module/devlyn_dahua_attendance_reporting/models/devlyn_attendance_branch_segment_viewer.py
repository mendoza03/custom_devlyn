from odoo import Command, api, fields, models
from odoo.exceptions import ValidationError

from ..services.report_utils import SEGMENT_STATE_SELECTION


class DevlynAttendanceBranchSegmentViewer(models.TransientModel):
    _name = "devlyn.attendance.branch.segment.viewer"
    _description = "Visor de Detalle de Intermitencias"
    _rec_name = "title"

    def _default_date_from(self):
        today = fields.Date.context_today(self)
        return today.replace(day=1)

    def _default_date_to(self):
        return fields.Date.context_today(self)

    title = fields.Char(default="Detalle de Intermitencias", readonly=True, string="Título")
    date_from = fields.Date(required=True, default=_default_date_from, string="Fecha inicial")
    date_to = fields.Date(required=True, default=_default_date_to, string="Fecha final")
    employee_ids = fields.Many2many(
        "hr.employee",
        "devlyn_att_segment_view_emp_rel",
        "viewer_id",
        "employee_id",
        string="Empleados",
    )
    region_ids = fields.Many2many(
        "devlyn.catalog.region",
        "devlyn_att_segment_view_reg_rel",
        "viewer_id",
        "region_id",
        string="Regiones",
    )
    zone_ids = fields.Many2many(
        "devlyn.catalog.zone",
        "devlyn_att_segment_view_zone_rel",
        "viewer_id",
        "zone_id",
        string="Zonas",
    )
    district_ids = fields.Many2many(
        "devlyn.catalog.district",
        "devlyn_att_segment_view_dist_rel",
        "viewer_id",
        "district_id",
        string="Distritos",
    )
    branch_ids = fields.Many2many(
        "devlyn.catalog.branch",
        "devlyn_att_segment_view_branch_rel",
        "viewer_id",
        "branch_id",
        string="Sucursales",
    )
    format_ids = fields.Many2many(
        "devlyn.catalog.format",
        "devlyn_att_segment_view_fmt_rel",
        "viewer_id",
        "format_id",
        string="Formatos",
    )
    status_ids = fields.Many2many(
        "devlyn.catalog.status",
        "devlyn_att_segment_view_status_rel",
        "viewer_id",
        "status_id",
        string="Estatus",
    )
    optical_level_ids = fields.Many2many(
        "devlyn.catalog.optical.level",
        "devlyn_att_segment_view_optlvl_rel",
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
    generated_at = fields.Datetime(readonly=True, string="Última actualización")
    total_rows = fields.Integer(readonly=True, string="Total")
    line_ids = fields.One2many(
        "devlyn.attendance.branch.segment.line",
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
        line_values, summary = self.env["devlyn.attendance.branch.report.service"].build_segment_viewer_payload(self)
        return {
            "generated_at": fields.Datetime.now(),
            "total_rows": summary["total_rows"],
            "line_ids": [Command.clear(), *[Command.create(values) for values in line_values]],
        }

    def _current_action(self):
        self.ensure_one()
        action = self.env.ref(
            "devlyn_dahua_attendance_reporting.action_devlyn_attendance_branch_segment_viewer"
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

    def action_export_xlsx(self):
        self.ensure_one()
        self._validate_date_range()
        file_name, payload = self.env["devlyn.attendance.branch.report.service"].export_segment_payload(self)
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


class DevlynAttendanceBranchSegmentLine(models.TransientModel):
    _name = "devlyn.attendance.branch.segment.line"
    _description = "Línea del Detalle de Intermitencias"
    _order = "report_date desc, employee_name, segment_sequence, id"

    viewer_id = fields.Many2one(
        "devlyn.attendance.branch.segment.viewer",
        required=True,
        ondelete="cascade",
        index=True,
        string="Visor",
    )
    report_date = fields.Date(required=True, index=True, string="Fecha")
    employee_id = fields.Many2one("hr.employee", readonly=True, ondelete="set null", string="Empleado")
    employee_number = fields.Char(readonly=True, string="Id Empleado")
    employee_name = fields.Char(readonly=True, string="Nombre Completo")
    segment_sequence = fields.Integer(readonly=True, string="Tramo #")
    first_check_in_display = fields.Char(readonly=True, string="Hora Entrada")
    last_check_out_display = fields.Char(readonly=True, string="Hora Salida")
    worked_minutes = fields.Integer(readonly=True, string="Minutos tramo")
    worked_minutes_display = fields.Char(readonly=True, string="Tiempo tramo")
    gap_before_start_display = fields.Char(readonly=True, string="Inicio intermitencia previa")
    gap_before_end_display = fields.Char(readonly=True, string="Fin intermitencia previa")
    gap_before_minutes = fields.Integer(readonly=True, string="Minutos intermitencia previa")
    gap_before_display = fields.Char(readonly=True, string="Tiempo intermitencia previa")
    segment_state = fields.Selection(SEGMENT_STATE_SELECTION, readonly=True, string="Estado tramo")
    center_code = fields.Char(readonly=True, string="Id Centro")
    branch_id = fields.Many2one(
        "devlyn.catalog.branch",
        readonly=True,
        ondelete="set null",
        string="Sucursal catálogo",
    )
    branch_code = fields.Char(readonly=True, string="Sucursal")
    branch_name = fields.Char(readonly=True, string="Nombre Sucursal")
