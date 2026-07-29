# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for observability contract normalization/validation."""

from __future__ import annotations

import pytest

from bioetl.domain.observability_contract import (
    build_observability_contract_payload,
    enforce_observability_contract_context,
    is_observability_contract_valid,
    missing_observability_fields,
    normalize_observability_metric_labels,
    normalize_observability_pipeline_label,
)


pytestmark = pytest.mark.unit


def test_enforce_contract_ignores_legacy_keys_after_grace_period() -> None:
    context = enforce_observability_contract_context(
        event_name="contract_event",
        context={
            "provider_name": "legacy_provider",
            "pipeline_name": "legacy_pipeline",
            "correlation_id": "legacy-run-id",
            "log_level": "warning",
        },
        default_provider="default_provider",
        default_pipeline="default_pipeline",
        default_run_id="default-run-id",
        default_severity="info",
    )

    assert missing_observability_fields(context) == ()
    assert context["provider"] == "default_provider"
    assert context["pipeline"] == "default_pipeline"
    assert context["run_id"] == "default-run-id"
    assert context["severity"] == "info"
    # Legacy aliases are ignored and not emitted.
    assert "provider_name" not in context
    assert "pipeline_name" not in context
    assert "correlation_id" not in context
    assert "log_level" not in context


def test_enforce_contract_repairs_empty_required_fields() -> None:
    context = enforce_observability_contract_context(
        event_name="",
        context={},
        default_provider="",
        default_pipeline="",
        default_run_id="",
        default_severity="INVALID",
    )

    assert is_observability_contract_valid(context)
    assert missing_observability_fields(context) == ()
    assert context["event"] == "unknown_event"
    assert context["provider"] == "unknown"
    assert context["pipeline"] == "unknown"
    assert context["run_id"] == "unknown"
    assert context["severity"] == "info"
    assert context["error_type"] == "none"


def test_metric_labels_normalization_ignores_legacy_aliases() -> None:
    labels = normalize_observability_metric_labels(
        {
            "event_name": "pipeline_started",
            "provider_name": "chembl",
            "pipeline_name": "chembl_activity",
            "log_level": "INFO",
        }
    )

    assert labels == {
        "event": "unknown_event",
        "provider": "unknown",
        "pipeline": "unknown",
        "severity": "info",
        "error_type": "none",
    }


def test_canonical_labels_take_precedence_when_legacy_aliases_present() -> None:
    labels = normalize_observability_metric_labels(
        {
            "event": "pipeline_started",
            "provider": "chembl",
            "pipeline": "chembl_activity",
            "severity": "info",
            "error_type": "none",
            "event_name": "legacy_event",
            "provider_name": "legacy_provider",
            "pipeline_name": "legacy_pipeline",
            "log_level": "warning",
        }
    )

    assert labels == {
        "event": "pipeline_started",
        "provider": "chembl",
        "pipeline": "chembl_activity",
        "severity": "info",
        "error_type": "none",
    }


def test_build_payload_returns_validated_context_and_metric_labels() -> None:
    payload = build_observability_contract_payload(
        event_name="contract_event",
        context={"provider_name": "legacy_provider"},
        default_provider="default_provider",
        default_pipeline="chembl_activity",
        default_run_id="run-123",
        default_severity="warning",
    )

    assert is_observability_contract_valid(payload.context)
    assert missing_observability_fields(payload.context) == ()
    assert set(payload.metric_labels) == {
        "event",
        "provider",
        "pipeline",
        "severity",
        "error_type",
    }
    assert payload.metric_labels["event"] == "contract_event"
    assert payload.metric_labels["provider"] == "default_provider"


def test_build_payload_enriches_event_family_and_correlation_defaults() -> None:
    payload = build_observability_contract_payload(
        event_name="preflight_started",
        context={},
        default_provider="chembl",
        default_pipeline="chembl_activity",
        default_run_id="run-123",
        default_severity="info",
        correlation_defaults={
            "manifest_id": "manifest-1",
            "entity": "activity",
            "run_type": "incremental",
            "effective_config_hash": "sha256:abc",
            "contract_ref": "gold.activity",
            "contract_version": "1.0.0",
        },
    )

    assert payload.context["event_family"] == "pipeline.phase"
    assert payload.context["manifest_id"] == "manifest-1"
    assert payload.context["entity"] == "activity"
    assert payload.context["run_type"] == "incremental"
    assert payload.context["effective_config_hash"] == "sha256:abc"
    assert payload.context["contract_ref"] == "gold.activity"
    assert payload.context["contract_version"] == "1.0.0"
    assert "manifest_id" not in payload.metric_labels


def test_normalize_observability_pipeline_label_extracts_table_name_from_path() -> None:
    assert (
        normalize_observability_pipeline_label(
            "test-output/bioetl/silver/chembl_activity__v1_2_3"
        )
        == "chembl_activity"
    )


def test_normalize_observability_pipeline_label_rejects_uuid_like_values() -> None:
    assert (
        normalize_observability_pipeline_label("123e4567-e89b-12d3-a456-426614174000")
        == "unknown"
    )


def test_metric_labels_normalization_collapses_path_like_pipeline_values() -> None:
    labels = normalize_observability_metric_labels(
        {
            "event": "silver_merge_retry",
            "provider": "storage",
            "pipeline": r"C:\\bioetl\\silver\\chembl_activity__v1_2_3",
            "severity": "warning",
            "error_type": "timeout",
        }
    )

    assert labels == {
        "event": "silver_merge_retry",
        "provider": "storage",
        "pipeline": "chembl_activity",
        "severity": "warning",
        "error_type": "timeout",
    }
