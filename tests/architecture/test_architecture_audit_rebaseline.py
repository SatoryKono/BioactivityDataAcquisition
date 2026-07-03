"""Guard current runtime topology against stale architecture-audit assumptions."""

from __future__ import annotations

from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

CURRENT_RUNTIME_SURFACES = (
    ROOT / "src" / "bioetl" / "application" / "composite" / "merger.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "composite"
    / "runner_pkg"
    / "runner.py",
    ROOT / "src" / "bioetl" / "domain" / "composite" / "state.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "checkpoint_compatibility_service.py",
    ROOT / "src" / "bioetl" / "domain" / "transformations" / "hashing.py",
    ROOT
    / "src"
    / "bioetl"
    / "domain"
    / "aggregates"
    / "_pipeline_run_mixins.py",
    ROOT / "src" / "bioetl" / "domain" / "aggregates" / "_batch_lifecycle.py",
)

STALE_ASSUMPTION_PATHS = (
    ROOT / "src" / "bioetl" / "application" / "composite_pipeline.py",
    ROOT / "src" / "bioetl" / "infrastructure" / "chembl_client.py",
    ROOT / "src" / "bioetl" / "infrastructure" / "pubchem_client.py",
)


@pytest.mark.architecture
def test_current_architecture_runtime_surfaces_exist() -> None:
    missing = [
        str(path.relative_to(ROOT))
        for path in CURRENT_RUNTIME_SURFACES
        if not path.exists()
    ]
    assert not missing, (
        "Current runtime topology changed; refresh architecture-audit assumptions for:\n"
        + "\n".join(missing)
    )


@pytest.mark.architecture
def test_stale_audit_greenfield_and_legacy_paths_stay_absent() -> None:
    lingering = [
        str(path.relative_to(ROOT))
        for path in STALE_ASSUMPTION_PATHS
        if path.exists()
    ]
    assert not lingering, (
        "Stale audit-only paths should stay absent so architecture checks remain "
        "calibrated to current topology:\n" + "\n".join(lingering)
    )
