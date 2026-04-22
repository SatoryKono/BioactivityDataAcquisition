"""Unit tests for composite control-plane payload builders."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from bioetl.composition.bootstrap.runtime._composite_control_plane_payloads import (
    build_composite_launch_context_snapshot,
    build_composite_planned_artifacts,
    build_composite_resolved_config_snapshot,
    build_composite_runtime_config_snapshot,
    build_composite_source_refs,
)


def _build_config() -> SimpleNamespace:
    return SimpleNamespace(
        name="publications",
        seed=SimpleNamespace(pipeline="pubmed_publications"),
        dependencies=[SimpleNamespace(pipeline="crossref_publications")],
        enrichers=[SimpleNamespace(pipeline="openalex_publications")],
        merge=SimpleNamespace(
            output_silver_path="silver/publications",
            output_gold_path="gold/publications",
        ),
    )


def _build_runtime() -> SimpleNamespace:
    return SimpleNamespace(
        resume=True,
        dry_run=False,
        required_only=True,
        force_enricher="openalex_publications",
        seed_limit=50,
        enrich_only=("openalex_publications",),
        use_cached_bronze=True,
        cached_bronze_path="bronze/cache",
        cached_bronze_date="2026-04-01",
        cached_bronze_enrichers=("openalex_publications",),
        cached_bronze_dependencies=("crossref_publications",),
    )


@pytest.mark.unit
def test_build_composite_launch_context_snapshot_returns_runtime_sensitive_fields() -> (
    None
):
    config = _build_config()
    runtime = _build_runtime()

    result = build_composite_launch_context_snapshot(
        config,
        runtime,
        required_persistence_profile="degraded_observable",
    )

    assert result["pipeline_name"] == "publications"
    assert result["execution_context"] == "composite"
    assert (
        result["exact_replay_support_boundary"]
        == "composite_snapshot_backed_input_envelope"
    )
    assert result["required_persistence_profile"] == "degraded_observable"
    assert result["required_only"] is True
    assert result["seed_limit"] == 50
    assert result["enrich_only"] == ["openalex_publications"]
    assert result["cached_bronze_dependencies"] == ("crossref_publications",)


@pytest.mark.unit
def test_build_composite_source_refs_preserves_seed_dependency_and_enricher_order() -> (
    None
):
    config = _build_config()

    result = build_composite_source_refs(config)

    assert [ref.pipeline_name for ref in result] == [
        "pubmed_publications",
        "crossref_publications",
        "openalex_publications",
    ]
    assert [(ref.provider, ref.entity) for ref in result] == [
        ("pubmed", "publications"),
        ("crossref", "publications"),
        ("openalex", "publications"),
    ]


@pytest.mark.unit
def test_build_composite_planned_artifacts_returns_silver_then_gold_targets() -> None:
    config = _build_config()

    result = build_composite_planned_artifacts(config)

    assert [(artifact.layer, artifact.path) for artifact in result] == [
        ("silver", "silver/publications"),
        ("gold", "gold/publications"),
    ]


@pytest.mark.unit
def test_build_composite_runtime_config_snapshot_normalizes_sequences() -> None:
    runtime = _build_runtime()

    result = build_composite_runtime_config_snapshot(runtime)

    assert result["resume"] is True
    assert result["enrich_only"] == ["openalex_publications"]
    assert result["cached_bronze_enrichers"] == ["openalex_publications"]
    assert result["cached_bronze_dependencies"] == ["crossref_publications"]


@pytest.mark.unit
def test_build_composite_resolved_config_snapshot_normalizes_nested_payloads() -> None:
    config = _build_config()

    result = build_composite_resolved_config_snapshot(config)

    assert result["name"] == "publications"
    assert result["seed"] == {"pipeline": "pubmed_publications"}
    assert result["dependencies"] == [{"pipeline": "crossref_publications"}]
    assert result["enrichers"] == [{"pipeline": "openalex_publications"}]
