from __future__ import annotations
"""Helper remoto para retencion y limpieza de artefactos de despliegue.

Este script corre dentro del servidor y nunca toca el tenant activo:
- conserva la imagen actualmente referenciada por `.env`
- conserva los N backups mas recientes
- conserva los N archivos remotos mas recientes
- conserva las N imagenes de deploy mas recientes por tenant
"""

import argparse
import json
import shutil
import subprocess
from pathlib import Path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Remote tenant maintenance helper")
    parser.add_argument("--tenant", required=True, help="Tenant name or 'all'")
    parser.add_argument("--keep-backups", required=True, type=int)
    parser.add_argument("--keep-archives", required=True, type=int)
    parser.add_argument("--keep-images", required=True, type=int)
    parser.add_argument("--stack-root", default="/home/ubuntu/ccima-prod/stacks")
    parser.add_argument("--backup-root", default="/home/ubuntu/ccima-prod/backups")
    parser.add_argument("--archive-root", default="/home/ubuntu/ccima-prod/archive/deployments")
    parser.add_argument("--repository", default="devaie/odoo_ccima")
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def load_env(path: Path) -> dict[str, str]:
    env: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = raw_line.split("=", 1)
        env[key.strip()] = value.strip()
    return env


def sorted_subdirs(path: Path) -> list[Path]:
    if not path.exists():
        return []
    return sorted([item for item in path.iterdir() if item.is_dir()], key=lambda item: item.name, reverse=True)


def choose_removals(items: list[str], keep_count: int, *, protected: set[str] | None = None) -> dict[str, list[str]]:
    protected = protected or set()
    kept: list[str] = []
    removed: list[str] = []
    for item in items:
        if item in protected:
            kept.append(item)
            continue
        if len(kept) < keep_count:
            kept.append(item)
        else:
            removed.append(item)
    return {"kept": kept, "planned_delete": removed}


def remove_dir(path: Path) -> dict[str, str]:
    try:
        shutil.rmtree(path)
        return {"path": str(path), "status": "deleted"}
    except Exception as exc:  # pragma: no cover - depende del runtime remoto
        return {"path": str(path), "status": "failed", "error": f"{type(exc).__name__}: {exc}"}


def run_command(cmd: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, text=True, capture_output=True)


def list_deploy_images(repository: str, tenant: str) -> list[str]:
    result = run_command(["docker", "images", repository, "--format", "{{.Repository}}:{{.Tag}}"])
    if result.returncode != 0:
        raise RuntimeError(result.stderr.strip() or "docker images failed")
    prefix = f"{repository}:{tenant}-deploy-"
    images = []
    for line in result.stdout.splitlines():
        image = line.strip()
        if not image or image.endswith(":<none>"):
            continue
        if image.startswith(prefix):
            images.append(image)
    return sorted(set(images), reverse=True)


def remove_image(image: str) -> dict[str, str]:
    result = run_command(["docker", "image", "rm", image])
    if result.returncode == 0:
        return {"image": image, "status": "deleted"}
    return {
        "image": image,
        "status": "failed",
        "error": (result.stderr or result.stdout).strip() or "docker image rm failed",
    }


def list_target_tenants(stack_root: Path, requested: str) -> list[str]:
    if requested != "all":
        tenant_dir = stack_root / requested
        if not tenant_dir.exists():
            raise RuntimeError(f"Tenant stack not found: {tenant_dir}")
        if not (tenant_dir / ".env").exists():
            raise RuntimeError(f"Missing .env for tenant: {requested}")
        return [requested]

    tenants = []
    for item in sorted_subdirs(stack_root):
        if (item / ".env").exists():
            tenants.append(item.name)
    return tenants


def summarize_group(
    found_items: list[str],
    keep_count: int,
    *,
    protected: set[str] | None = None,
    apply: bool,
    delete_fn,
) -> dict[str, object]:
    plan = choose_removals(found_items, keep_count, protected=protected)
    deleted: list[dict[str, str]] = []
    failed: list[dict[str, str]] = []
    if apply:
        for item in plan["planned_delete"]:
            result = delete_fn(item)
            if result["status"] == "deleted":
                deleted.append(result)
            else:
                failed.append(result)
    return {
        "found": len(found_items),
        "keep_limit": keep_count,
        "protected": sorted(protected or set()),
        "kept": plan["kept"],
        "planned_delete": plan["planned_delete"],
        "deleted": deleted,
        "failed": failed,
    }


def tenant_report(args: argparse.Namespace, tenant: str) -> dict[str, object]:
    stack_dir = Path(args.stack_root) / tenant
    env = load_env(stack_dir / ".env")
    active_image = env.get("ODOO_IMAGE", "")

    backup_names = [item.name for item in sorted_subdirs(Path(args.backup_root)) if item.name.startswith(f"{tenant}-deploy-")]
    archive_root = Path(args.archive_root) / tenant
    archive_names = [item.name for item in sorted_subdirs(archive_root)]
    image_names = list_deploy_images(args.repository, tenant)

    backups = summarize_group(
        backup_names,
        args.keep_backups,
        apply=args.apply,
        delete_fn=lambda name: remove_dir(Path(args.backup_root) / name),
    )
    archives = summarize_group(
        archive_names,
        args.keep_archives,
        apply=args.apply,
        delete_fn=lambda name: remove_dir(archive_root / name),
    )
    images = summarize_group(
        image_names,
        args.keep_images,
        protected={active_image} if active_image else set(),
        apply=args.apply,
        delete_fn=remove_image,
    )

    return {
        "tenant": tenant,
        "stack_dir": str(stack_dir),
        "active_image": active_image,
        "backups": backups,
        "archives": archives,
        "images": images,
    }


def main() -> int:
    args = parse_args()
    stack_root = Path(args.stack_root)
    tenants = list_target_tenants(stack_root, args.tenant)

    tenant_reports = [tenant_report(args, tenant) for tenant in tenants]
    totals = {
        "tenants": len(tenant_reports),
        "backups_planned_delete": sum(len(item["backups"]["planned_delete"]) for item in tenant_reports),
        "archives_planned_delete": sum(len(item["archives"]["planned_delete"]) for item in tenant_reports),
        "images_planned_delete": sum(len(item["images"]["planned_delete"]) for item in tenant_reports),
        "backups_deleted": sum(len(item["backups"]["deleted"]) for item in tenant_reports),
        "archives_deleted": sum(len(item["archives"]["deleted"]) for item in tenant_reports),
        "images_deleted": sum(len(item["images"]["deleted"]) for item in tenant_reports),
        "failures": sum(
            len(item["backups"]["failed"]) + len(item["archives"]["failed"]) + len(item["images"]["failed"])
            for item in tenant_reports
        ),
    }
    print(
        json.dumps(
            {
                "mode": "apply" if args.apply else "dry-run",
                "tenant_selector": args.tenant,
                "policies": {
                    "keep_backups": args.keep_backups,
                    "keep_archives": args.keep_archives,
                    "keep_images": args.keep_images,
                },
                "tenants": tenant_reports,
                "totals": totals,
            },
            indent=2,
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
