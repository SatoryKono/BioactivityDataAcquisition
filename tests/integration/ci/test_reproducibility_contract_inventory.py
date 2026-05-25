"""Split inventory and deterministic bundle owner tests for the reproducibility contract suite."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import polars as pl

from bioetl.application.services.control_plane.run_manifest_inspection_service import (
    RunManifestInspectionService,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.control_plane.reproducibility_profiles import (
    published_reproducibility_family_inventory,
)
from bioetl.domain.types import RunID
from tests.integration.ci.test_reproducibility_contract_suite import (
    _InMemoryRunLedgerStore,
    _InMemoryRunManifestStore,
    _PUBLISHED_PRODUCTION_FAMILIES,
    _deduplicate_by_primary_keys_impl,
    _make_manifest,
    _make_merge_metrics_mixin,
)


def test_reproducibility_contract_inventory_covers_all_production_families() -> None:
    entity_families = {
        f"{path.parent.name}.{path.stem}"
        for path in Path("configs/entities").glob("*/*.yaml")
    }
    composite_families = {
        f"composite.{path.stem}" for path in Path("configs/composites").glob("*.yaml")
    }

    assert set(_PUBLISHED_PRODUCTION_FAMILIES) == entity_families | composite_families


def test_reproducibility_contract_inventory_profiles_all_production_families() -> None:
    inventory = published_reproducibility_family_inventory()
    profile_by_family = {str(item["family"]): item for item in inventory}

    assert set(profile_by_family) == set(_PUBLISHED_PRODUCTION_FAMILIES)
    assert profile_by_family["chembl.activity"]["strict_exact_replay_supported"] is True
    assert profile_by_family["chembl.activity"]["strict_replay_runtime_verdict"] == (
        "allowed_with_snapshot_backed_source_refs"
    )
    assert (
        profile_by_family["openalex.publication"]["strict_exact_replay_supported"]
        is True
    )
    assert (
        profile_by_family["openalex.publication"]["strict_replay_runtime_verdict"]
        == "allowed_with_snapshot_backed_source_refs"
    )
    assert (
        profile_by_family["composite.publication"]["exact_replay_support_boundary"]
        == "composite_snapshot_backed_input_envelope"
    )
    assert (
        profile_by_family["composite.publication"]["strict_replay_runtime_verdict"]
        == "requires_full_composite_snapshot_envelope"
    )
    assert profile_by_family["composite.publication"]["lineage_closure_supported"] is (
        True
    )


def test_reproducibility_contract_silver_batch_dedup_is_order_insensitive() -> None:
    forward = [
        {"id": "1", "value": "winner", "content_hash": "a-hash"},
        {"id": "1", "value": "loser", "content_hash": "z-hash"},
    ]
    reverse = list(reversed(forward))
    expected = [{"id": "1", "value": "winner", "content_hash": "a-hash"}]

    assert _deduplicate_by_primary_keys_impl(forward, ["id"]) == expected
    assert _deduplicate_by_primary_keys_impl(reverse, ["id"]) == expected


def test_reproducibility_contract_composite_rows_exclude_runtime_anchors() -> None:
    mixin = _make_merge_metrics_mixin()
    df = pl.DataFrame({"doi": ["10.1/a"]})
    metadata_timestamp = datetime(2025, 2, 3, 0, 0, tzinfo=UTC)

    first = mixin._add_lineage(
        df,
        enrichment_results={},
        run_id="run-left",
        metadata_timestamp=metadata_timestamp,
        sources_used=["seed"],
    )
    second = mixin._add_lineage(
        df,
        enrichment_results={},
        run_id="run-right",
        metadata_timestamp=metadata_timestamp,
        sources_used=["seed"],
    )

    assert "_composite_run_id" not in first.columns
    assert "_lineage_created_at" not in first.columns
    assert first.columns == second.columns


def test_reproducibility_contract_composite_quarantine_is_explicitly_occurrence_only() -> (
    None
):
    manifest_store = _InMemoryRunManifestStore()
    ledger_store = _InMemoryRunLedgerStore()
    run_id = RunID(UUID("00000000-0000-0000-0000-000000000402"))
    manifest = _make_manifest(
        manifest_id="manifest-composite-quarantine",
        run_id=run_id,
        execution_fingerprint="fp-stable",
    )
    manifest_store.save(manifest)
    ledger_store.append(
        RunLedgerEntry(
            entry_id="entry-composite-cv-1",
            manifest_id=manifest.manifest_id,
            run_id=run_id,
            event_type="dq_policy_applied",
            occurred_at=datetime(2025, 2, 3, tzinfo=UTC),
            event_family="dq",
            status="quarantined",
            stage="cross_validation",
            details={
                "rule_id": "composite.cross_validation.quarantine",
                "disposition": "quarantine",
                "violation_kind": "cross_validation_mismatch",
                "config_path": "cross_validation",
                "artifact_policy": "occurrence_only_diagnostic",
                "replay_contract": "excluded_from_exact_replay",
                "diagnostic_scope": "composite_cross_validation_quarantine",
            },
        )
    )

    result = RunManifestInspectionService(
        manifest_port=manifest_store,
        ledger_port=ledger_store,
    ).show(manifest.manifest_id)

    assert (
        result.diagnostics["cross_validation_quarantine_policy"]
        == "occurrence_only_diagnostic"
    )
    assert (
        result.diagnostics["cross_validation_quarantine_replay_contract"]
        == "excluded_from_exact_replay"
    )
    assert result.diagnostics["occurrence_only_diagnostics"] == [
        "composite_cross_validation_quarantine"
    ]
    assert result.identity_graph["occurrence_only_diagnostics"] == [
        "composite_cross_validation_quarantine"
    ]
