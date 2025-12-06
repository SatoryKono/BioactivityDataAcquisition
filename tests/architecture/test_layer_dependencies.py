import ast
from dataclasses import dataclass
from pathlib import Path

import pytest

SOURCE_ROOT = Path("src")
DOMAIN_ROOT = SOURCE_ROOT / "bioetl" / "domain"
APPLICATION_ROOT = SOURCE_ROOT / "bioetl" / "application"
INFRASTRUCTURE_ROOT = SOURCE_ROOT / "bioetl" / "infrastructure"

APPLICATION_IMPL_ALLOWLIST: set[tuple[str, str]] = {
    (
        "src/bioetl/application/services/chembl_extraction.py",
        "bioetl.infrastructure.clients.chembl.impl.chembl_extraction_service_impl",
    ),
}


@dataclass(frozen=True)
class ImportReference:
    module: str
    lineno: int


def _module_from_path(path: Path) -> tuple[str, bool]:
    relative = path.relative_to(SOURCE_ROOT).with_suffix("")
    parts = list(relative.parts)
    is_package = parts[-1] == "__init__"
    if is_package:
        parts = parts[:-1]
    return ".".join(parts), is_package


def _resolve_module(
    current_module: str, *, module: str, level: int, is_package: bool
) -> str:
    if level == 0:
        return module

    current_parts = current_module.split(".")
    base_parts = current_parts if is_package else current_parts[:-1]
    if level > len(base_parts):
        return module
    prefix = base_parts[: -level]
    if module:
        prefix.extend(module.split("."))
    return ".".join(prefix)


def _collect_imports(path: Path) -> list[ImportReference]:
    code = path.read_text(encoding="utf-8")
    tree = ast.parse(code)
    current_module, is_package = _module_from_path(path)
    imports: list[ImportReference] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend(
                ImportReference(alias.name, node.lineno) for alias in node.names
            )
        elif isinstance(node, ast.ImportFrom):
            module = _resolve_module(
                current_module,
                module=node.module or "",
                level=node.level,
                is_package=is_package,
            )
            if module:
                imports.append(ImportReference(module, node.lineno))
            for alias in node.names:
                target = module
                if target:
                    target = f"{target}.{alias.name}" if alias.name else target
                else:
                    target = alias.name
                if target:
                    imports.append(ImportReference(target, node.lineno))

    return imports


def _layer_segment(module: str, layer: str) -> str | None:
    parts = module.split(".")
    try:
        idx = parts.index(layer)
    except ValueError:
        return None
    if idx + 1 < len(parts):
        return parts[idx + 1]
    return None


def _format_violation(path: Path, lineno: int, message: str) -> str:
    return f"{path.as_posix()}:{lineno}: {message}"


def _assert_no_violations(violations: list[str]) -> None:
    if violations:
        formatted = "\n".join(sorted(set(violations)))
        pytest.fail(f"Forbidden imports detected:\n{formatted}")


def test_domain_has_no_outer_dependencies() -> None:
    violations: list[str] = []
    for file_path in sorted(DOMAIN_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if reference.module.startswith("bioetl.infrastructure"):
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        f"domain must not depend on infrastructure (imported {reference.module})",
                    )
                )
            if reference.module.startswith("bioetl.application"):
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        f"domain must not depend on application (imported {reference.module})",
                    )
                )

    _assert_no_violations(violations)


def test_application_avoids_infrastructure_implementations() -> None:
    violations: list[str] = []
    for file_path in sorted(APPLICATION_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue

            is_allowed = any(
                file_path.as_posix() == allowed_path
                and (
                    reference.module == allowed_module
                    or reference.module.startswith(f"{allowed_module}.")
                )
                for allowed_path, allowed_module in APPLICATION_IMPL_ALLOWLIST
            )

            if "impl" in reference.module.split(".") and not is_allowed:
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "application must not import infrastructure implementations "
                        f"(imported {reference.module})",
                    )
                )

    _assert_no_violations(violations)


def test_infrastructure_does_not_depend_on_application() -> None:
    violations: list[str] = []
    for file_path in sorted(INFRASTRUCTURE_ROOT.rglob("*.py")):
        for reference in _collect_imports(file_path):
            if reference.module.startswith("bioetl.application"):
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "infrastructure must not import application layer "
                        f"(imported {reference.module})",
                    )
                )

    _assert_no_violations(violations)


def test_infrastructure_impls_are_not_cross_used() -> None:
    violations: list[str] = []
    for file_path in sorted(INFRASTRUCTURE_ROOT.rglob("*.py")):
        current_module, _ = _module_from_path(file_path)
        current_segment = _layer_segment(current_module, "infrastructure")

        for reference in _collect_imports(file_path):
            if not reference.module.startswith("bioetl.infrastructure"):
                continue
            if "impl" not in reference.module.split("."):
                continue

            target_segment = _layer_segment(reference.module, "infrastructure")
            if target_segment and target_segment != current_segment:
                violations.append(
                    _format_violation(
                        file_path,
                        reference.lineno,
                        "infrastructure modules must not depend on implementations "
                        f"from other modules (imported {reference.module})",
                    )
                )

    _assert_no_violations(violations)
