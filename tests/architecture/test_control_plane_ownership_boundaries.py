"""Architecture guard for control-plane responsibility package ownership."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
CONTROL_PLANE_ROOT = (
    PROJECT_ROOT / "src" / "bioetl" / "application" / "services" / "control_plane"
)

APPROVED_FLAT_CONTROL_PLANE_MODULES = frozenset(
    {
        "__init__.py",
        "_lazy_export_facade.py",
        "effective_config_service.py",
        "effective_config_support.py",
        "forensic_diff_service.py",
        "run_ledger_service.py",
        "run_manifest_diagnostics_support.py",
        "run_manifest_exact_replay_blockers.py",
        "run_manifest_reproducibility_claims.py",
        "run_manifest_reproducibility_score_cards.py",
        "run_manifest_reproducibility_scoring.py",
        "run_manifest_reproducibility_scoring_support.py",
        "run_manifest_service.py",
    }
)

REQUIRED_RESPONSIBILITY_PACKAGES = frozenset(
    {
        "effective_config",
        "ledger",
        "manifest",
        "replay",
        "workflow",
    }
)


@pytest.mark.architecture
def test_control_plane_flat_root_does_not_gain_unowned_modules() -> None:
    """New control-plane modules must land in responsibility subpackages."""
    current_root_modules = frozenset(
        path.name for path in CONTROL_PLANE_ROOT.glob("*.py")
    )

    assert current_root_modules <= APPROVED_FLAT_CONTROL_PLANE_MODULES, (
        "Unowned flat control-plane modules detected; place new code under "
        "effective_config/, ledger/, manifest/, replay/, or workflow/: "
        f"{sorted(current_root_modules - APPROVED_FLAT_CONTROL_PLANE_MODULES)}"
    )


@pytest.mark.architecture
def test_control_plane_responsibility_packages_are_present() -> None:
    """Issue #4610 ownership seams must stay materialized as packages."""
    missing = [
        package_name
        for package_name in sorted(REQUIRED_RESPONSIBILITY_PACKAGES)
        if not (CONTROL_PLANE_ROOT / package_name / "__init__.py").is_file()
    ]

    assert missing == []


@pytest.mark.architecture
def test_manifest_replay_payload_helpers_are_not_flat_root_modules() -> None:
    """Manifest replay projection helpers must stay under the manifest seam."""
    assert not (
        CONTROL_PLANE_ROOT / "_run_manifest_replay_family_contract_payload.py"
    ).exists()
    assert (
        CONTROL_PLANE_ROOT / "manifest" / "replay_family_contract_payload.py"
    ).is_file()
    assert not (CONTROL_PLANE_ROOT / "run_manifest_replay_taxonomy.py").exists()
    assert (CONTROL_PLANE_ROOT / "manifest" / "replay_taxonomy.py").is_file()
    assert not (CONTROL_PLANE_ROOT / "_run_manifest_replay_taxonomy_fields.py").exists()
    assert (CONTROL_PLANE_ROOT / "manifest" / "replay_taxonomy_fields.py").is_file()


@pytest.mark.architecture
def test_ledger_entry_support_implementation_is_not_flat_root_module() -> None:
    """Ledger entry helpers must be implemented under the ledger seam."""
    assert not (CONTROL_PLANE_ROOT / "_run_ledger_diagnostic_support.py").exists()
    assert (CONTROL_PLANE_ROOT / "ledger" / "diagnostic_support.py").is_file()
    assert (CONTROL_PLANE_ROOT / "ledger" / "entry_support.py").is_file()
    assert (CONTROL_PLANE_ROOT / "ledger" / "core_events.py").is_file()
    assert (CONTROL_PLANE_ROOT / "ledger" / "rich_events.py").is_file()


@pytest.mark.architecture
def test_effective_config_context_helpers_are_not_flat_root_modules() -> None:
    """Effective-config context helpers must be implemented under its seam."""
    assert not (CONTROL_PLANE_ROOT / "_effective_config_provenance_support.py").exists()
    assert (CONTROL_PLANE_ROOT / "effective_config" / "context.py").is_file()
    assert (CONTROL_PLANE_ROOT / "effective_config" / "provenance_support.py").is_file()
    assert (CONTROL_PLANE_ROOT / "effective_config" / "support.py").is_file()


@pytest.mark.architecture
def test_manifest_validation_implementation_is_not_flat_root_module() -> None:
    """Run-manifest validation implementation must live under manifest seam."""
    assert (CONTROL_PLANE_ROOT / "manifest" / "validation.py").is_file()
    assert (CONTROL_PLANE_ROOT / "manifest" / "artifact_payloads.py").is_file()
    assert (CONTROL_PLANE_ROOT / "manifest" / "service_scaffold.py").is_file()


@pytest.mark.architecture
def test_historical_replay_closure_claims_are_replay_owned() -> None:
    """Historical replay closure claim helpers must live under replay seam."""
    assert (CONTROL_PLANE_ROOT / "replay" / "closure_claims.py").is_file()


@pytest.mark.architecture
def test_manifest_inspection_helpers_are_not_flat_root_modules() -> None:
    """Run-manifest inspection helpers must be implemented under manifest seam."""
    assert not (
        CONTROL_PLANE_ROOT / "_run_manifest_inspection_artifact_refs.py"
    ).exists()
    assert (CONTROL_PLANE_ROOT / "manifest" / "inspection_artifact_refs.py").is_file()
    assert (CONTROL_PLANE_ROOT / "manifest" / "inspection_helpers.py").is_file()
    assert (CONTROL_PLANE_ROOT / "manifest" / "inspection_verification.py").is_file()


@pytest.mark.architecture
def test_manifest_diagnostics_helpers_are_owned_by_manifest_package() -> None:
    """Run-manifest diagnostics implementations must live under manifest seam."""
    owned_modules = {
        "composite_projection.py",
        "ledger_processing.py",
        "main_helpers.py",
        "persistence.py",
        "persistence_alerts.py",
        "persistence_profile_support.py",
        "persistence_profiles.py",
        "replay_helpers.py",
        "replay_state.py",
        "summary.py",
    }
    diagnostics_root = CONTROL_PLANE_ROOT / "manifest" / "diagnostics"

    missing = [
        module_name
        for module_name in sorted(owned_modules)
        if not (diagnostics_root / module_name).is_file()
    ]

    assert missing == []
