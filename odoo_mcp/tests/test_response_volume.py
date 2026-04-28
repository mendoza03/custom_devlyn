from __future__ import annotations

import json
from dataclasses import dataclass

from starlette.testclient import TestClient

from odoo_mcp.app import create_app
from odoo_mcp.config import Settings
from odoo_mcp.server import build_controlled_list_envelope


class VolumeDummyPg:
    def healthcheck(self) -> dict[str, object]:
        return {"db": "biometric_ingest", "usr": "mcp_readonly", "ok": 1}

    def close(self) -> None:
        return None


class VolumeBranchReport:
    def build_rows(self, **_: object):
        return [], "UTC"


class VolumeOdoo:
    def __init__(self):
        self._employees = [
            {
                "id": index,
                "name": f"Empleado {index}",
                "employee_number": 1000 + index,
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "parent_id": {"id": 2000 + index, "display_name": f"Manager {index}"},
                "user_id": False,
                "active": True,
            }
            for index in range(1, 31)
        ]
        self._attendance_summary = [
            {
                "id": index,
                "summary_date": "2026-04-12",
                "employee_id": {"id": index, "display_name": f"Empleado {index}"},
                "user_id": False,
                "login": f"user{index}",
                "first_check_in": f"2026-04-12T08:{index % 60:02d}:00",
                "last_check_out": f"2026-04-12T18:{index % 60:02d}:00",
                "total_worked_hours": float(index),
                "segments": 2,
                "open_segments": 0 if index % 2 == 0 else 1,
            }
            for index in range(1, 21)
        ]
        self._users = [
            {"id": 16, "name": "Ivan", "login": "ivan@example.test", "active": True},
            {"id": 12, "name": "Adriana Mendoza", "login": "adriana@example.test", "active": True},
            {"id": 2, "name": "Administrator", "login": "admin@example.test", "active": True},
        ]
        self._projects = [
            {
                "id": 3,
                "name": "Biométricos",
                "display_name": "Biométricos",
                "user_id": {"id": 12, "display_name": "Adriana Mendoza"},
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
            },
            {
                "id": 2,
                "name": "Otro Proyecto",
                "display_name": "Otro Proyecto",
                "user_id": {"id": 16, "display_name": "Ivan"},
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
            },
        ]
        self._task_stages = [
            {"id": 86, "name": "Configuración y Pruebas", "display_name": "Configuración y Pruebas", "fold": False, "sequence": 1, "active": True},
            {"id": 70, "name": "Pendiente", "display_name": "Pendiente", "fold": False, "sequence": 2, "active": True},
            {"id": 77, "name": "Hecha", "display_name": "Hecha", "fold": True, "sequence": 6, "active": True},
        ]
        self._tasks = [
            {
                "id": 19,
                "name": "Configuraciones de Correo",
                "display_name": "Configuraciones de Correo",
                "project_id": {"id": 3, "display_name": "Biométricos"},
                "user_ids": [16],
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
                "stage_id": {"id": 86, "display_name": "Configuración y Pruebas"},
            },
            {
                "id": 15,
                "name": "Validación de Primera Carga",
                "display_name": "Validación de Primera Carga",
                "project_id": {"id": 3, "display_name": "Biométricos"},
                "user_ids": [12],
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
                "stage_id": {"id": 86, "display_name": "Configuración y Pruebas"},
            },
            {
                "id": 14,
                "name": "Tarea Fuera de Proyecto",
                "display_name": "Tarea Fuera de Proyecto",
                "project_id": {"id": 2, "display_name": "Otro"},
                "user_ids": [16],
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
                "stage_id": {"id": 70, "display_name": "Pendiente"},
            },
            {
                "id": 1,
                "name": "Tarea con m2m roto",
                "display_name": "Tarea con m2m roto",
                "project_id": {"id": 2, "display_name": "Otro Proyecto"},
                "user_ids": {"id": 2, "display_name": 10},
                "company_id": {"id": 1, "display_name": "Grupo Devlyn"},
                "active": True,
                "stage_id": {"id": 77, "display_name": "Hecha"},
            },
        ]
        self._helpdesk_stages = [
            {"id": 1, "name": "Nuevo", "display_name": "Nuevo", "fold": False, "sequence": 1, "active": True},
            {"id": 2, "name": "En proceso de solución", "display_name": "En proceso de solución", "fold": False, "sequence": 2, "active": True},
            {"id": 3, "name": "Solucionado", "display_name": "Solucionado", "fold": True, "sequence": 9, "active": True},
        ]
        self._helpdesk_teams = [
            {"id": 10, "name": "Soporte Devlyn", "display_name": "Soporte Devlyn", "sequence": 1, "active": True},
        ]
        self._helpdesk_tags = [{"id": 7, "name": "VIP", "display_name": "VIP"}]
        self._helpdesk_sections = [
            {"id": 100, "name": "TI", "display_name": "TI", "sequence": 1, "active": True},
        ]
        self._helpdesk_categories = [
            {
                "id": 200,
                "name": "Accesos",
                "display_name": "Accesos",
                "section_id": {"id": 100, "display_name": "TI"},
                "sequence": 1,
                "active": True,
            },
        ]
        self._helpdesk_subcategories = [
            {
                "id": 300,
                "name": "Usuario contraseña",
                "display_name": "Usuario contraseña",
                "category_id": {"id": 200, "display_name": "Accesos"},
                "code": "usuario_contrasena",
                "sequence": 1,
                "active": True,
            },
        ]
        self._helpdesk_slas = [{"id": 50, "name": "Atención 24h", "display_name": "Atención 24h"}]
        self._helpdesk_sla_statuses = [
            {
                "id": 501,
                "display_name": "Atención 24h",
                "sla_id": {"id": 50, "display_name": "Atención 24h"},
                "status": "ongoing",
                "deadline": "2026-04-18 18:00:00",
                "reached_datetime": False,
                "color": 2,
            }
        ]
        self._helpdesk_tickets = [
            {
                "id": 1000 + index,
                "name": f"Ticket {index}",
                "display_name": f"Ticket {index}",
                "ticket_ref": f"HD{index:04d}",
                "partner_id": {"id": 900 + index, "display_name": f"Solicitante {index}"},
                "partner_name": f"Solicitante {index}",
                "partner_email": f"solicitante{index}@example.test",
                "partner_phone": f"555-00{index:02d}",
                "user_id": {"id": 16 if index % 2 else 12, "display_name": "Ivan" if index % 2 else "Adriana Mendoza"},
                "team_id": {"id": 10, "display_name": "Soporte Devlyn"},
                "stage_id": {"id": 3 if index <= 3 else 2, "display_name": "Solucionado" if index <= 3 else "En proceso de solución"},
                "priority": "3" if index == 1 else "1",
                "create_date": f"2026-04-{index:02d} 09:00:00",
                "write_date": f"2026-04-{index:02d} 11:00:00",
                "close_date": f"2026-04-{index:02d} 18:30:00" if index <= 3 else False,
                "assign_date": f"2026-04-{index:02d} 10:00:00",
                "create_uid": {"id": 2, "display_name": "Administrator"},
                "description": f"<p>Detalle del ticket {index}</p>",
                "tag_ids": [7] if index == 1 else [],
                "sla_deadline": "2026-04-18 18:00:00",
                "sla_reached_late": index == 3,
                "sla_status_ids": [501] if index == 1 else [],
                "active": True,
                "x_general_description": f"Motivo ticket {index}",
                "x_detailed_description": f"<p>Motivo detallado {index}</p>",
                "x_section_id": {"id": 100, "display_name": "TI"},
                "x_category_id": {"id": 200, "display_name": "Accesos"},
                "x_subcategory_id": {"id": 300, "display_name": "Usuario contraseña"},
                "x_subcategory_code": "usuario_contrasena",
                "x_commitment_date": "2026-04-20",
                "x_branch_id": {"id": 400, "display_name": "Sucursal Centro"},
                "x_centro_sap": "A001",
                "x_numero_telefonico": "555-0000",
                "x_correo": "sucursal@example.test",
                "x_order_number": "ABCP123456" if index == 1 else False,
            }
            for index in range(1, 15)
        ]

    def healthcheck(self) -> dict[str, object]:
        return {"server_version": "19.0", "authenticated_uid": 999}

    def close(self) -> None:
        return None

    def get_timezone_name(self, fallback_timezone: str) -> str:
        return fallback_timezone

    def fields_get(self, model: str) -> dict[str, object]:
        return dict(self._model_fields(model))

    def existing_fields(self, model: str, candidates: list[str]) -> list[str]:
        known = set(self._model_fields(model))
        return [field for field in candidates if field in known]

    def search_count(self, model: str, domain: list[object]) -> int:
        if model == "hr.employee":
            return len(self._employees)
        if model == "biometric.attendance.summary":
            return len(self._attendance_summary)
        if model == "project.task":
            return len(self._filter_tasks(domain))
        if model == "res.users":
            return len(self._users)
        if model == "project.project":
            return len(self._filter_projects(domain))
        if model == "project.task.type":
            return len(self._task_stages)
        if model == "helpdesk.ticket":
            return len(self._filter_helpdesk_tickets(domain))
        if model == "helpdesk.stage":
            return len(self._helpdesk_stages)
        if model == "helpdesk.team":
            return len(self._helpdesk_teams)
        if model == "helpdesk.tag":
            return len(self._helpdesk_tags)
        if model == "helpdesk.section":
            return len(self._helpdesk_sections)
        if model == "helpdesk.ticket.category":
            return len(self._helpdesk_categories)
        if model == "helpdesk.ticket.subcategory":
            return len(self._helpdesk_subcategories)
        if model == "helpdesk.sla":
            return len(self._helpdesk_slas)
        if model == "helpdesk.sla.status":
            return len(self._helpdesk_sla_statuses)
        return 0

    def search_read(
        self,
        model: str,
        domain: list[object],
        *,
        fields: list[str],
        limit: int,
        offset: int = 0,
        order: str | None = None,
    ) -> list[dict[str, object]]:
        if model == "hr.employee":
            data = self._employees
        elif model == "biometric.attendance.summary":
            data = self._attendance_summary
        elif model == "project.task":
            data = self._filter_tasks(domain)
        elif model == "res.users":
            data = self._users
        elif model == "project.project":
            data = self._filter_projects(domain)
        elif model == "project.task.type":
            data = self._task_stages
        elif model == "helpdesk.ticket":
            data = self._filter_helpdesk_tickets(domain)
        elif model == "helpdesk.stage":
            data = self._helpdesk_stages
        elif model == "helpdesk.team":
            data = self._helpdesk_teams
        elif model == "helpdesk.tag":
            data = self._helpdesk_tags
        elif model == "helpdesk.section":
            data = self._helpdesk_sections
        elif model == "helpdesk.ticket.category":
            data = self._helpdesk_categories
        elif model == "helpdesk.ticket.subcategory":
            data = self._helpdesk_subcategories
        elif model == "helpdesk.sla":
            data = self._helpdesk_slas
        elif model == "helpdesk.sla.status":
            data = self._helpdesk_sla_statuses
        else:
            data = []
        rows = data[offset : offset + limit]
        return [{field: row.get(field) for field in fields if field in row} for row in rows]

    def read(self, model: str, ids: list[int], fields: list[str]) -> list[dict[str, object]]:
        if model == "res.users":
            data = self._users
        elif model == "project.task":
            data = self._tasks
        elif model == "project.project":
            data = self._projects
        elif model == "project.task.type":
            data = self._task_stages
        elif model == "hr.employee":
            data = self._employees
        elif model == "biometric.attendance.summary":
            data = self._attendance_summary
        elif model == "helpdesk.ticket":
            data = self._helpdesk_tickets
        elif model == "helpdesk.stage":
            data = self._helpdesk_stages
        elif model == "helpdesk.team":
            data = self._helpdesk_teams
        elif model == "helpdesk.tag":
            data = self._helpdesk_tags
        elif model == "helpdesk.section":
            data = self._helpdesk_sections
        elif model == "helpdesk.ticket.category":
            data = self._helpdesk_categories
        elif model == "helpdesk.ticket.subcategory":
            data = self._helpdesk_subcategories
        elif model == "helpdesk.sla":
            data = self._helpdesk_slas
        elif model == "helpdesk.sla.status":
            data = self._helpdesk_sla_statuses
        else:
            data = []
        id_set = {int(item) for item in ids}
        rows = [row for row in data if int(row.get("id", 0)) in id_set]
        return [{field: row.get(field) for field in fields if field in row} for row in rows]

    def _model_fields(self, model: str) -> dict[str, dict[str, object]]:
        if model == "hr.employee":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "employee_number": {"type": "integer"},
                "company_id": {"type": "many2one"},
                "parent_id": {"type": "many2one"},
                "user_id": {"type": "many2one"},
                "active": {"type": "boolean"},
            }
        if model == "biometric.attendance.summary":
            return {
                "id": {"type": "integer"},
                "summary_date": {"type": "date"},
                "employee_id": {"type": "many2one"},
                "user_id": {"type": "many2one"},
                "login": {"type": "char"},
                "first_check_in": {"type": "datetime"},
                "last_check_out": {"type": "datetime"},
                "total_worked_hours": {"type": "float"},
                "segments": {"type": "integer"},
                "open_segments": {"type": "integer"},
            }
        if model == "project.task":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "project_id": {"type": "many2one"},
                "user_ids": {"type": "many2many"},
                "company_id": {"type": "many2one"},
                "active": {"type": "boolean"},
                "stage_id": {"type": "many2one"},
            }
        if model == "res.users":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "login": {"type": "char"},
                "active": {"type": "boolean"},
            }
        if model == "project.project":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "user_id": {"type": "many2one"},
                "company_id": {"type": "many2one"},
                "active": {"type": "boolean"},
            }
        if model == "project.task.type":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "fold": {"type": "boolean"},
                "sequence": {"type": "integer"},
                "active": {"type": "boolean"},
            }
        if model == "helpdesk.ticket":
            return {
                "id": {"type": "integer", "string": "ID", "store": True},
                "name": {"type": "char", "string": "Subject", "required": True, "store": True},
                "display_name": {"type": "char", "string": "Display Name", "store": False},
                "ticket_ref": {"type": "char", "string": "Ticket IDs Sequence", "store": True},
                "partner_id": {"type": "many2one", "relation": "res.partner", "string": "Customer", "store": True},
                "partner_name": {"type": "char", "string": "Customer Name", "store": True},
                "partner_email": {"type": "char", "string": "Customer Email", "store": True},
                "partner_phone": {"type": "char", "string": "Customer Phone", "store": True},
                "user_id": {"type": "many2one", "relation": "res.users", "string": "Assigned to", "store": True},
                "team_id": {"type": "many2one", "relation": "helpdesk.team", "string": "Helpdesk Team", "store": True},
                "stage_id": {"type": "many2one", "relation": "helpdesk.stage", "string": "Stage", "store": True},
                "priority": {
                    "type": "selection",
                    "string": "Priority",
                    "selection": [("0", "Low priority"), ("1", "Medium priority"), ("2", "High priority"), ("3", "Urgent")],
                    "store": True,
                },
                "create_date": {"type": "datetime", "string": "Created on", "readonly": True, "store": True},
                "write_date": {"type": "datetime", "string": "Last Updated on", "readonly": True, "store": True},
                "close_date": {"type": "datetime", "string": "Close date", "store": True},
                "assign_date": {"type": "datetime", "string": "First assignment date", "store": True},
                "create_uid": {"type": "many2one", "relation": "res.users", "string": "Created by", "readonly": True, "store": True},
                "description": {"type": "html", "string": "Description", "store": True},
                "tag_ids": {"type": "many2many", "relation": "helpdesk.tag", "string": "Tags", "store": True},
                "sla_deadline": {"type": "datetime", "string": "SLA Deadline", "readonly": True, "store": True},
                "sla_reached_late": {"type": "boolean", "string": "Has SLA reached late", "readonly": True, "store": True},
                "sla_status_ids": {"type": "one2many", "relation": "helpdesk.sla.status", "string": "SLA Status", "store": True},
                "active": {"type": "boolean", "string": "Active", "store": True},
                "x_general_description": {"type": "char", "string": "Descripción General", "required": True, "store": True},
                "x_detailed_description": {"type": "html", "string": "Descripción Detallada", "store": True},
                "x_section_id": {"type": "many2one", "relation": "helpdesk.section", "string": "Sección", "required": True, "store": True},
                "x_category_id": {"type": "many2one", "relation": "helpdesk.ticket.category", "string": "Categoría", "required": True, "store": True},
                "x_subcategory_id": {"type": "many2one", "relation": "helpdesk.ticket.subcategory", "string": "Subcategoría", "required": True, "store": True},
                "x_subcategory_code": {"type": "char", "string": "Código", "readonly": True, "store": True},
                "x_commitment_date": {"type": "date", "string": "Fecha compromiso", "store": True},
                "x_branch_id": {"type": "many2one", "relation": "devlyn.catalog.branch", "string": "Sucursal", "store": True},
                "x_centro_sap": {"type": "char", "string": "Centro SAP", "store": True},
                "x_numero_telefonico": {"type": "char", "string": "Número telefónico", "store": True},
                "x_correo": {"type": "char", "string": "Correo", "store": True},
                "x_order_number": {"type": "char", "string": "Pedido", "store": True},
            }
        if model == "helpdesk.stage":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "sequence": {"type": "integer"},
                "fold": {"type": "boolean"},
                "active": {"type": "boolean"},
            }
        if model == "helpdesk.team":
            return {"id": {"type": "integer"}, "name": {"type": "char"}, "display_name": {"type": "char"}, "sequence": {"type": "integer"}, "active": {"type": "boolean"}}
        if model == "helpdesk.tag":
            return {"id": {"type": "integer"}, "name": {"type": "char"}, "display_name": {"type": "char"}}
        if model == "helpdesk.section":
            return {"id": {"type": "integer"}, "name": {"type": "char"}, "display_name": {"type": "char"}, "sequence": {"type": "integer"}, "active": {"type": "boolean"}}
        if model == "helpdesk.ticket.category":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "section_id": {"type": "many2one", "relation": "helpdesk.section"},
                "sequence": {"type": "integer"},
                "active": {"type": "boolean"},
            }
        if model == "helpdesk.ticket.subcategory":
            return {
                "id": {"type": "integer"},
                "name": {"type": "char"},
                "display_name": {"type": "char"},
                "category_id": {"type": "many2one", "relation": "helpdesk.ticket.category"},
                "code": {"type": "char"},
                "sequence": {"type": "integer"},
                "active": {"type": "boolean"},
            }
        if model == "helpdesk.sla":
            return {"id": {"type": "integer"}, "name": {"type": "char"}, "display_name": {"type": "char"}}
        if model == "helpdesk.sla.status":
            return {
                "id": {"type": "integer"},
                "display_name": {"type": "char"},
                "sla_id": {"type": "many2one", "relation": "helpdesk.sla"},
                "status": {"type": "selection"},
                "deadline": {"type": "datetime"},
                "reached_datetime": {"type": "datetime"},
                "color": {"type": "integer"},
            }
        return {}

    def _filter_tasks(self, domain: list[object]) -> list[dict[str, object]]:
        rows = list(self._tasks)
        for condition in domain:
            if not isinstance(condition, tuple) or len(condition) != 3:
                continue
            field, operator, value = condition
            if field == "active" and operator == "=":
                rows = [row for row in rows if bool(row.get("active")) is bool(value)]
            elif field == "project_id" and operator == "in":
                allowed = {int(item) for item in value}
                rows = [row for row in rows if int((row.get("project_id") or {}).get("id", 0)) in allowed]
            elif field == "stage_id" and operator == "in":
                allowed = {int(item) for item in value}
                rows = [row for row in rows if int((row.get("stage_id") or {}).get("id", 0)) in allowed]
            elif field == "user_ids" and operator == "in":
                allowed = {int(item) for item in value}
                rows = [
                    row
                    for row in rows
                    if any(int(user_id) in allowed for user_id in ([row["user_ids"]["id"]] if isinstance(row.get("user_ids"), dict) else (row.get("user_ids") or [])))
                ]
        return rows

    def _filter_projects(self, domain: list[object]) -> list[dict[str, object]]:
        rows = list(self._projects)
        for condition in domain:
            if not isinstance(condition, tuple) or len(condition) != 3:
                continue
            field, operator, value = condition
            if field == "active" and operator == "=":
                rows = [row for row in rows if bool(row.get("active")) is bool(value)]
        return rows

    def _filter_helpdesk_tickets(self, domain: list[object]) -> list[dict[str, object]]:
        rows = list(self._helpdesk_tickets)
        for condition in domain:
            if not isinstance(condition, tuple) or len(condition) != 3:
                continue
            field, operator, value = condition
            if field == "stage_id" and operator == "=":
                rows = [row for row in rows if int((row.get("stage_id") or {}).get("id", 0)) == int(value)]
            elif field == "stage_id.name" and operator == "ilike":
                needle = str(value).casefold()
                rows = [row for row in rows if needle in str((row.get("stage_id") or {}).get("display_name", "")).casefold()]
            elif field == "user_id" and operator == "=":
                rows = [row for row in rows if int((row.get("user_id") or {}).get("id", 0)) == int(value)]
            elif field == "partner_id" and operator == "=":
                rows = [row for row in rows if int((row.get("partner_id") or {}).get("id", 0)) == int(value)]
            elif field == "priority" and operator == "=":
                rows = [row for row in rows if str(row.get("priority")) == str(value)]
            elif field == "tag_ids" and operator == "in":
                allowed = {int(item) for item in value}
                rows = [row for row in rows if any(int(tag_id) in allowed for tag_id in row.get("tag_ids", []))]
            elif field == "create_date" and operator == ">=":
                rows = [row for row in rows if str(row.get("create_date")) >= str(value)]
            elif field == "create_date" and operator == "<":
                rows = [row for row in rows if str(row.get("create_date")) < str(value)]
            elif field == "close_date" and operator == ">=":
                rows = [row for row in rows if row.get("close_date") and str(row.get("close_date")) >= str(value)]
            elif field == "close_date" and operator == "<":
                rows = [row for row in rows if row.get("close_date") and str(row.get("close_date")) < str(value)]
            elif field == "close_date" and operator == "=" and value is False:
                rows = [row for row in rows if not row.get("close_date")]
            elif field == "close_date" and operator == "!=" and value is False:
                rows = [row for row in rows if bool(row.get("close_date"))]
            elif field == "active" and operator == "=":
                rows = [row for row in rows if bool(row.get("active")) is bool(value)]
        return rows


@dataclass
class VolumeRuntime:
    settings: Settings
    odoo: VolumeOdoo
    biometric_ingest: VolumeDummyPg
    branch_report: VolumeBranchReport

    def close(self) -> None:
        self.odoo.close()
        self.biometric_ingest.close()


def build_volume_test_client() -> TestClient:
    settings = Settings(
        app_name="Devlyn Test MCP",
        app_version="1.0.0-test",
        public_base_url="https://mcp.example.test",
        mcp_mount_path="/mcp",
        host="127.0.0.1",
        port=8071,
        mcp_api_key="top-secret",
        odoo_url="https://erp.example.test",
        odoo_db="devlyn_com",
        odoo_login="mcp.readonly",
        odoo_api_key="odoo-api-key",
        odoo_locale="es_MX",
        odoo_timeout_seconds=15,
        biometric_pg_dsn="postgresql://mcp_readonly:secret@127.0.0.1/biometric_ingest",
        biometric_pg_connect_timeout_seconds=5,
        biometric_pg_statement_timeout_ms=5000,
        default_limit=50,
        max_limit=200,
        default_window_days=7,
        cache_ttl_seconds=300,
        default_timezone="America/Mexico_City",
        log_level="INFO",
    )
    runtime = VolumeRuntime(
        settings=settings,
        odoo=VolumeOdoo(),
        biometric_ingest=VolumeDummyPg(),
        branch_report=VolumeBranchReport(),
    )
    return TestClient(create_app(settings=settings, runtime=runtime))


def _call_tool(client: TestClient, name: str, arguments: dict | None = None) -> dict:
    response = client.post(
        "/mcp",
        headers={
            "x-api-key": "top-secret",
            "accept": "application/json",
            "mcp-protocol-version": "2025-06-18",
            "host": "mcp.example.test",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": name, "arguments": arguments or {}}},
    )
    assert response.status_code == 200
    payload = response.json()
    return json.loads(payload["result"]["content"][0]["text"])


def _list_tools(client: TestClient) -> list[dict]:
    response = client.post(
        "/mcp",
        headers={
            "x-api-key": "top-secret",
            "accept": "application/json",
            "mcp-protocol-version": "2025-06-18",
            "host": "mcp.example.test",
        },
        json={"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}},
    )
    assert response.status_code == 200
    return response.json()["result"]["tools"]


def test_controlled_list_envelope_truncates_large_dataset():
    rows = [{"id": index, "name": "X" * 400, "description": "Y" * 600} for index in range(1, 40)]
    payload = build_controlled_list_envelope(
        source="odoo",
        rows=rows,
        total_count=39,
        offset=0,
        limit=50,
        detail_level="summary",
        summary_fields=["id", "name", "description"],
        standard_fields=["id", "name", "description"],
    )

    assert payload["summary"]["detail_level"] == "summary"
    assert payload["truncated"] is True
    assert len(payload["items"]) <= 8
    assert len(payload["items"][0]["name"]) < 120
    assert payload["next_cursor"] is not None


def test_search_tasks_schema_exposes_project_and_assignee_filters():
    with build_volume_test_client() as client:
        tools = _list_tools(client)

    search_tasks_tool = next(tool for tool in tools if tool["name"] == "search_tasks")
    get_task_tool = next(tool for tool in tools if tool["name"] == "get_task_by_id")
    properties = search_tasks_tool["inputSchema"]["properties"]
    assert "project_ids" in properties
    assert "assignee_ids" in properties
    assert "stage_ids" in properties
    assert "detail_level" in properties
    assert "assignees" in search_tasks_tool["description"]
    assert get_task_tool["name"] == "get_task_by_id"


def test_search_projects_is_accent_tolerant():
    with build_volume_test_client() as client:
        accented = _call_tool(client, "search_projects", {"query": "Biométricos"})
        plain = _call_tool(client, "search_projects", {"query": "biometricos"})

    assert accented["summary"]["total_count"] == 1
    assert plain["summary"]["total_count"] == 1
    assert accented["items"][0]["id"] == 3
    assert plain["items"][0]["id"] == 3


def test_search_employees_defaults_to_summary_mode_and_small_page():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_employees")

    assert payload["summary"]["detail_level"] == "summary"
    assert payload["truncated"] is True
    assert len(payload["items"]) <= 8
    assert set(payload["items"][0].keys()) <= {"id", "employee_number", "name", "active"}
    assert payload["next_cursor"] is not None


def test_search_employees_full_mode_can_return_extra_fields():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_employees", {"detail_level": "full", "limit": 3})

    assert payload["summary"]["detail_level"] == "full"
    assert len(payload["items"]) == 3
    assert "company_id" in payload["items"][0]
    assert "parent_id" in payload["items"][0]


def test_employee_attendance_summary_default_is_top_n():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "get_employee_attendance_summary")

    assert payload["summary"]["detail_level"] == "summary"
    assert payload["summary"]["ordering"] == "top_worked_hours_desc"
    assert payload["items"][0]["employee_id"] == 20
    assert payload["items"][0]["total_worked_hours"] == 20.0
    assert len(payload["items"]) <= 8
    assert payload["truncated"] is True
    assert payload["next_cursor"] is not None


def test_search_tasks_project_filter_returns_assignees_and_stage_names():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_tasks", {"project_ids": [3]})

    assert payload["summary"]["detail_level"] == "summary"
    assert payload["summary"]["total_count"] == 2
    assert payload["summary"]["pending_count"] == 2
    assert payload["summary"]["aggregation_complete"] is True
    assert payload["summary"]["stage_breakdown"] == [
        {
            "stage_id": 86,
            "stage_name": "Configuración y Pruebas",
            "task_count": 2,
            "pending_count": 2,
            "fold": False,
        }
    ]
    assert payload["summary"]["assignee_breakdown"][0]["task_count"] == 1
    assert len(payload["summary"]["top_pending_tasks"]) == 2
    assert payload["items"][0]["project_name"] == "Biométricos"
    assert payload["items"][0]["stage_name"] == "Configuración y Pruebas"
    assert payload["items"][0]["assignees"][0]["name"] in {"Ivan", "Adriana Mendoza"}


def test_search_tasks_limit_50_handles_malformed_assignee_shape():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_tasks", {"limit": 50})

    assert payload["summary"]["total_count"] == 4
    assert payload["summary"]["pending_count"] == 3
    assert "assignee_shape_recovered" in payload["warnings"]
    assert payload["items"][0]["assignees"]


def test_get_task_by_id_resolves_assignee_names():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "get_task_by_id", {"task_id": 19})

    assert payload["summary"]["found"] is True
    assert payload["items"][0]["project_name"] == "Biométricos"
    assert payload["items"][0]["stage_name"] == "Configuración y Pruebas"
    assert payload["items"][0]["assignees"] == [
        {"id": 16, "name": "Ivan", "login": "ivan@example.test", "active": True}
    ]


def test_helpdesk_tools_are_discoverable_with_dashboard_filters():
    with build_volume_test_client() as client:
        tools = {tool["name"]: tool for tool in _list_tools(client)}

    assert "get_helpdesk_catalogs" in tools
    assert "describe_helpdesk_ticket_schema" in tools
    properties = tools["search_helpdesk_tickets"]["inputSchema"]["properties"]
    for field in [
        "detail_level",
        "limit",
        "cursor",
        "fields",
        "stage_id",
        "stage_name",
        "user_id",
        "partner_id",
        "priority",
        "ticket_type_id",
        "tag_id",
        "created_from",
        "created_to",
        "closed_from",
        "closed_to",
        "active",
        "open_only",
        "resolved_only",
    ]:
        assert field in properties
    assert "detail_level=full" in tools["search_helpdesk_tickets"]["description"]


def test_helpdesk_search_dashboard_rows_and_limit_cap_summary():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "search_helpdesk_tickets", {"detail_level": "summary", "limit": 20})

    assert payload["summary"]["requested_limit"] == 20
    assert payload["summary"]["effective_limit"] == 8
    assert payload["summary"]["limit"] == 8
    assert payload["summary"]["returned_count"] == len(payload["items"])
    assert payload["summary"]["returned_count"] <= 8
    assert "limit_capped_to_8" in payload["warnings"]
    assert payload["next_cursor"] is not None
    item = payload["items"][0]
    assert item["requester"]["name"] == "Solicitante 1"
    assert item["assigned_agent"]["name"] == "Ivan"
    assert item["stage"]["name"] == "Solucionado"
    assert item["priority_label"] == "Urgent"
    assert item["security_level_candidate"]["source"] == "priority"
    assert item["category"]["name"] == "Accesos"
    assert item["subcategory"]["name"] == "Usuario contraseña"
    assert item["resolution_hours"] == 9.5


def test_helpdesk_search_filters_stage_agent_requester_priority_dates_and_state():
    with build_volume_test_client() as client:
        by_stage = _call_tool(client, "search_helpdesk_tickets", {"stage_name": "proceso", "open_only": True, "limit": 5})
        by_agent = _call_tool(client, "search_helpdesk_tickets", {"user_id": 12, "open_only": True, "limit": 5})
        by_requester = _call_tool(client, "search_helpdesk_tickets", {"partner_id": 901, "resolved_only": True})
        by_priority = _call_tool(client, "search_helpdesk_tickets", {"priority": "3"})
        by_tag = _call_tool(client, "search_helpdesk_tickets", {"tag_id": 7})
        by_dates = _call_tool(client, "search_helpdesk_tickets", {"created_from": "2026-04-02", "created_to": "2026-04-03"})

    assert by_stage["summary"]["total_count"] == 11
    assert {item["stage"]["name"] for item in by_stage["items"]} == {"En proceso de solución"}
    assert all(item["assigned_agent"]["id"] == 12 for item in by_agent["items"])
    assert by_requester["summary"]["total_count"] == 1
    assert by_requester["items"][0]["requester"]["id"] == 901
    assert by_priority["summary"]["total_count"] == 1
    assert by_tag["summary"]["total_count"] == 1
    assert by_dates["summary"]["total_count"] == 2


def test_helpdesk_catalogs_and_schema_report_real_metadata_and_missing_ticket_type():
    with build_volume_test_client() as client:
        catalogs = _call_tool(client, "get_helpdesk_catalogs")
        schema = _call_tool(client, "describe_helpdesk_ticket_schema")

    item = catalogs["items"][0]
    assert item["catalog_counts"]["stages"] == 3
    assert item["catalog_counts"]["categories"] == 1
    assert item["catalog_counts"]["subcategories"] == 1
    assert {"value": "3", "label": "Urgent"} in item["priorities"]
    assert "ticket_types" in item["unavailable_catalogs"]

    schema_item = schema["items"][0]
    assert "ticket_type_id" in schema_item["unavailable_expected_fields"]
    assert schema_item["fields"]["priority"]["selection"][3] == ["3", "Urgent"] or schema_item["fields"]["priority"]["selection"][3] == ("3", "Urgent")
    assert "x_category_id" in schema_item["custom_dashboard_fields"]
    assert "no_dedicated_security_level_field" in schema["warnings"]


def test_get_helpdesk_ticket_by_id_returns_audit_detail_and_custom_fields():
    with build_volume_test_client() as client:
        payload = _call_tool(client, "get_helpdesk_ticket_by_id", {"ticket_id": 1001})

    assert payload["summary"]["found"] is True
    item = payload["items"][0]
    assert item["requester"] == {
        "id": 901,
        "name": "Solicitante 1",
        "email": "solicitante1@example.test",
        "phone": "555-0001",
    }
    assert item["assigned_agent"]["login"] == "ivan@example.test"
    assert item["creator"]["name"] == "Administrator"
    assert item["sla"]["statuses"][0]["sla"]["display_name"] == "Atención 24h"
    assert item["custom_fields"]["x_order_number"] == "ABCP123456"
    assert "field_unavailable:ticket_type_id" in payload["warnings"]
    assert "no_dedicated_security_level_field" in payload["warnings"]
