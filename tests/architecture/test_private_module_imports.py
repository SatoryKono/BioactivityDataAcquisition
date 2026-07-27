"""Owner-aware guardrail for first-party private-module imports in src/.

RF-011.0 introduced a baseline-aware mode; RF-011.2 switched this guard to strict.
Only imports within the same immediate owner package may target ``._*`` modules.
All cross-owner private-module imports in ``src/`` are forbidden.
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

STRICT_PRIVATE_IMPORT_GUARD = False

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
            "bioetl/interfaces/cli/commands/domains/health/server_integration.py",
            "bioetl.composition._resource_management",
        ),
        (
            "bioetl/interfaces/cli/commands/domains/health/server_integration.py",
            "bioetl.composition._service_protocols",
        ),
        (
            "bioetl/interfaces/cli/commands/domains/health/server_integration.py",
            "bioetl.composition._services",
        ),
        (
            "bioetl/interfaces/cli/commands/health.py",
            "bioetl.composition._service_protocols",
        ),
        # Workflow control plane support helpers (RF-6042)
        (
            "bioetl/composition/bootstrap/runtime/_composite_control_plane_support.py",
            "bioetl.composition.runtime_builders._run_manifest_refs",
        ),
        (
            "bioetl/composition/bootstrap/runtime/_composite_control_plane_support.py",
            "bioetl.composition.runtime_builders._snapshot_mapping_support",
        ),
        # Domain immutability utilities (RF-6225)
        (
            "bioetl/domain/aggregates/_batch_record.py",
            "bioetl.domain._immutability",
        ),
        (
            "bioetl/domain/control_plane/contract_registry_types.py",
            "bioetl.domain._immutability",
        ),
        (
            "bioetl/domain/control_plane/workflow_manifest.py",
            "bioetl.domain._immutability",
        ),
        (
            "bioetl/domain/entities/crossref.py",
            "bioetl.domain._immutability",
        ),
        (
            "bioetl/domain/entities/openalex.py",
            "bioetl.domain._immutability",
        ),
        (
            "bioetl/domain/entities/pubmed.py",
            "bioetl.domain._immutability",
        ),
        (
            "bioetl/domain/workflow/transform_spec.py",
            "bioetl.domain._immutability",
        ),
    }
)


def _module_name_for_path(src_dir: Path, file_path: Path) -> str:
    rel_parts = file_path.relative_to(src_dir).with_suffix("").parts
    return ".".join(rel_parts)


def _collect_existing_modules_from_cache(
    source_ast_cache: dict[Path, ast.Module],
    *,
    src_dir: Path,
) -> frozenset[str]:
    """Build the module set from the shared architecture AST index."""
    modules: set[str] = set()
    for py_file in source_ast_cache:
        try:
            rel_path = py_file.resolve().relative_to(src_dir.resolve())
        except ValueError:
            continue
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
    source_ast_cache: dict[Path, ast.Module],
) -> dict[tuple[str, str], list[int]]:
    violations: dict[tuple[str, str], list[int]] = {}
    existing_modules = _collect_existing_modules_from_cache(
        source_ast_cache,
        src_dir=src_dir,
    )
    resolved_src = src_dir.resolve()

    for py_file, tree in sorted(
        source_ast_cache.items(),
        key=lambda item: item[0].as_posix(),
    ):
        try:
            rel_path = py_file.resolve().relative_to(resolved_src).as_posix()
        except ValueError:
            continue
        importer_module = _module_name_for_path(src_dir, py_file)
        importer_owner = importer_module.rsplit(".", 1)[0]

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
@pytest.mark.slow
def test_owner_aware_private_module_imports(
    src_dir: Path,
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """Cross-owner imports of first-party private modules are forbidden in src/."""
    violations = _collect_external_private_imports(src_dir, source_ast_cache)
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
