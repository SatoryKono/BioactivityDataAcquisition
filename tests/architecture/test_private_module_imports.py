"""Owner-aware guardrail for first-party private-module imports in src/.

RF-011.0 introduced a baseline-aware mode; RF-011.2 switched this guard to strict.
Only imports within the same immediate owner package may target ``._*`` modules.
All cross-owner private-module imports in ``src/`` are forbidden.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

STRICT_PRIVATE_IMPORT_GUARD = True

# RF-011.0 baseline (historical, kept for traceability):
# {
#   ("src/bioetl/composition/bootstrap/assembly/storage.py",
#    "bioetl.composition.factories.storage._resilience"),
#   ("src/bioetl/composition/factories/datasource/data_source_factory.py",
#    "bioetl.composition.providers._models"),
#   ("src/bioetl/composition/factories/services/bundle.py",
#    "bioetl.composition.factories._observability_wiring"),
#   ("src/bioetl/composition/factories/services/bundle.py",
#    "bioetl.composition.factories.pipeline._creation_wiring"),
#   ("src/bioetl/domain/contracts/__init__.py",
#    "bioetl.domain.contracts.gold._base"),
#   ("src/bioetl/infrastructure/export/dq_report_writer.py",
#    "bioetl.infrastructure.storage.support.atomic_ops"),
# }
ALLOWED_BASELINE_IMPORTS: frozenset[tuple[str, str]] = frozenset(
    {
        # Internal composition modules used by interfaces for runtime access
        (
            "src/bioetl/interfaces/cli/commands/domains/health/server_integration.py",
            "bioetl.composition._resource_management",
        ),
        (
            "src/bioetl/interfaces/cli/commands/domains/health/server_integration.py",
            "bioetl.composition._service_protocols",
        ),
        (
            "src/bioetl/interfaces/cli/commands/domains/health/server_integration.py",
            "bioetl.composition._services",
        ),
        (
            "src/bioetl/interfaces/cli/commands/health.py",
            "bioetl.composition._service_protocols",
        ),
    }
)


def _module_name_for_path(src_dir: Path, file_path: Path) -> str:
    rel_parts = file_path.relative_to(src_dir).with_suffix("").parts
    return ".".join(rel_parts)


def _collect_existing_modules(source_root: Path) -> frozenset[str]:
    modules: set[str] = set()
    for py_file in source_root.rglob("*.py"):
        rel_path = py_file.relative_to(source_root.parent)
        if py_file.name == "__init__.py":
            modules.add(".".join(rel_path.parent.parts))
            continue
        modules.add(".".join(rel_path.with_suffix("").parts))
    return frozenset(modules)


def _resolve_relative_module(
    *,
    importer_module: str,
    module: str | None,
    level: int,
) -> str | None:
    if level == 0:
        return module

    parent_parts = importer_module.split(".")[:-1]
    if level > len(parent_parts):
        return None

    base_parts = parent_parts[: len(parent_parts) - level + 1]
    if module:
        return ".".join([*base_parts, module])
    return ".".join(base_parts)


def _module_exists(existing_modules: frozenset[str], module: str) -> bool:
    return module in existing_modules


def _iter_candidate_import_targets(
    *,
    existing_modules: frozenset[str],
    importer_module: str,
    node: ast.AST,
) -> list[str]:
    if isinstance(node, ast.Import):
        return [alias.name for alias in node.names if alias.name.startswith("bioetl.")]

    if not isinstance(node, ast.ImportFrom):
        return []

    base_module = _resolve_relative_module(
        importer_module=importer_module,
        module=node.module,
        level=node.level,
    )
    if not base_module or not base_module.startswith("bioetl."):
        return []

    candidates = [base_module]
    for alias in node.names:
        if alias.name == "*":
            continue
        nested_module = f"{base_module}.{alias.name}"
        if _module_exists(existing_modules, nested_module):
            candidates.append(nested_module)
    return candidates


def _is_private_module(module: str) -> bool:
    return any(part.startswith("_") for part in module.split("."))


def _collect_external_private_imports(
    src_dir: Path,
) -> dict[tuple[str, str], list[int]]:
    violations: dict[tuple[str, str], list[int]] = {}
    source_root = src_dir / "bioetl"
    existing_modules = _collect_existing_modules(source_root)

    for py_file in sorted(source_root.rglob("*.py")):
        importer_module = _module_name_for_path(src_dir, py_file)
        importer_owner = importer_module.rsplit(".", 1)[0]
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        rel_path = py_file.relative_to(src_dir).as_posix()

        for node in ast.walk(tree):
            for target_module in _iter_candidate_import_targets(
                existing_modules=existing_modules,
                importer_module=importer_module,
                node=node,
            ):
                if not _is_private_module(target_module):
                    continue
                target_owner = target_module.rsplit(".", 1)[0]
                if importer_owner == target_owner:
                    continue
                key = (rel_path, target_module)
                violations.setdefault(key, []).append(getattr(node, "lineno", 0))

    return violations


@pytest.mark.architecture
def test_owner_aware_private_module_imports(src_dir: Path) -> None:
    """Cross-owner imports of first-party private modules are forbidden in src/."""
    violations = _collect_external_private_imports(src_dir)
    observed = frozenset(violations)

    if STRICT_PRIVATE_IMPORT_GUARD:
        assert not observed, (
            "External first-party private-module imports detected in src/:\n"
            + "\n".join(
                f"  - {path}:{min(lines)} -> {module}"
                for (path, module), lines in sorted(violations.items())
            )
        )
        return

    unexpected = observed - ALLOWED_BASELINE_IMPORTS
    assert not unexpected, (
        "New external first-party private-module imports introduced:\n"
        + "\n".join(
            f"  - {path}:{min(violations[(path, module)])} -> {module}"
            for path, module in sorted(unexpected)
        )
    )
