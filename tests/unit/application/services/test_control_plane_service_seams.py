"""Contract tests for control-plane responsibility facades."""

from __future__ import annotations

import pytest

from pathlib import Path

from bioetl.application.services.control_plane import (
    EffectiveConfigService,
    RunLedgerService,
    RunManifestService,
    WorkflowExecutionService,
)
from bioetl.application.services.control_plane.effective_config import (
    EffectiveConfigService as EffectiveConfigSeamService,
)
from bioetl.application.services.control_plane.ledger import (
    RunLedgerService as LedgerSeamService,
)
from bioetl.application.services.control_plane.manifest import (
    RunManifestService as ManifestSeamService,
)
from bioetl.application.services.control_plane.replay import (
    HistoricalReplayCertificationService,
    build_run_replay_bundle_descriptor,
)
from bioetl.application.services.control_plane.workflow import (
    WorkflowExecutionService as WorkflowSeamExecutionService,
)
import bioetl.application.services.control_plane as control_plane_root


pytestmark = pytest.mark.unit

EXPECTED_RESPONSIBILITY_SEAMS = {
    "effective_config",
    "ledger",
    "manifest",
    "replay",
    "workflow",
}


def test_control_plane_responsibility_facades_preserve_canonical_exports() -> None:
    """New responsibility seams must not fork existing service classes."""
    assert ManifestSeamService is RunManifestService
    assert LedgerSeamService is RunLedgerService
    assert EffectiveConfigSeamService is EffectiveConfigService
    assert WorkflowSeamExecutionService is WorkflowExecutionService


def test_control_plane_replay_facade_exposes_replay_services() -> None:
    """Replay seam groups historical replay and descriptor entrypoints."""
    assert HistoricalReplayCertificationService.__name__ == (
        "HistoricalReplayCertificationService"
    )
    assert callable(build_run_replay_bundle_descriptor)


def test_control_plane_services_live_under_ownership_packages() -> None:
    """Canonical service modules must not remain in the flat package surface."""
    ownership_modules = {
        EffectiveConfigSeamService.__module__,
        LedgerSeamService.__module__,
        ManifestSeamService.__module__,
        HistoricalReplayCertificationService.__module__,
        WorkflowSeamExecutionService.__module__,
    }

    assert ownership_modules == {
        "bioetl.application.services.control_plane.effective_config.service",
        "bioetl.application.services.control_plane.ledger.service",
        "bioetl.application.services.control_plane.manifest.service",
        "bioetl.application.services.control_plane.replay.historical_certification_service",
        "bioetl.application.services.control_plane.workflow.execution_service",
    }


def test_control_plane_root_documents_explicit_responsibility_seams() -> None:
    """The package root must stay a compatibility facade over explicit use cases."""
    doc = control_plane_root.__doc__ or ""

    for seam in EXPECTED_RESPONSIBILITY_SEAMS:
        assert seam in doc


def test_control_plane_root_lazy_exports_target_responsibility_seams() -> None:
    """Root lazy exports must route to use-case owner packages, not flat wrappers."""
    lazy_exports = control_plane_root._LAZY_ATTR_EXPORTS
    allowed_module_prefixes = (
        *(
            f"bioetl.application.services.control_plane.{seam}."
            for seam in EXPECTED_RESPONSIBILITY_SEAMS
        ),
        "bioetl.application.services.control_plane.forensic_diff_service",
    )

    assert lazy_exports
    for export_name, target in lazy_exports.items():
        target_module = target[0]
        assert target_module.startswith(allowed_module_prefixes), (
            f"{export_name} must point to an explicit control-plane owner seam, "
            f"not {target_module}"
        )


def test_removed_flat_control_plane_compatibility_wrappers_stay_absent() -> None:
    """Removed flat compatibility wrappers must not return under control_plane/."""
    root = (
        Path(__file__).resolve().parents[4]
        / "src"
        / "bioetl"
        / "application"
        / "services"
        / "control_plane"
    )
    wrappers = (
        "effective_config_service.py",
        "run_ledger_service.py",
        "run_manifest_service.py",
    )

    for wrapper in wrappers:
        assert not (root / wrapper).exists()
