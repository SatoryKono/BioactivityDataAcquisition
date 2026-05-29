"""Contract tests for control-plane responsibility facades."""

from __future__ import annotations

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


def test_flat_control_plane_paths_are_compatibility_wrappers_only() -> None:
    """Legacy module paths should only re-export ownership-package implementations."""
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
        source = (root / wrapper).read_text(encoding="utf-8")
        assert "Compatibility wrapper" in source
        assert source.count("from bioetl.application.services.control_plane.") == 1
