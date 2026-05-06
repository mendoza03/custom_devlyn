from odoo import fields, models, tools


class BiometricAttendanceSummary(models.Model):
    _name = "biometric.attendance.summary"
    _description = "Biometric Attendance Daily Summary"
    _auto = False
    _order = "summary_date desc, employee_id"

    summary_date = fields.Date(readonly=True)
    employee_id = fields.Many2one("hr.employee", readonly=True)
    user_id = fields.Many2one("res.users", readonly=True)
    login = fields.Char(readonly=True)
    first_check_in = fields.Datetime(readonly=True)
    last_check_out = fields.Datetime(readonly=True)
    total_worked_hours = fields.Float(readonly=True)
    segments = fields.Integer(readonly=True)
    open_segments = fields.Integer(readonly=True)

    def init(self):
        tools.drop_view_if_exists(self._cr, self._table)
        self._cr.execute(
            f"""
            CREATE OR REPLACE VIEW {self._table} AS (
                SELECT
                    MIN(a.id) AS id,
                    DATE(a.check_in) AS summary_date,
                    a.employee_id AS employee_id,
                    e.user_id AS user_id,
                    u.login AS login,
                    MIN(a.check_in) AS first_check_in,
                    MAX(a.check_out) AS last_check_out,
                    COALESCE(SUM(a.worked_hours), 0.0) AS total_worked_hours,
                    COUNT(*)::int AS segments,
                    COUNT(*) FILTER (WHERE a.check_out IS NULL)::int AS open_segments
                FROM hr_attendance a
                JOIN hr_employee e ON e.id = a.employee_id
                LEFT JOIN res_users u ON u.id = e.user_id
                GROUP BY DATE(a.check_in), a.employee_id, e.user_id, u.login
            )
            """
        )
