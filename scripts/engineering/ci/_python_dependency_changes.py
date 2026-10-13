"""Dependency diff analysis for the existing affected-test selector (no runner)."""

from __future__ import annotations

import ast
from collections.abc import Mapping
import json
from importlib.metadata import packages_distributions
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement


def _name(value: str) -> str:
    return re.sub(r"[-_.]+", "-", value).lower()


def _read_revision(root: Path, revision: str, name: str) -> dict[str, Any]:
    if not revision:
        raise ValueError("Python dependency route requires base/head revisions")
    result = subprocess.run(
        ["git", "show", f"{revision}:{name}"],
        cwd=root,
        check=False,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )
    if result.returncode:
        raise ValueError(f"Cannot verify dependency input {revision}:{name}")
    return tomllib.loads(result.stdout)


def _requirements(document: dict[str, Any]) -> dict[str, list[str]]:
    project = document.get("project", {})
    groups = [
        project.get("dependencies", []),
        document.get("build-system", {}).get("requires", []),
    ]
    groups.extend(project.get("optional-dependencies", {}).values())
    groups.extend(document.get("dependency-groups", {}).values())
    result: dict[str, list[str]] = {}
    for group in groups:
        for raw in group:
            if isinstance(raw, str):
                requirement = Requirement(raw)
                result.setdefault(_name(requirement.name), []).append(str(requirement))
    return {key: sorted(values) for key, values in result.items()}


def changed_dependencies(root: Path, base: str, head: str) -> set[str]:
    """Compare both manifests; include transitive/wheel/hash changes in the lock."""
    changed: set[str] = set()
    for name in ("pyproject.toml", "uv.lock"):
        old = _read_revision(root, base, name)
        new = _read_revision(root, head, name)
        if name == "pyproject.toml":
            before, after = _requirements(old), _requirements(new)
        else:
            before, after = _locked_packages(old), _locked_packages(new)
        changed.update(
            key
            for key in before.keys() | after.keys()
            if before.get(key) != after.get(key)
        )
    if not changed:
        raise ValueError(
            "No Python dependency change proven; manifest/tool configuration needs its own classified route"
        )
    return changed


def _locked_packages(document: dict[str, Any]) -> dict[str, list[str]]:
    result: dict[str, list[str]] = {}
    for package in document.get("package", []):
        if package.get("source", {}).get("editable") == ".":
            continue
        result.setdefault(_name(package["name"]), []).append(
            json.dumps(package, sort_keys=True)
        )
    return {key: sorted(values) for key, values in result.items()}


def dependency_consumers(root: Path, changed: set[str]) -> list[str]:
    """Find real imports, including consumers of reverse lock dependencies."""
    lock = tomllib.loads((root / "uv.lock").read_text(encoding="utf-8"))
    packages = lock.get("package", [])
    consumers: set[str] = set()
    unresolved: list[str] = []
    imports = _source_imports(root)
    module_owners = packages_distributions()
    for dependency in sorted(changed):
        family = _lock_family(packages, dependency)
        selected = _import_consumers(imports, module_owners, family)
        if selected:
            consumers.update(selected)
        else:
            unresolved.append(dependency)
    if unresolved:
        raise ValueError(
            "Unconfirmed Python dependency consumer route: " + ", ".join(unresolved)
        )
    return sorted(consumers)


def _lock_family(packages: list[dict[str, Any]], dependency: str) -> set[str]:
    family = {_name(dependency)}
    while True:
        parents = {
            _name(package["name"])
            for package in packages
            if package.get("source", {}).get("editable") != "."
            and any(
                _name(edge["name"]) in family
                for edge in package.get("dependencies", [])
            )
        }
        expanded = family | parents
        if expanded == family:
            return family
        family = expanded


def _import_consumers(
    imports: dict[str, set[str]], owners: dict[str, list[str]], family: set[str]
) -> set[str]:
    modules = {
        module
        for module, distributions in owners.items()
        if any(_name(owner) in family for owner in distributions)
    }
    return {path for path, imported in imports.items() if imported & modules}


def _source_imports(root: Path) -> dict[str, set[str]]:
    result: dict[str, set[str]] = {}
    for prefix in ("src/bioetl", "src/memory", "scripts", "tests"):
        for path in sorted((root / prefix).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            modules: set[str] = set()
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    modules.update(alias.name.split(".")[0] for alias in node.names)
                elif (
                    isinstance(node, ast.ImportFrom) and node.module and not node.level
                ):
                    modules.add(node.module.split(".")[0])
            result[path.relative_to(root).as_posix()] = modules
    return result
