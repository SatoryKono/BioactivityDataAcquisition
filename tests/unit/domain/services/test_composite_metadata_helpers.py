"""Unit tests for pure composite metadata parsing helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from bioetl.domain.services.composite_metadata_helpers import (
    _parse_literal,
    extract_composite_lineage_metadata,
    parse_composite_field_sources,
    parse_composite_list,
    parse_composite_status,
    summarize_composite_cv_dq,
)


def test_parse_literal_prefers_json_and_supports_legacy_literals() -> None:
    """Composite metadata parsing should support both JSON and legacy string payloads."""
    assert _parse_literal('["a", "b"]') == ["a", "b"]
    assert _parse_literal('{"a": 1}') == {"a": 1}
    assert _parse_literal("['a', 'b']") == ["a", "b"]
    assert _parse_literal("{'a': 1}") == {"a": 1}
    assert _parse_literal("not json") is None
    assert _parse_literal(None) is None


def test_parse_composite_list_accepts_json_and_legacy_strings() -> None:
    """List metadata should parse from JSON strings and older Python literals."""
    assert parse_composite_list('["a", "b"]') == ["a", "b"]
    assert parse_composite_list("['a', 'b']") == ["a", "b"]
    assert parse_composite_list(["a", "b"]) == ["a", "b"]


def test_parse_composite_status_accepts_json_and_legacy_strings() -> None:
    """Status metadata should parse from JSON strings and older Python literals."""
    assert parse_composite_status('{"a": "success"}') == {"a": "success"}
    assert parse_composite_status("{'a': 'success'}") == {"a": "success"}
    assert parse_composite_status({"a": "success"}) == {"a": "success"}


def test_parse_composite_field_sources_from_dict_and_stringified_dict() -> None:
    """Field-source metadata should parse from dict and string payloads."""
    assert parse_composite_field_sources({"title": "openalex", "doi": "seed"}) == {
        "title": "openalex",
        "doi": "seed",
    }
    assert parse_composite_field_sources("{'abstract': 'pubmed'}") == {
        "abstract": "pubmed"
    }
    assert parse_composite_field_sources("[1, 2, 3]") == {}


def test_extract_composite_lineage_metadata_parses_graph_relevant_fields() -> None:
    """Composite lineage extraction should normalize canonical graph fields."""
    metadata = extract_composite_lineage_metadata(
        [
            {
                "_composite_run_id": "comp-run-123",
                "_source_providers": "['seed', 'openalex']",
                "_enrichment_status": "{'openalex': 'success'}",
                "_field_sources": "{'title': 'openalex', 'doi': 'seed'}",
                "_seed_record_id": "seed-001",
                "_lineage_created_at": "2026-03-24T10:00:00+00:00",
            }
        ],
        composite_name="composite.publication",
    )

    assert metadata is not None
    assert metadata.composite_run_id == "comp-run-123"
    assert metadata.composite_name == "composite.publication"
    assert metadata.source_providers == ("seed", "openalex")
    assert metadata.enrichment_status["openalex"].status == "success"
    assert metadata.field_sources == {"title": "openalex", "doi": "seed"}
    assert metadata.seed_record_id == "seed-001"
    assert metadata.created_at == datetime(2026, 3, 24, 10, 0, tzinfo=UTC)


def test_extract_composite_lineage_metadata_returns_none_for_plain_records() -> None:
    """Plain records should not produce composite lineage metadata."""
    assert (
        extract_composite_lineage_metadata([{"id": 1}], composite_name="plain") is None
    )


def test_summarize_composite_cv_dq_returns_counts_and_provenance() -> None:
    """Composite CV markers should map to stable DQ semantics."""
    summary = summarize_composite_cv_dq(
        [
            {"id": 1, "_cv_warn": True, "_cv_error": False, "_cv_quarantine": False},
            {"id": 2, "_cv_warn": False, "_cv_error": True, "_cv_quarantine": True},
            {"id": 3, "_cv_warn": True, "_cv_error": True, "_cv_quarantine": False},
        ],
        contract_version="2.1.0",
        report_artifact_path="reports/dq/composite.json",
    )

    assert summary["has_signal"] is True
    assert summary["warning_records"] == 1
    assert summary["error_records"] == 2
    assert summary["quarantine_records"] == 1
    assert summary["validation_passed"] is False
    provenance = summary["rule_provenance"]
    assert provenance == [
        {
            "rule_id": "composite.cross_validation.warning",
            "contract_version": "2.1.0",
            "config_path": "cross_validation",
            "layer": "composite",
            "field": None,
            "severity": "warning",
            "decision": "warn",
            "violation_kind": "cross_validation_mismatch",
            "report_artifact_path": "reports/dq/composite.json",
            "record_count": "1",
        },
        {
            "rule_id": "composite.cross_validation.nullify",
            "contract_version": "2.1.0",
            "config_path": "cross_validation",
            "layer": "composite",
            "field": None,
            "severity": "error",
            "decision": "skip",
            "violation_kind": "cross_validation_mismatch",
            "report_artifact_path": "reports/dq/composite.json",
            "record_count": "1",
        },
        {
            "rule_id": "composite.cross_validation.quarantine",
            "contract_version": "2.1.0",
            "config_path": "cross_validation",
            "layer": "composite",
            "field": None,
            "severity": "error",
            "decision": "quarantine",
            "violation_kind": "cross_validation_mismatch",
            "report_artifact_path": "reports/dq/composite.json",
            "record_count": "1",
        },
    ]
