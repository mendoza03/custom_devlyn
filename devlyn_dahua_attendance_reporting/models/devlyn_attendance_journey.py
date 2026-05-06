from odoo import api, fields, models

from ..services.report_utils import DAY_STATE_SELECTION, SEGMENT_STATE_SELECTION


class DevlynAttendanceJourney(models.Model):
    _name = "devlyn.attendance.journey"
    _description = "Jornada biometrica diaria Devlyn"
    _order = "local_date desc, employee_id"
    _rec_name = "name"

    name = fields.Char(compute="_compute_name", store=True, index=True, string="Descripcion")
    employee_id = fields.Many2one(
        "hr.employee",
        required=True,
        ondelete="cascade",
        index=True,
        string="Empleado",
    )
    local_date = fields.Date(required=True, index=True, string="Fecha local")
    segment_count = fields.Integer(default=0, readonly=True, string="Tramos")
    intermittence_count = fields.Integer(default=0, readonly=True, string="Intermitencias")
    total_gap_minutes = fields.Integer(default=0, readonly=True, string="Minutos intermitentes")
    day_state = fields.Selection(
        DAY_STATE_SELECTION,
        required=True,
        default="open",
        index=True,
        string="Estado del dia",
    )
    has_auto_close = fields.Boolean(default=False, readonly=True, index=True, string="Con autocierre")
    has_after_close_review = fields.Boolean(
        default=False,
        readonly=True,
        index=True,
        string="Con revision tardia",
    )
    rebuilt_at = fields.Datetime(readonly=True, string="Reconstruido en")
    segment_ids = fields.One2many(
        "devlyn.attendance.journey.segment",
        "journey_id",
        string="Tramos",
        readonly=True,
        copy=False,
    )

    _employee_day_uniq = models.Constraint(
        "UNIQUE(employee_id, local_date)",
        "La jornada ya existe para ese empleado y fecha.",
    )

    @api.depends("employee_id", "local_date")
    def _compute_name(self):
        for record in self:
            pieces = [
                record.employee_id.name if record.employee_id else "",
                record.local_date.isoformat() if record.local_date else "",
            ]
            record.name = " - ".join(piece for piece in pieces if piece)


class DevlynAttendanceJourneySegment(models.Model):
    _name = "devlyn.attendance.journey.segment"
    _description = "Tramo biometrico de jornada Devlyn"
    _order = "local_date desc, employee_id, sequence, id"

    journey_id = fields.Many2one(
        "devlyn.attendance.journey",
        required=True,
        ondelete="cascade",
        index=True,
        string="Jornada",
    )
    employee_id = fields.Many2one(
        "hr.employee",
        related="journey_id.employee_id",
        store=True,
        index=True,
        readonly=True,
        string="Empleado",
    )
    local_date = fields.Date(
        related="journey_id.local_date",
        store=True,
        index=True,
        readonly=True,
        string="Fecha local",
    )
    sequence = fields.Integer(required=True, index=True, string="Tramo #")
    hr_attendance_id = fields.Many2one(
        "hr.attendance",
        required=True,
        ondelete="cascade",
        index=True,
        string="Asistencia base",
    )
    check_in_local = fields.Char(required=True, readonly=True, string="Entrada local")
    check_out_local = fields.Char(readonly=True, string="Salida local")
    worked_minutes = fields.Integer(default=0, readonly=True, string="Minutos trabajados")
    gap_before_start_local = fields.Char(readonly=True, string="Inicio intermitencia previa")
    gap_before_end_local = fields.Char(readonly=True, string="Fin intermitencia previa")
    gap_before_minutes = fields.Integer(default=0, readonly=True, string="Minutos intermitencia previa")
    segment_state = fields.Selection(
        SEGMENT_STATE_SELECTION,
        required=True,
        default="open",
        index=True,
        readonly=True,
        string="Estado tramo",
    )
    center_code = fields.Char(readonly=True, index=True, string="Id Centro")
    branch_id = fields.Many2one(
        "devlyn.catalog.branch",
        readonly=True,
        ondelete="set null",
        index=True,
        string="Sucursal",
    )
    branch_code = fields.Char(related="branch_id.branch_code", store=True, readonly=True, string="Sucursal codigo")
    branch_name = fields.Char(related="branch_id.branch_name", store=True, readonly=True, string="Sucursal nombre")
    region_id = fields.Many2one(
        "devlyn.catalog.region",
        related="branch_id.region_id",
        store=True,
        readonly=True,
        string="Region",
    )
    zone_id = fields.Many2one(
        "devlyn.catalog.zone",
        related="branch_id.zone_id",
        store=True,
        readonly=True,
        string="Zona",
    )
    district_id = fields.Many2one(
        "devlyn.catalog.district",
        related="branch_id.district_id",
        store=True,
        readonly=True,
        string="Distrito",
    )
    format_id = fields.Many2one(
        "devlyn.catalog.format",
        related="branch_id.format_id",
        store=True,
        readonly=True,
        string="Formato",
    )
    status_id = fields.Many2one(
        "devlyn.catalog.status",
        related="branch_id.status_id",
        store=True,
        readonly=True,
        string="Estatus",
    )
    optical_level_id = fields.Many2one(
        "devlyn.catalog.optical.level",
        related="branch_id.optical_level_id",
        store=True,
        readonly=True,
        string="Nivel optica ventas",
    )

    _journey_sequence_uniq = models.Constraint(
        "UNIQUE(journey_id, sequence)",
        "El tramo ya existe para esa jornada.",
    )


class DevlynAttendanceJourneyRun(models.Model):
    _name = "devlyn.attendance.journey.run"
    _description = "Corrida de reconstruccion de jornadas Devlyn"
    _order = "started_at desc, id desc"

    name = fields.Char(required=True, string="Nombre")
    run_type = fields.Selection(
        [
            ("backfill", "Backfill"),
            ("catchup", "Catch-up"),
            ("repair", "Repair"),
        ],
        required=True,
        default="backfill",
        index=True,
        string="Tipo",
    )
    mode = fields.Selection(
        [("dry_run", "Dry run"), ("apply", "Apply")],
        required=True,
        default="dry_run",
        index=True,
        string="Modo",
    )
    status = fields.Selection(
        [("running", "Running"), ("success", "Success"), ("failed", "Failed")],
        required=True,
        default="running",
        index=True,
        string="Estado",
    )
    date_from = fields.Date(required=True, index=True, string="Fecha inicial")
    date_to = fields.Date(required=True, index=True, string="Fecha final")
    started_at = fields.Datetime(required=True, default=fields.Datetime.now, index=True, string="Inicio")
    finished_at = fields.Datetime(string="Fin")
    batch_size = fields.Integer(default=500, string="Tamano lote")
    employee_filter_json = fields.Text(string="Filtro empleados")
    key_count = fields.Integer(default=0, string="Llaves detectadas")
    processed_count = fields.Integer(default=0, string="Llaves procesadas")
    created_count = fields.Integer(default=0, string="Jornadas creadas")
    updated_count = fields.Integer(default=0, string="Jornadas reconstruidas")
    deleted_count = fields.Integer(default=0, string="Jornadas eliminadas")
    segment_count = fields.Integer(default=0, string="Tramos generados")
    intermittence_count = fields.Integer(default=0, string="Intermitencias generadas")
    error_count = fields.Integer(default=0, string="Errores")
    message = fields.Text(string="Mensaje")
    summary_json = fields.Json(default=dict, string="Resumen")
