"""Guardrails for removed application.services facade modules."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
from tests.helpers.compat_shim_guards import (
    find_lingering_files,
    iter_compat_import_violations,
)

ROOT = Path(__file__).resolve().parents[2]
REMOVED_FACADE_MODULES = frozenset(
    {
        "bioetl.application.services.cli_run_orchestration_service",
        "bioetl.application.services.lineage_inspection_service",
        "bioetl.application.services.metadata_coordinator",
        "bioetl.application.services.run_ledger_service",
        "bioetl.application.services.run_manifest_inspection_service",
        "bioetl.application.services.cli_run_orchestration_contracts",
        "bioetl.application.services.cli_run_orchestration_models",
        "bioetl.application.services.pipeline_run_context_service",
        "bioetl.application.services.pipeline_run_execution_service",
        "bioetl.application.services.pipeline_run_lifecycle_service",
        "bioetl.application.services.pipeline_runner_models",
        "bioetl.application.services.pipeline_runner_service",
        "bioetl.application.services.checkpoint_compatibility_runtime",
        "bioetl.application.services.run_manifest_diagnostics",
    }
)
REMOVED_FACADE_FILES = frozenset(
    {
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "cli_run_orchestration_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "lineage_inspection_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "metadata_coordinator.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "run_ledger_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "run_manifest_inspection_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "cli_run_orchestration_contracts.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "cli_run_orchestration_models.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "pipeline_run_context_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "pipeline_run_execution_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "pipeline_run_lifecycle_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "pipeline_runner_models.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "execution/pipeline_runner_service.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "checkpoint_compatibility_runtime.py",
        ROOT
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "run_manifest_diagnostics.py",
    }
)
REMOVED_FACADE_PARENT_IMPORTS = {
    "bioetl.application.services": frozenset(
        {
            "cli_run_orchestration_service",
            "cli_run_orchestration_contracts",
            "cli_run_orchestration_models",
            "lineage_inspection_service",
            "metadata_coordinator",
            "pipeline_run_context_service",
            "pipeline_run_execution_service",
            "pipeline_run_lifecycle_service",
            "pipeline_runner_models",
            "pipeline_runner_service",
            "checkpoint_compatibility_runtime",
            "run_ledger_service",
            "run_manifest_diagnostics",
            "run_manifest_inspection_service",
        }
    ),
}


@pytest.mark.architecture
def test_removed_application_services_facade_file_stays_absent() -> None:
    """Removed application.services facade file must not return."""
    lingering = find_lingering_files(root=ROOT, removed_files=REMOVED_FACADE_FILES)
    assert not lingering, (
        "application.services facade file must stay removed:\n"
        + "\n".join(lingering)
    )


@pytest.mark.architecture
def test_removed_application_services_facade_is_not_used_in_src(
    source_ast_cache: dict[Path, ast.Module],
) -> None:
    """First-party src must import canonical owners directly."""
    violations = iter_compat_import_violations(
        ast_cache=source_ast_cache,
        root=ROOT,
        compat_modules=REMOVED_FACADE_MODULES,
        compat_parent_imports=REMOVED_FACADE_PARENT_IMPORTS,
    )
    assert not violations, (
        "removed application.services facade leaked into first-party src imports:\n"
        + "\n".join(violations)
    )


@pytest.mark.architecture
def test_removed_application_services_facade_is_not_used_in_tests(
    test_ast_cache: dict[Path, ast.Module],
) -> None:
    """Tests must not keep importing the removed application.services facade."""
    violations = iter_compat_import_violations(
        ast_cache=test_ast_cache,
        root=ROOT,
        compat_modules=REMOVED_FACADE_MODULES,
        compat_parent_imports=REMOVED_FACADE_PARENT_IMPORTS,
    )
    assert not violations, (
        "removed application.services facade must stay absent from tests:\n"
        + "\n".join(violations)
    )
