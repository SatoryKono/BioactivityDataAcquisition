"""Unit tests for observability contract normalization/validation."""

from __future__ import annotations

from bioetl.domain.observability_contract import (
    build_observability_contract_payload,
    enforce_observability_contract_context,
    is_observability_contract_valid,
    missing_observability_fields,
    normalize_observability_metric_labels,
)


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
