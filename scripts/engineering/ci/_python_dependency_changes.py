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
FULL_SUITE_CONFIGURATION_PREFIXES = (
    "tool.pytest.ini_options",
    "tool.setuptools.packages.find.exclude",
)


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


def _uv_constraint_dependencies(document: dict[str, Any]) -> list[str] | None:
    """Return uv resolver constraints when they are a list of requirement strings.

    Any other shape stays in the configuration diff and fails closed.
    """
    tool = document.get("tool")
    if not isinstance(tool, dict):
        return None
    uv = tool.get("uv")
    if not isinstance(uv, dict) or "constraint-dependencies" not in uv:
        return None
    constraints = uv["constraint-dependencies"]
    if isinstance(constraints, list) and all(
        isinstance(item, str) for item in constraints
    ):
        return constraints
    return None


def _requirements(document: dict[str, Any]) -> dict[str, list[str]]:
    project = document.get("project", {})
    groups: list[tuple[str, Any]] = [
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
    constraints = _uv_constraint_dependencies(document)
    if constraints is not None:
        groups.append(("uv-constraint", constraints))
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
    unknown = [
        path for path in paths if not path.startswith(FULL_SUITE_CONFIGURATION_PREFIXES)
    ]
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
    if _uv_constraint_dependencies(remaining) is not None:
        uv = remaining["tool"]["uv"]
        uv.pop("constraint-dependencies", None)
        if not uv:
            remaining["tool"].pop("uv")
        if not remaining["tool"]:
            remaining.pop("tool")
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
    """Find real imports, including consumers of reverse lock dependencies.

    A transitive package with no installed import owner is confirmed only when
    its lock family reaches a distribution declared in ``pyproject.toml`` and a
    scanned file names that distribution in a literal ``distribution`` keyword.
    """
    lock = tomllib.loads((root / PYTHON_LOCK).read_text(encoding="utf-8"))
    packages = lock.get("package", [])
    consumers: set[str] = set()
    unresolved: list[str] = []
    declared = _declared_distributions(root)
    imports, references = _source_index(root, declared)
    module_owners = packages_distributions()
    for dependency in sorted(changed):
        family = _lock_family(packages, dependency)
        selected = _import_consumers(imports, module_owners, family)
        selected |= _declared_reference_consumers(references, declared, family)
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


def _declared_distributions(root: Path) -> set[str]:
    """Return normalized names declared in the working-tree manifest."""
    manifest = root / PYTHON_MANIFEST
    if not manifest.is_file():
        return set()
    document = tomllib.loads(manifest.read_text(encoding="utf-8"))
    return set(_requirements(document))


def _declared_reference_consumers(
    references: Mapping[str, set[str]], declared: set[str], family: set[str]
) -> set[str]:
    """Files that name a manifest distribution reached through the lock family."""
    anchored = declared & family
    if not anchored:
        return set()
    return {path for path, names in references.items() if names & anchored}


def _source_index(
    root: Path, declared: set[str]
) -> tuple[dict[str, set[str]], dict[str, set[str]]]:
    imports: dict[str, set[str]] = {}
    references: dict[str, set[str]] = {}
    for prefix in ("src/bioetl", "src/memory", "scripts", "tests"):
        for path in sorted((root / prefix).rglob("*.py")):
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
            modules, names = _module_and_declared_names(tree, declared)
            relative = path.relative_to(root).as_posix()
            imports[relative] = modules
            if names:
                references[relative] = names
    return imports, references


def _module_and_declared_names(
    tree: ast.AST, declared: set[str]
) -> tuple[set[str], set[str]]:
    modules: set[str] = set()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            modules.add(node.module.split(".")[0])
        elif (
            declared
            and isinstance(node, ast.keyword)
            and node.arg == "distribution"
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        ):
            normalized = _name(node.value.value)
            if normalized in declared:
                names.add(normalized)
    return modules, names
