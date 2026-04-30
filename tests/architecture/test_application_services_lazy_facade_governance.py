"""Caller-zero governance for the application services package-root lazy facade.

Issue: #3474
"""

from __future__ import annotations

import ast
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
PACKAGE_ROOT_MODULE = "bioetl.application.services"
_DIRECT_MODULE_IMPORT_SENTINEL = "<module>"

EXPECTED_TEST_IMPORTS: dict[str, frozenset[str]] = {
    "tests/e2e/test_cli_safety.py": frozenset({"PipelineRunResult"}),
    "tests/integration/interfaces/test_cli_run_dry_run.py": frozenset(
        {"PipelineRunResult", "RunResult"}
    ),
    "tests/integration/interfaces/test_cli_run_incremental.py": frozenset(
        {"PipelineRunResult", "RunResult"}
    ),
    "tests/integration/interfaces/test_cli_shutdown_integration.py": frozenset(
        {"PipelineRunResult", "RunResult"}
    ),
    "tests/unit/application/services/test_cli_run_orchestration_service.py": frozenset(
        {"PipelineRunResult", "RunResult"}
    ),
    "tests/unit/application/services/test_run_options_execution_context.py": frozenset(
        {"RunOptions"}
    ),
    "tests/unit/composition/bootstrap/cli/test_config.py": frozenset(
        {"ConfigService"}
    ),
    "tests/unit/composition/bootstrap/cli/test_service_builders.py": frozenset(
        {"CheckpointService"}
    ),
    "tests/unit/composition/bootstrap/test_checkpoint_bootstrap.py": frozenset(
        {"CheckpointService", "QuarantineService"}
    ),
    "tests/unit/composition/bootstrap/test_health_bootstrap.py": frozenset(
        {"HealthService"}
    ),
    "tests/unit/composition/bootstrap/test_runner_bootstrap.py": frozenset(
        {"PipelineRunnerService"}
    ),
    "tests/unit/composition/bootstrap/test_storage_bootstrap.py": frozenset(
        {"BronzeCleanupService", "VacuumService"}
    ),
    "tests/unit/infrastructure/config/test_workflow_config_api.py": frozenset(
        {"RunOptions"}
    ),
    "tests/unit/interfaces/cli/commands/test_debug.py": frozenset(
        {"PipelineRunResult", "RunResult"}
    ),
    "tests/unit/interfaces/cli/commands/test_execution_policy.py": frozenset(
        {"PipelineNotFoundError", "PipelineRunResult"}
    ),
    "tests/unit/interfaces/cli/commands/test_export.py": frozenset(
        {"ColumnInfo", "ExportResult", "TableInfo", "TablePreview"}
    ),
    "tests/unit/interfaces/cli/commands/test_export_support.py": frozenset(
        {"ExportOptions", "ExportResult", "TableInfo", "TablePreview"}
    ),
    "tests/unit/interfaces/cli/commands/test_run_all_command_policy.py": frozenset(
        {"RunOptions"}
    ),
    "tests/unit/interfaces/cli/commands/test_run_all_helpers.py": frozenset(
        {"PipelineRunResult", "RunResult"}
    ),
    "tests/unit/interfaces/cli/commands/test_run_command_policy.py": frozenset(
        {"PipelineNotFoundError", "PipelineRunResult", "RunResult"}
    ),
    "tests/unit/interfaces/cli/commands/test_run_result_presenter.py": frozenset(
        {"PipelineRunResult", "RunResult"}
    ),
    "tests/unit/interfaces/cli/test_cli_commands.py": frozenset(
        {"PipelineNotFoundError", "PipelineRunResult", "RunResult"}
    ),
    "tests/unit/interfaces/cli/test_cli_commands_basic.py": frozenset(
        {"PipelineNotFoundError", "PipelineRunResult", "RunOptions", "RunResult"}
    ),
    "tests/unit/interfaces/cli/test_cli_helpers.py": frozenset(
        {"PipelineRunResult", "RunOptions", "RunResult"}
    ),
    "tests/unit/interfaces/cli/test_cli_run_all_vacuum_formatters.py": frozenset(
        {
            "PipelineNotFoundError",
            "PipelineRunResult",
            "RunOptions",
            "RunResult",
            "TableVacuumResult",
            "VacuumAllResult",
        }
    ),
    "tests/unit/interfaces/cli/test_run_all_command.py": frozenset(
        {"PipelineRunResult", "RunResult"}
    ),
    "tests/unit/interfaces/cli/test_run_all_service_mock.py": frozenset(
        {"PipelineNotFoundError", "PipelineRunResult", "RunOptions", "RunResult"}
    ),
}


def _collect_imports(root: Path) -> dict[str, frozenset[str]]:
    """Collect exact imports from ``bioetl.application.services`` under ``root``."""
    collected: dict[str, set[str]] = {}

    for path in sorted(root.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError as exc:  # pragma: no cover - architecture scan safety
            raise AssertionError(f"Unable to parse {path}: {exc}") from exc

        imported_names: set[str] = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name == PACKAGE_ROOT_MODULE:
                        imported_names.add(_DIRECT_MODULE_IMPORT_SENTINEL)
            elif isinstance(node, ast.ImportFrom) and node.module == PACKAGE_ROOT_MODULE:
                imported_names.update(alias.name for alias in node.names)

        if imported_names:
            collected[path.relative_to(ROOT).as_posix()] = imported_names

    return {
        relative_path: frozenset(sorted(imported_names))
        for relative_path, imported_names in collected.items()
    }


def test_application_services_package_root_has_zero_first_party_src_callers() -> None:
    """Production code must stay off the package-root lazy compatibility facade."""
    src_imports = _collect_imports(ROOT / "src")
    assert not src_imports, (
        "First-party src imports of bioetl.application.services must stay at zero.\n"
        + "\n".join(
            f"{path}: {sorted(imported_names)}"
            for path, imported_names in sorted(src_imports.items())
        )
    )


def test_application_services_package_root_test_import_inventory_is_frozen() -> None:
    """Test-only compatibility callers must remain explicit until the facade is removed."""
    observed_test_imports = _collect_imports(ROOT / "tests")
    assert observed_test_imports == EXPECTED_TEST_IMPORTS, (
        "Application services package-root compatibility callers drifted.\n"
        "Migrate new callers to canonical owner modules or update the reviewed "
        "caller inventory when intentionally retaining a temporary test seam.\n"
        f"Observed: {observed_test_imports}\n"
        f"Expected: {EXPECTED_TEST_IMPORTS}"
    )


def test_application_services_package_root_inventory_avoids_direct_module_imports() -> (
    None
):
    """Compatibility callers must import explicit symbols, not the whole facade module."""
    observed_test_imports = _collect_imports(ROOT / "tests")
    offenders = {
        path: imported_names
        for path, imported_names in observed_test_imports.items()
        if _DIRECT_MODULE_IMPORT_SENTINEL in imported_names
    }
    assert not offenders, (
        "Tests must import explicit bioetl.application.services symbols instead of "
        "binding the whole lazy facade module.\n"
        + "\n".join(
            f"{path}: {sorted(imported_names)}"
            for path, imported_names in sorted(offenders.items())
        )
    )
