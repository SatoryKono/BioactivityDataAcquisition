"""Sunset enforcement for backward-compatibility shims.

Tracks active sunset items and removed shims. Active items count toward the
compatibility debt scorecard. Removed shims stay under an absence guard so the
compatibility surface cannot reappear silently.

Sunset date: 2026-06-30 (see PLAN-001).
"""

from __future__ import annotations

import ast
from datetime import date
from importlib import import_module
from pathlib import Path

import pytest

from scripts.engineering.qa.file_discovery import discover_files

ROOT = Path(__file__).resolve().parents[2]
SUNSET_DATE = date(2026, 6, 30)
POLICY_REVIEW_DATE = date(2026, 5, 15)
REMOVED_CHECKPOINT_COMPATIBILITY_V2_MODULE = (
    "bioetl.application.services.checkpoint_compatibility_service_v2"
)
REMOVED_CHECKPOINT_COMPATIBILITY_V2_PATH = (
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "checkpoint_compatibility_service_v2.py"
)
BASE_PIPELINE_CONFIG = ROOT / "configs" / "base" / "pipeline.yaml"

# Active sunset items. The 2026-04-29 removal wave retired all previously
# tracked entries early with explicit maintainer approval.
COMPAT_FILES: dict[str, Path] = {}
COMPAT_MODULES: dict[str, Path] = {}

REMOVED_COMPAT_MODULES: dict[str, Path] = {
    "application services cli_run_orchestration_service facade": Path(
        "src/bioetl/application/services/cli_run_orchestration_service.py"
    ),
    "application services cli_run_orchestration_contracts facade": Path(
        "src/bioetl/application/services/cli_run_orchestration_contracts.py"
    ),
    "application services cli_run_orchestration_models facade": Path(
        "src/bioetl/application/services/cli_run_orchestration_models.py"
    ),
    "application services lineage_inspection_service facade": Path(
        "src/bioetl/application/services/lineage_inspection_service.py"
    ),
    "application services metadata_coordinator facade": Path(
        "src/bioetl/application/services/metadata_coordinator.py"
    ),
    "application services run_ledger_service facade": Path(
        "src/bioetl/application/services/run_ledger_service.py"
    ),
    "application services run_manifest_inspection_service facade": Path(
        "src/bioetl/application/services/run_manifest_inspection_service.py"
    ),
    "application services pipeline_run_context_service facade": Path(
        "src/bioetl/application/services/pipeline_run_context_service.py"
    ),
    "application services pipeline_run_execution_service facade": Path(
        "src/bioetl/application/services/pipeline_run_execution_service.py"
    ),
    "application services pipeline_run_lifecycle_service facade": Path(
        "src/bioetl/application/services/pipeline_run_lifecycle_service.py"
    ),
    "application services pipeline_runner_models facade": Path(
        "src/bioetl/application/services/pipeline_runner_models.py"
    ),
    "application services pipeline_runner_service facade": Path(
        "src/bioetl/application/services/pipeline_runner_service.py"
    ),
    "application services checkpoint_compatibility_runtime facade": Path(
        "src/bioetl/application/services/checkpoint_compatibility_runtime.py"
    ),
    "application services run_manifest_diagnostics facade": Path(
        "src/bioetl/application/services/run_manifest_diagnostics.py"
    ),
    "application services effective_config_service facade": Path(
        "src/bioetl/application/services/effective_config_service.py"
    ),
    "application services run_manifest_service facade": Path(
        "src/bioetl/application/services/run_manifest_service.py"
    ),
    "cli inspection_output compat wrapper": Path(
        "src/bioetl/interfaces/cli/commands/inspection_output.py"
    ),
    "cli run_manifest_output compat wrapper": Path(
        "src/bioetl/interfaces/cli/commands/run_manifest_output.py"
    ),
    "cli maintenance plan facade": Path("src/bioetl/interfaces/cli/commands/plan.py"),
    "aggregate_port.py (StoragePort)": Path(
        "src/bioetl/domain/ports/storage/aggregate_port.py"
    ),
    "domain normalization_authors compat wrapper": Path(
        "src/bioetl/domain/normalization_authors.py"
    ),
    "domain normalization_pages compat wrapper": Path(
        "src/bioetl/domain/normalization_pages.py"
    ),
    "domain normalization_dates compat wrapper": Path(
        "src/bioetl/domain/normalization_dates.py"
    ),
    "domain normalization_chembl compat wrapper": Path(
        "src/bioetl/domain/normalization_chembl.py"
    ),
    "domain publication_field_groups facade": Path(
        "src/bioetl/domain/value_objects/publication_field_groups.py"
    ),
    "domain services doi_normalization compat wrapper": Path(
        "src/bioetl/domain/services/doi_normalization.py"
    ),
    "domain services pmid_normalization compat wrapper": Path(
        "src/bioetl/domain/services/pmid_normalization.py"
    ),
    "domain services date_normalization compat wrapper": Path(
        "src/bioetl/domain/services/date_normalization.py"
    ),
    "domain services text_normalization compat wrapper": Path(
        "src/bioetl/domain/services/text_normalization.py"
    ),
    "domain services _date_helpers compat wrapper": Path(
        "src/bioetl/domain/services/_date_helpers.py"
    ),
    "application checkpoint legacy wrapper": Path(
        "src/bioetl/application/core/lifecycle/_checkpoint_legacy.py"
    ),
}


@pytest.mark.parametrize("name,path", COMPAT_FILES.items(), ids=COMPAT_FILES.keys())
def test_compat_file_sunset(name: str, path: Path) -> None:
    """Before sunset: compat file MUST exist. After sunset: MUST be removed."""
    today = POLICY_REVIEW_DATE
    exists = path.exists()

    if today <= SUNSET_DATE:
        assert exists, (
            f"Compat file {name} was removed before sunset date {SUNSET_DATE}. "
            f"If intentional, remove this test entry."
        )
    else:
        assert not exists, (
            f"Compat file {name} still exists after sunset date {SUNSET_DATE}. "
            f"Migrate callers to canonical imports and remove the file."
        )


@pytest.mark.parametrize("name,path", COMPAT_MODULES.items(), ids=COMPAT_MODULES.keys())
def test_compat_module_sunset(name: str, path: Path) -> None:
    """Before sunset: compat module MUST exist. After sunset: MUST be removed."""
    today = POLICY_REVIEW_DATE
    exists = path.exists()

    if today <= SUNSET_DATE:
        assert exists, (
            f"Compat module {name} was removed before sunset date {SUNSET_DATE}. "
            f"If intentional, remove this test entry."
        )
    else:
        assert not exists, (
            f"Compat module {name} still exists after sunset date {SUNSET_DATE}. "
            f"Migrate consumers to narrow ports and remove the aggregate."
        )


@pytest.mark.parametrize(
    "name,path",
    REMOVED_COMPAT_MODULES.items(),
    ids=REMOVED_COMPAT_MODULES.keys(),
)
def test_removed_compat_module_stays_removed(name: str, path: Path) -> None:
    """Removed compatibility modules must not be reintroduced."""
    assert not path.exists(), (
        f"Removed compatibility module {name} exists again at {path}. "
        "Use the canonical narrow-port or normalization surface instead."
    )


def _find_importers(root: Path, module_name: str) -> list[str]:
    violations: list[str] = []
    for relative_path in discover_files(str(root.resolve()), ".py"):
        path = root / relative_path
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                names = {alias.name for alias in node.names}
                if module_name in names:
                    violations.append(path.relative_to(ROOT).as_posix())
                    break
            if isinstance(node, ast.ImportFrom) and node.module == module_name:
                violations.append(path.relative_to(ROOT).as_posix())
                break
    return violations


@pytest.mark.architecture
def test_checkpoint_compatibility_v2_surface_stays_removed_and_unimportable() -> None:
    """Removed checkpoint compatibility V2 surface must stay absent everywhere."""
    assert not REMOVED_CHECKPOINT_COMPATIBILITY_V2_PATH.exists()
    with pytest.raises(ModuleNotFoundError):
        import_module(REMOVED_CHECKPOINT_COMPATIBILITY_V2_MODULE)
    assert not _find_importers(ROOT / "src", REMOVED_CHECKPOINT_COMPATIBILITY_V2_MODULE)
    assert not _find_importers(
        ROOT / "tests", REMOVED_CHECKPOINT_COMPATIBILITY_V2_MODULE
    )


@pytest.mark.architecture
def test_removed_pipeline_base_yaml_fallback_surface_stays_absent() -> None:
    """Historical pipeline base fallback path must not silently return."""
    text = BASE_PIPELINE_CONFIG.read_text(encoding="utf-8")
    assert "configs/pipelines/_base.yaml" not in text
    assert not (ROOT / "configs" / "pipelines").exists()
