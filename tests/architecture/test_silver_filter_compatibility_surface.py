"""Guardrails for retired Silver filter compatibility modes."""

from __future__ import annotations

from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
ACTIVE_SURFACES = (
    ROOT / "src" / "bioetl" / "domain" / "config" / "runtime.py",
    ROOT / "src" / "bioetl" / "domain" / "normalization" / "_control_plane_identity.py",
    ROOT / "src" / "bioetl" / "domain" / "types" / "checkpoint_metadata.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "core"
    / "lifecycle"
    / "checkpoint_runtime.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "control_plane"
    / "manifest"
    / "_service_support.py",
    ROOT
    / "src"
    / "bioetl"
    / "application"
    / "services"
    / "control_plane"
    / "manifest"
    / "identity_graph_assembly.py",
    ROOT
    / "src"
    / "bioetl"
    / "composition"
    / "runtime_builders"
    / "run_manifest_contract_identity.py",
    ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "config"
    / "silver_filter_migration.py",
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "filter_config_loader.py",
    ROOT / "docs" / "filters" / "ADR-048-silver-filters-structural-scope.md",
    ROOT / "docs" / "filters" / "migration-plan.md",
    ROOT
    / "docs"
    / "02-architecture"
    / "decisions"
    / "ADR-050-silver-structural-gold-semantic-filter-boundary.md",
)


@pytest.mark.architecture
def test_active_silver_filter_surfaces_do_not_expose_retired_legacy_mode() -> None:
    forbidden_tokens = (
        "legacy_semantic_silver",
        "BIOETL_LEGACY_SILVER_SEMANTIC",
    )
    violations: list[str] = []
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}: {token}")

    assert not violations, (
        "Active Silver filter surfaces must not expose retired legacy mode "
        "tokens:\n" + "\n".join(violations)
    )


@pytest.mark.architecture
def test_silver_filter_identity_surfaces_do_not_add_deferred_or_duplicate_mode_fields() -> (
    None
):
    forbidden_tokens = (
        "source_profile_version",
        "silver_filter_mode",
        "silver_filter_runtime_mode",
        "silver_filter_semantic_mode",
        "silver_filter_execution_mode",
    )
    violations: list[str] = []
    for path in ACTIVE_SURFACES:
        text = path.read_text(encoding="utf-8")
        for token in forbidden_tokens:
            if token in text:
                violations.append(f"{path.relative_to(ROOT)}: {token}")

    assert not violations, (
        "Silver filter execution identity must use only "
        "'silver_filter_compatibility_mode'; deferred or duplicate fields found:\n"
        + "\n".join(violations)
    )
