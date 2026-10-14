"""Dependency diff analysis for the existing affected-test selector (no runner)."""

from __future__ import annotations

import ast
import copy
from collections.abc import Mapping
import json
from importlib.metadata import (
    PackageNotFoundError,
    distribution,
    packages_distributions,
)
import re
import subprocess
import tomllib
from pathlib import Path
from typing import Any

from packaging.requirements import Requirement

PYTHON_MANIFEST = "pyproject.toml"
PYTHON_LOCK = "uv.lock"


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
        ("project", project.get("dependencies", [])),
        ("build-system", document.get("build-system", {}).get("requires", [])),
        *[
            (f"optional:{name}", values)
            for name, values in project.get("optional-dependencies", {}).items()
        ],
        *[
            (f"group:{name}", values)
            for name, values in document.get("dependency-groups", {}).items()
        ],
    ]
    result: dict[str, list[str]] = {}
    for label, group in groups:
        for raw in group:
            if isinstance(raw, str):
                requirement = Requirement(raw)
                result.setdefault(_name(requirement.name), []).append(
                    f"{label}:{requirement}"
                )
    return {key: sorted(values) for key, values in result.items()}


def changed_dependencies(
    root: Path, base: str, head: str, *, allow_configuration: bool = False
) -> set[str]:
    """Compare both manifests; include transitive/wheel/hash changes in the lock."""
    changed: set[str] = set()
    for name in (PYTHON_MANIFEST, PYTHON_LOCK):
        old = _read_revision(root, base, name)
        new = _read_revision(root, head, name)
        if name == PYTHON_MANIFEST:
            before, after = _requirements(old), _requirements(new)
        else:
            before, after = _locked_packages(old), _locked_packages(new)
        changed.update(
            key
            for key in before.keys() | after.keys()
            if before.get(key) != after.get(key)
        )
    if not changed and not allow_configuration:
        raise ValueError(
            "No Python dependency change proven; manifest/tool configuration needs its own classified route"
        )
    return changed


def pytest_configuration_changed(root: Path, base: str, head: str) -> bool:
    """Mixed config/dependency changes must retain their configuration lane."""
    before = _configuration(_read_revision(root, base, PYTHON_MANIFEST))
    after = _configuration(_read_revision(root, head, PYTHON_MANIFEST))
    paths = _changed_paths(before, after)
    unknown = [path for path in paths if not path.startswith("tool.pytest.ini_options")]
    if unknown:
        raise ValueError(
            "Unconfirmed Python manifest configuration route: " + ", ".join(unknown)
        )
    return bool(paths)


def _configuration(document: dict[str, Any]) -> dict[str, Any]:
    remaining = copy.deepcopy(document)
    for section, keys in (
        ("project", ("dependencies", "optional-dependencies")),
        ("build-system", ("requires",)),
    ):
        for key in keys:
            remaining.get(section, {}).pop(key, None)
        if section in remaining and not remaining[section]:
            remaining.pop(section)
    group_config = {
        name: [item for item in values if not isinstance(item, str)]
        for name, values in remaining.pop("dependency-groups", {}).items()
    }
    if any(group_config.values()):
        remaining["dependency-groups"] = group_config
    return remaining


def _changed_paths(before: Any, after: Any, prefix: str = "") -> list[str]:
    if isinstance(before, dict) and isinstance(after, dict):
        return [
            path
            for key in sorted(before.keys() | after.keys())
            for path in _changed_paths(
                before.get(key, {}), after.get(key, {}), f"{prefix}.{key}".lstrip(".")
            )
        ]
    return [prefix] if before != after else []


def pytest_framework_affected(root: Path, dependencies: set[str]) -> bool:
    """The global test framework owns the canonical all-tests lane, including helpers."""
    packages = tomllib.loads((root / PYTHON_LOCK).read_text(encoding="utf-8")).get(
        "package", []
    )
    return any(
        "pytest" in _lock_family(packages, dependency) or _is_pytest_plugin(dependency)
        for dependency in dependencies
    )


def repository_cli_affected(root: Path, dependencies: set[str]) -> bool:
    """CLI ownership comes from installed entrypoints and existing workflow commands."""
    workflows = [
        *(root / ".github/workflows").glob("*.yml"),
        root / ".circleci/config.yml",
    ]
    commands = {
        token
        for workflow in workflows
        if workflow.is_file()
        for command in _workflow_commands(workflow)
        for line in command.splitlines()
        if not line.lstrip().startswith("#")
        for token in re.findall(r"(?<![\w./-])[\w-]+(?=\s|[;&|]|$)", line)
    }
    return any(
        command in commands
        for dependency in dependencies
        for command in _console_commands(dependency)
    )


def _console_commands(package: str) -> set[str]:
    try:
        installed = distribution(package)
    except PackageNotFoundError:
        return set()
    commands = {
        entry.name
        for entry in installed.entry_points
        if entry.group == "console_scripts"
    }
    # Native wheels (e.g. Ruff) own scripts through RECORD, not console_scripts.
    commands.update(
        Path(str(record)).stem
        for record in (getattr(installed, "files", None) or ())
        if {"bin", "Scripts", "scripts"} & set(Path(str(record)).parts[:-1])
    )
    return commands


def _workflow_commands(path: Path) -> list[str]:
    import yaml

    def runs(value: Any) -> list[str]:
        if isinstance(value, dict):
            result = []
            for key, nested in value.items():
                if key == "run" and isinstance(nested, str):
                    result.append(nested)
                elif key == "run" and isinstance(nested, dict):
                    result.append(nested.get("command", ""))
                else:
                    result.extend(runs(nested))
            return result
        if isinstance(value, list):
            return [command for nested in value for command in runs(nested)]
        return []

    return runs(yaml.safe_load(path.read_text(encoding="utf-8")))


def _entry_points(package: str) -> tuple[Any, ...]:
    try:
        return tuple(distribution(package).entry_points)
    except PackageNotFoundError:
        return ()


def _is_pytest_plugin(package: str) -> bool:
    return any(entry.group == "pytest11" for entry in _entry_points(package))


def removed_dependencies(root: Path, base: str, head: str) -> bool:
    """Exact sync removes ownership metadata; retain a conservative canonical lane."""
    before = _locked_packages(_read_revision(root, base, PYTHON_LOCK))
    after = _locked_packages(_read_revision(root, head, PYTHON_LOCK))
    return bool(before.keys() - after.keys())


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
    lock = tomllib.loads((root / PYTHON_LOCK).read_text(encoding="utf-8"))
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
    imports: dict[str, set[str]], owners: Mapping[str, list[str]], family: set[str]
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
