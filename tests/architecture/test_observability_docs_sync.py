"""Architecture ratchets for canonical observability docs vocabulary."""

from __future__ import annotations

from pathlib import Path

import pytest


RULES_PATH = Path("docs/00-project/RULES.md")
METRICS_GUIDE_PATH = Path("docs/03-guides/metrics-monitoring.md")
OBSERVABILITY_CONTRACT_PATH = Path("docs/04-reference/contracts/observability.md")


@pytest.mark.architecture
def test_rules_metrics_section_uses_canonical_observability_tokens() -> None:
    """RULES must not reintroduce legacy metric names or log-key spellings."""
    text = RULES_PATH.read_text(encoding="utf-8")

    legacy_tokens = (
        "`pipeline-duration-seconds`",
        "`records-processed-total`",
        "`errors-total`",
        "| run-id       |",
        "| error-type   |",
        "| record-count |",
        "`run-id` обязателен во всех логах, метриках и блокировках",
        "stage        | MUST           | `extract`, `transform`, `load`",
    )

    for token in legacy_tokens:
        assert token not in text, (
            f"RULES.md reintroduced a legacy observability token: {token}"
        )

    assert "`bioetl_pipeline_duration_seconds`" in text
    assert "`bioetl_records_processed_total`" in text
    assert "`bioetl_errors_total`" in text
    assert "`run_id` обязателен во всех логах" in text


@pytest.mark.architecture
def test_metrics_monitoring_guide_uses_canonical_log_schema_tokens() -> None:
    """Metrics guide log schema examples must match the canonical contract."""
    text = METRICS_GUIDE_PATH.read_text(encoding="utf-8")

    legacy_tokens = (
        "| `ts`       |",
        "| `run-id`   |",
        '"ts": "',
        '"run-id": "',
        '"stage": "extract"',
        "Этап (extract, transform, load, validate)",
    )

    for token in legacy_tokens:
        assert token not in text, (
            f"metrics-monitoring.md reintroduced a legacy observability token: {token}"
        )

    assert "`timestamp`" in text
    assert "`run_id`" in text
    assert '"timestamp": "' in text
    assert '"run_id": "' in text
    assert '"stage": "preflight"' in text


@pytest.mark.architecture
def test_docs_publish_stage_model_and_invariant_metric_contracts() -> None:
    """Published observability docs must include the canonical stage/invariant families."""
    metrics_guide = METRICS_GUIDE_PATH.read_text(encoding="utf-8")
    observability_contract = OBSERVABILITY_CONTRACT_PATH.read_text(encoding="utf-8")

    required_tokens = (
        "bioetl_stage_records_total",
        "bioetl_stage_backlog_records",
        "bioetl_stage_lag_seconds",
        "bioetl_record_flow_invariants_total",
        "bioetl_batch_lifecycle_events_total",
        "bioetl_batch_lifecycle_records_total",
        "bioetl_composite_phase_records_total",
        "bioetl_composite_phase_errors_total",
        "bioetl_composite_phase_loss_total",
        "bioetl_composite_phase_retries_total",
        "bioetl_output_artifact_publication_events_total",
    )

    for token in required_tokens:
        assert token in metrics_guide, (
            f"metrics-monitoring.md is missing canonical observability token: {token}"
        )
        assert token in observability_contract, (
            f"observability.md is missing canonical observability token: {token}"
        )


@pytest.mark.architecture
def test_docs_publish_control_plane_and_runtime_health_metric_contracts() -> None:
    """Published observability docs must include control-plane/runtime health families."""
    metrics_guide = METRICS_GUIDE_PATH.read_text(encoding="utf-8")
    observability_contract = OBSERVABILITY_CONTRACT_PATH.read_text(encoding="utf-8")

    required_tokens = (
        "bioetl_control_plane_terminal_events_total",
        "bioetl_replay_reconstructability_events_total",
        "bioetl_metrics_publication_events_total",
        "bioetl_observability_runtime_status",
    )

    for token in required_tokens:
        assert token in metrics_guide, (
            f"metrics-monitoring.md is missing canonical observability token: {token}"
        )
        assert token in observability_contract, (
            f"observability.md is missing canonical observability token: {token}"
        )


@pytest.mark.architecture
def test_docs_publish_dq_disposition_metric_contract() -> None:
    """Published observability docs must include bounded DQ disposition semantics."""
    metrics_guide = METRICS_GUIDE_PATH.read_text(encoding="utf-8")
    observability_contract = OBSERVABILITY_CONTRACT_PATH.read_text(encoding="utf-8")

    expected_metric = "bioetl_dq_dispositions_total"

    assert expected_metric in metrics_guide, (
        "metrics-monitoring.md is missing canonical observability metric: "
        f"{expected_metric}"
    )
    assert expected_metric in observability_contract, (
        f"observability.md is missing canonical observability metric: {expected_metric}"
    )
