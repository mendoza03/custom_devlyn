from __future__ import annotations

import json
from pathlib import Path

from odoo import models


class DevlynCatalogLoader:
    def __init__(self, env):
        self.env = env

    def _read_seed(self, file_name: str) -> list[dict]:
        file_path = Path(__file__).resolve().parents[1] / "data" / "seed" / file_name
        if not file_path.exists():
            raise FileNotFoundError(f"Seed file not found: {file_name}")
        return json.loads(file_path.read_text(encoding="utf-8"))

    def _upsert_by_key(self, model_name: str, records: list[dict], key_field: str) -> dict[str, int]:
        model = self.env[model_name]
        existing = {record[key_field]: record for record in model.search([])}
        created = 0
        updated = 0
        for values in records:
            key_value = values[key_field]
            record = existing.get(key_value)
            if record:
                record.write(values)
                updated += 1
            else:
                record = model.create(values)
                existing[key_value] = record
                created += 1
        return {"created": created, "updated": updated, "total": len(records)}

    def load_all(self) -> dict[str, dict[str, int]]:
        results: dict[str, dict[str, int]] = {}
        branches_seed = self._read_seed("branches.json")
        branch_zone_by_district: dict[int, set[int]] = {}
        for item in branches_seed:
            branch_zone_by_district.setdefault(item["legacy_district_id"], set()).add(item["legacy_zone_id"])

        results["regions"] = self._upsert_by_key(
            "devlyn.catalog.region",
            self._read_seed("regions.json"),
            "legacy_region_id",
        )
        results["formats"] = self._upsert_by_key(
            "devlyn.catalog.format",
            self._read_seed("formats.json"),
            "name",
        )
        results["statuses"] = self._upsert_by_key(
            "devlyn.catalog.status",
            self._read_seed("statuses.json"),
            "name",
        )
        results["optical_levels"] = self._upsert_by_key(
            "devlyn.catalog.optical.level",
            self._read_seed("optical_levels.json"),
            "code",
        )

        region_by_legacy = {
            record.legacy_region_id: record
            for record in self.env["devlyn.catalog.region"].search([])
        }

        zone_seed = self._read_seed("zones.json")
        zone_records = []
        known_zone_ids = set()
        for item in zone_seed:
            zone_records.append(
                {
                    "legacy_zone_id": item["legacy_zone_id"],
                    "name": item["name"],
                    "region_id": region_by_legacy[item["legacy_region_id"]].id,
                    "active": True,
                }
            )
            known_zone_ids.add(item["legacy_zone_id"])

        for item in self._read_seed("districts.json"):
            zone_id = item["legacy_zone_id"]
            candidate_zones = branch_zone_by_district.get(item["legacy_district_id"], set())
            if zone_id not in known_zone_ids and len(candidate_zones) == 1:
                zone_id = next(iter(candidate_zones))
            if zone_id in known_zone_ids:
                continue
            zone_records.append(
                {
                    "legacy_zone_id": zone_id,
                    "name": f"Zona legado {zone_id}",
                    "region_id": region_by_legacy[item["legacy_region_id"]].id,
                    "active": True,
                }
            )
            known_zone_ids.add(zone_id)
        results["zones"] = self._upsert_by_key(
            "devlyn.catalog.zone",
            zone_records,
            "legacy_zone_id",
        )

        zone_by_legacy = {
            record.legacy_zone_id: record
            for record in self.env["devlyn.catalog.zone"].search([])
        }

        district_records = []
        for item in self._read_seed("districts.json"):
            zone_legacy_id = item["legacy_zone_id"]
            if zone_legacy_id not in zone_by_legacy:
                candidate_zones = branch_zone_by_district.get(item["legacy_district_id"], set())
                if len(candidate_zones) == 1:
                    zone_legacy_id = next(iter(candidate_zones))
            district_records.append(
                {
                    "legacy_district_id": item["legacy_district_id"],
                    "name": item["name"],
                    "region_id": region_by_legacy[item["legacy_region_id"]].id,
                    "zone_id": zone_by_legacy[zone_legacy_id].id,
                    "active": True,
                }
            )
        results["districts"] = self._upsert_by_key(
            "devlyn.catalog.district",
            district_records,
            "legacy_district_id",
        )

        district_by_legacy = {
            record.legacy_district_id: record
            for record in self.env["devlyn.catalog.district"].search([])
        }
        format_by_name = {record.name: record for record in self.env["devlyn.catalog.format"].search([])}
        status_by_name = {record.name: record for record in self.env["devlyn.catalog.status"].search([])}
        optical_level_by_code = {
            record.code: record
            for record in self.env["devlyn.catalog.optical.level"].search([])
        }

        branch_records = []
        for item in branches_seed:
            branch_records.append(
                {
                    "center_code": item["center_code"],
                    "branch_code": item["branch_code"],
                    "branch_name": item["branch_name"],
                    "optical_level_id": optical_level_by_code[item["optical_level_code"]].id,
                    "format_id": format_by_name[item["format_name"]].id,
                    "status_id": status_by_name[item["status_name"]].id,
                    "region_id": region_by_legacy[item["legacy_region_id"]].id,
                    "zone_id": zone_by_legacy[item["legacy_zone_id"]].id,
                    "district_id": district_by_legacy[item["legacy_district_id"]].id,
                    "active": bool(item["active"]),
                }
            )
        results["branches"] = self._upsert_by_key(
            "devlyn.catalog.branch",
            branch_records,
            "center_code",
        )
        return results


class DevlynCatalogLoaderService(models.AbstractModel):
    _name = "devlyn.catalog.loader.service"
    _description = "Devlyn Catalog Loader Service"

    def load_all(self):
        return DevlynCatalogLoader(self.env).load_all()
