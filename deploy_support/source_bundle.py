from __future__ import annotations
"""Preparacion local del source bundle y del contexto Docker.

Responsabilidad del modulo:
1. Resolver addons desde GitHub o desde el filesystem local.
2. Copiarlos a un staging temporal limpio.
3. Detectar dependencias Python externas.
4. Construir el contexto que luego se sube al servidor para `docker build`.
"""

import json
import shutil
import subprocess
import tarfile
from dataclasses import dataclass
from pathlib import Path

from .manifest_tools import (
    ManifestInfo,
    addon_dirs_from_container,
    normalize_package_name,
    parse_manifest_file,
    parse_requirement_lines,
    select_requirement_lines,
)


@dataclass
class PreparedSource:
    """Resultado intermedio de resolver la fuente del despliegue."""
    mode: str
    root_description: str
    git_ref: str | None
    git_commit: str | None
    selected_addons: list[ManifestInfo]
    staging_dir: Path
    source_manifest: dict
    required_python_packages: list[str]
    required_python_imports: list[str]
    requirements_path: Path | None


@dataclass
class BuildContext:
    """Artefactos locales finales que se subiran al servidor."""
    context_dir: Path
    tarball_path: Path
    dockerfile_path: Path
    source_manifest_path: Path
    build_requirements_path: Path


def _run(
    cmd: list[str],
    *,
    cwd: Path | None = None,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    """Wrapper local para comandos shell con error legible."""
    result = subprocess.run(
        cmd,
        cwd=str(cwd) if cwd else None,
        text=True,
        capture_output=True,
    )
    if check and result.returncode != 0:
        raise RuntimeError(
            f"Command failed ({result.returncode}): {' '.join(cmd)}\n"
            f"STDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        )
    return result


def _filter_addons(addons: list[Path], addon_names: list[str]) -> list[Path]:
    """Reduce la lista de addons disponibles al subconjunto solicitado."""
    if not addon_names:
        return addons

    requested = {item.strip() for item in addon_names if item.strip()}
    available = {addon.name: addon for addon in addons}
    missing = sorted(requested - set(available))
    if missing:
        raise RuntimeError(f"Addons not found in source: {', '.join(missing)}")
    return [available[name] for name in sorted(requested)]


def _detect_git_addons(repo_root: Path, git_ref: str) -> list[str]:
    """Inspecciona el arbol Git sin hacer checkout para detectar addons validos."""
    listing = _run(
        ["git", "ls-tree", "-r", "--name-only", git_ref],
        cwd=repo_root,
    ).stdout.splitlines()
    addon_names = {
        entry.split("/", 1)[0]
        for entry in listing
        if entry.count("/") >= 1 and entry.endswith("/__manifest__.py")
    }
    return sorted(addon_names)


def _ensure_git_ref_available(repo_root: Path, git_ref: str) -> None:
    """Asegura que el ref pedido exista localmente antes de exportarlo.

    Caso importante:
    - `origin/<branch>` puede no existir aun en `refs/remotes/...` aunque la rama
      ya exista en GitHub. En ese escenario la traemos explicitamente.
    """
    _run(["git", "fetch", "--tags", "origin"], cwd=repo_root)
    verify = _run(["git", "rev-parse", "--verify", git_ref], cwd=repo_root, check=False)
    if verify.returncode == 0:
        return

    if git_ref.startswith("origin/"):
        branch_name = git_ref.removeprefix("origin/")
        _run(
            [
                "git",
                "fetch",
                "origin",
                f"{branch_name}:refs/remotes/origin/{branch_name}",
            ],
            cwd=repo_root,
        )
        return

    _run(["git", "fetch", "origin", git_ref], cwd=repo_root)


def _prepare_github_source(
    repo_root: Path,
    git_ref: str,
    addon_names: list[str],
    run_tmp_dir: Path,
) -> PreparedSource:
    """Resuelve fuente `github`.

    Paso a paso:
    1. Hace fetch del remoto.
    2. Resuelve el commit exacto del ref.
    3. Detecta addons disponibles en ese ref.
    4. Exporta solo los paths necesarios con `git archive`.
    5. Reconstruye un staging temporal y genera el manifiesto fuente.
    """
    _ensure_git_ref_available(repo_root, git_ref)
    git_commit = _run(["git", "rev-parse", f"{git_ref}^{{commit}}"], cwd=repo_root).stdout.strip()

    available_addons = _detect_git_addons(repo_root, git_ref)
    if not available_addons:
        raise RuntimeError(f"No addons detected in git ref {git_ref}")

    selected_names = _filter_addons([Path(name) for name in available_addons], addon_names)
    export_paths = [path.name for path in selected_names]
    if (repo_root / "requirements.txt").exists():
        export_paths.append("requirements.txt")

    archive_path = run_tmp_dir / "github_source.tar"
    _run(
        ["git", "archive", "--format=tar", "--output", str(archive_path), git_ref, *export_paths],
        cwd=repo_root,
    )

    staging_dir = run_tmp_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    with tarfile.open(archive_path) as archive:
        archive.extractall(staging_dir)

    manifests = [
        parse_manifest_file(staging_dir / name / "__manifest__.py")
        for name in sorted(path.name for path in selected_names)
    ]
    requirements_path = staging_dir / "requirements.txt"
    if not requirements_path.exists():
        requirements_path = None
    requirement_lines = parse_requirement_lines(requirements_path)
    external_python = sorted(
        {
            dep
            for manifest in manifests
            for dep in manifest.external_python_deps
        }
    )
    required_python_packages = select_requirement_lines(requirement_lines, external_python)
    required_python_imports = [
        normalize_package_name(dep).replace("-", "_")
        for dep in external_python
    ]
    source_manifest = {
        "mode": "github",
        "git_ref": git_ref,
        "git_commit": git_commit,
        "selected_addons": [manifest.name for manifest in manifests],
        "addons": [
            {
                "name": manifest.name,
                "version": manifest.version,
                "depends": manifest.depends,
                "external_python_deps": manifest.external_python_deps,
            }
            for manifest in manifests
        ],
    }
    return PreparedSource(
        mode="github",
        root_description=f"git ref {git_ref}",
        git_ref=git_ref,
        git_commit=git_commit,
        selected_addons=manifests,
        staging_dir=staging_dir,
        source_manifest={
            **source_manifest,
            "python_runtime_strategy": "venv",
            "required_python_packages": required_python_packages,
            "required_python_imports": required_python_imports,
        },
        required_python_packages=required_python_packages,
        required_python_imports=required_python_imports,
        requirements_path=requirements_path,
    )


def _prepare_local_source(
    repo_root: Path,
    local_source_path: str,
    addon_names: list[str],
    run_tmp_dir: Path,
) -> PreparedSource:
    """Resuelve fuente `local`.

    Paso a paso:
    1. Normaliza la ruta local.
    2. Detecta si es un addon unico o una carpeta con varios addons.
    3. Copia solo los addons seleccionados al staging temporal.
    4. Lleva tambien `requirements.txt` del repo, si existe.
    """
    source_path = Path(local_source_path)
    if not source_path.is_absolute():
        source_path = (repo_root / source_path).resolve()
    if not source_path.exists():
        raise RuntimeError(f"Local source path not found: {source_path}")

    candidate_addons = addon_dirs_from_container(source_path)
    if not candidate_addons:
        raise RuntimeError(f"No addons detected at local path: {source_path}")
    selected_dirs = _filter_addons(candidate_addons, addon_names)

    staging_dir = run_tmp_dir / "staging"
    staging_dir.mkdir(parents=True, exist_ok=True)
    for addon_dir in selected_dirs:
        shutil.copytree(addon_dir, staging_dir / addon_dir.name)
    requirements_path = repo_root / "requirements.txt"
    if requirements_path.exists():
        shutil.copy2(requirements_path, staging_dir / "requirements.txt")
        staged_requirements = staging_dir / "requirements.txt"
    else:
        staged_requirements = None

    manifests = [
        parse_manifest_file(staging_dir / addon_dir.name / "__manifest__.py")
        for addon_dir in sorted(selected_dirs, key=lambda item: item.name)
    ]
    requirement_lines = parse_requirement_lines(staged_requirements)
    external_python = sorted(
        {
            dep
            for manifest in manifests
            for dep in manifest.external_python_deps
        }
    )
    required_python_packages = select_requirement_lines(requirement_lines, external_python)
    required_python_imports = [
        normalize_package_name(dep).replace("-", "_")
        for dep in external_python
    ]
    source_manifest = {
        "mode": "local",
        "git_ref": None,
        "git_commit": None,
        "selected_addons": [manifest.name for manifest in manifests],
        "addons": [
            {
                "name": manifest.name,
                "version": manifest.version,
                "depends": manifest.depends,
                "external_python_deps": manifest.external_python_deps,
            }
            for manifest in manifests
        ],
        "local_source_path": str(source_path),
    }
    return PreparedSource(
        mode="local",
        root_description=str(source_path),
        git_ref=None,
        git_commit=None,
        selected_addons=manifests,
        staging_dir=staging_dir,
        source_manifest={
            **source_manifest,
            "python_runtime_strategy": "venv",
            "required_python_packages": required_python_packages,
            "required_python_imports": required_python_imports,
        },
        required_python_packages=required_python_packages,
        required_python_imports=required_python_imports,
        requirements_path=staged_requirements,
    )


def prepare_source_bundle(
    *,
    repo_root: Path,
    source_mode: str,
    git_ref: str,
    local_source_path: str,
    addon_names: list[str],
    run_tmp_dir: Path,
) -> PreparedSource:
    """Punto de entrada publico para preparar la fuente del despliegue."""
    run_tmp_dir.mkdir(parents=True, exist_ok=True)
    if source_mode == "github":
        return _prepare_github_source(repo_root, git_ref, addon_names, run_tmp_dir)
    if source_mode == "local":
        return _prepare_local_source(repo_root, local_source_path, addon_names, run_tmp_dir)
    raise RuntimeError(f"Unsupported SOURCE_MODE: {source_mode}")


def build_context_from_source(
    prepared_source: PreparedSource,
    *,
    base_image: str,
    run_tmp_dir: Path,
) -> BuildContext:
    """Construye el contexto Docker final.

    El contexto queda listo para:
    - copiar addons sobre `/mnt/addons-sam`
    - crear `/opt/odoo-venv` como runtime Python aislado
    - instalar dependencias Python necesarias dentro de ese `venv`
    - subirse como tarball al servidor
    """
    context_dir = run_tmp_dir / "context"
    addons_dir = context_dir / "addons"
    addons_dir.mkdir(parents=True, exist_ok=True)

    # Paso 1: copiar cada addon seleccionado a un contexto limpio de build.
    addon_names = [manifest.name for manifest in prepared_source.selected_addons]
    for addon_name in addon_names:
        shutil.copytree(
            prepared_source.staging_dir / addon_name,
            addons_dir / addon_name,
        )

    # Paso 2: generar un Dockerfile minimo derivado de la imagen activa del tenant.
    dockerfile_lines = [
        f"FROM {base_image}",
        "",
        "USER root",
        "",
        "ENV VIRTUAL_ENV=/opt/odoo-venv",
        'ENV PATH="/opt/odoo-venv/bin:${PATH}"',
        "",
        "RUN set -eux; \\",
        "    if ! python3 -m venv --system-site-packages \"$VIRTUAL_ENV\"; then \\",
        "        apt-get update; \\",
        "        apt-get install -y --no-install-recommends python3-venv; \\",
        "        rm -rf /var/lib/apt/lists/*; \\",
        "        rm -rf \"$VIRTUAL_ENV\"; \\",
        "        python3 -m venv --system-site-packages \"$VIRTUAL_ENV\"; \\",
        "    fi",
        "",
        "RUN set -eux; \\",
        "    printf '%s\\n' '#!/bin/sh' 'exec /opt/odoo-venv/bin/python /usr/bin/odoo \"$@\"' > \"$VIRTUAL_ENV/bin/odoo\"; \\",
        "    chmod +x \"$VIRTUAL_ENV/bin/odoo\"",
        "",
    ]
    if prepared_source.required_python_packages:
        dockerfile_lines.extend(
            [
                "COPY build_requirements.txt /tmp/build_requirements.txt",
                "RUN /opt/odoo-venv/bin/pip install --no-cache-dir -r /tmp/build_requirements.txt",
                "",
            ]
        )
    for addon_name in addon_names:
        dockerfile_lines.extend(
            [
                f"RUN rm -rf /mnt/addons-sam/{addon_name}",
                f"COPY addons/{addon_name} /mnt/addons-sam/{addon_name}",
                "",
            ]
        )
    dockerfile_lines.append("USER odoo")
    dockerfile_lines.append("")

    dockerfile_path = context_dir / "Dockerfile"
    dockerfile_path.write_text("\n".join(dockerfile_lines), encoding="utf-8")

    # Paso 3: escribir requirements especificos del build y el manifiesto de fuente.
    build_requirements_path = context_dir / "build_requirements.txt"
    build_requirements_path.write_text(
        "\n".join(prepared_source.required_python_packages) + ("\n" if prepared_source.required_python_packages else ""),
        encoding="utf-8",
    )

    source_manifest_path = context_dir / "source_manifest.json"
    source_manifest_path.write_text(
        json.dumps(prepared_source.source_manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    # Paso 4: comprimir todo en un tarball unico para subirlo al servidor.
    tarball_path = run_tmp_dir / "source_context.tar.gz"
    with tarfile.open(tarball_path, "w:gz") as archive:
        archive.add(context_dir, arcname="context")

    return BuildContext(
        context_dir=context_dir,
        tarball_path=tarball_path,
        dockerfile_path=dockerfile_path,
        source_manifest_path=source_manifest_path,
        build_requirements_path=build_requirements_path,
    )
