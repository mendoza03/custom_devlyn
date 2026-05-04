from __future__ import annotations
"""Helpers para interpretar manifests de Odoo y requirements Python.

Este modulo se usa en la fase local para:
1. Detectar addons validos por la presencia de `__manifest__.py`.
2. Extraer dependencias de Odoo y dependencias Python externas.
3. Traducir esas dependencias Python a lineas reales de `requirements.txt`.
"""

import ast
import re
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ManifestInfo:
    """Representa la metadata minima que el deploy necesita de un addon."""
    name: str
    path: Path
    version: str | None
    depends: list[str]
    external_python_deps: list[str]


def normalize_package_name(value: str) -> str:
    """Normaliza nombres de paquetes para compararlos contra requirements."""
    return value.strip().lower().replace("_", "-")


def parse_requirement_lines(path: Path | None) -> dict[str, str]:
    """Indexa `requirements.txt` por nombre normalizado del paquete.

    Se conserva la linea original para luego reescribir un archivo de build
    con versiones o constraints si ya estaban definidas en el repo.
    """
    if not path or not path.exists():
        return {}

    parsed: dict[str, str] = {}
    pattern = re.compile(r"^([A-Za-z0-9_.-]+)")
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("-r "):
            continue
        match = pattern.match(line)
        if not match:
            continue
        parsed[normalize_package_name(match.group(1))] = line
    return parsed


def select_requirement_lines(
    available_requirements: dict[str, str],
    external_python_deps: list[str],
) -> list[str]:
    """Elige las lineas exactas a instalar durante el build remoto.

    Si el repo ya conoce una version pinneada, se usa esa.
    Si no, se deja solo el nombre del paquete para que pip lo resuelva.
    """
    selected: dict[str, str] = {}
    for dep in external_python_deps:
        normalized = normalize_package_name(dep)
        selected[normalized] = available_requirements.get(normalized, dep)
    return [selected[key] for key in sorted(selected)]


def parse_manifest_text(module_name: str, text: str, path: Path) -> ManifestInfo:
    """Parsea el `__manifest__.py` sin ejecutar codigo arbitrario."""
    module = ast.parse(text)
    if not module.body or not isinstance(module.body[0], ast.Expr):
        raise RuntimeError(f"Unexpected manifest structure in {path}")

    manifest = ast.literal_eval(module.body[0].value)
    depends = [str(item) for item in manifest.get("depends", [])]
    external_python = [
        str(item)
        for item in manifest.get("external_dependencies", {}).get("python", [])
    ]
    version = manifest.get("version")
    if version is not None:
        version = str(version)

    return ManifestInfo(
        name=module_name,
        path=path,
        version=version,
        depends=depends,
        external_python_deps=sorted(set(external_python)),
    )


def parse_manifest_file(path: Path) -> ManifestInfo:
    """Conveniencia para parsear directamente un archivo de manifest."""
    return parse_manifest_text(path.parent.name, path.read_text(encoding="utf-8"), path)


def addon_dirs_from_container(path: Path) -> list[Path]:
    """Acepta dos formas de entrada:

    - una carpeta que ya es un addon
    - una carpeta que contiene varios addons hijos
    """
    if (path / "__manifest__.py").exists():
        return [path]

    addons = [
        child
        for child in sorted(path.iterdir())
        if child.is_dir() and (child / "__manifest__.py").exists()
    ]
    return addons
