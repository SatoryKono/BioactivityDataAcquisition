"""Architecture ratchets for canonical observability docs vocabulary."""

from __future__ import annotations

import re
from pathlib import Path

import pytest


RULES_PATH = Path("docs/00-project/RULES.md")
METRICS_GUIDE_PATH = Path("docs/03-guides/metrics-monitoring.md")
OBSERVABILITY_CONTRACT_PATH = Path("docs/04-reference/contracts/observability.md")
GRAFANA_README_PATH = Path("grafana/README.md")
MONITORING_INDEX_PATH = Path("docs/03-guides/dashboards/monitoring-index.md")


@pytest.mark.architecture
def test_monitoring_docs_do_not_publish_unsafe_promql_examples() -> None:
    """Operator docs must not publish known unsafe PromQL copy-paste patterns."""
    docs = {
        "docs/03-guides/metrics-monitoring.md": METRICS_GUIDE_PATH.read_text(
            encoding="utf-8"
        ),
        "docs/04-reference/contracts/observability.md": (
            OBSERVABILITY_CONTRACT_PATH.read_text(encoding="utf-8")
        ),
        "grafana/README.md": GRAFANA_README_PATH.read_text(encoding="utf-8"),
    }

    unsafe_patterns = (
        (
            re.compile(r"histogram_quantile\(\s*0\.\d+\s*,\s*rate\(", re.MULTILINE),
            "histogram_quantile must aggregate buckets with sum by (le, ...) "
            "before quantile calculation",
        ),
        (
            re.compile(r"rate\(bioetl_errors_total\[5m\]\)\s*>\s*10"),
            "bioetl_errors_total alerts must use an explicit processed-record "
            "denominator or be documented as raw error throughput",
        ),
    )

    violations: list[str] = []
    for doc_name, text in docs.items():
        for pattern, reason in unsafe_patterns:
            for match in pattern.finditer(text):
                line_number = text.count("\n", 0, match.start()) + 1
                violations.append(f"{doc_name}:{line_number}: {reason}")

    assert not violations, "\n".join(violations)


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


@pytest.mark.architecture
def test_monitoring_docs_track_modular_observability_code_paths() -> None:
    """Monitoring docs must point to current modular observability paths."""
    grafana_readme = GRAFANA_README_PATH.read_text(encoding="utf-8")
    metrics_guide = METRICS_GUIDE_PATH.read_text(encoding="utf-8")
    observability_contract = OBSERVABILITY_CONTRACT_PATH.read_text(encoding="utf-8")

    assert "src/bioetl/domain/ports/noop.py" not in grafana_readme
    for required_token in (
        "src/bioetl/domain/ports/noop/_metrics.py",
        "src/bioetl/infrastructure/observability/_metrics_defs_*.py",
        "src/bioetl/infrastructure/observability/prometheus_metric_registries.py",
        "src/bioetl/infrastructure/observability/prometheus_metric_label_dispatch.py",
        "src/bioetl/infrastructure/observability/prometheus_metric_label_policy_sets.py",
    ):
        assert required_token in grafana_readme, (
            f"grafana/README.md is missing current observability path: {required_token}"
        )

    for text, doc_name in (
        (grafana_readme, "grafana/README.md"),
        (metrics_guide, "metrics-monitoring.md"),
        (observability_contract, "observability.md"),
    ):
        assert "replace-style" in text, (
            f"{doc_name} must document Pushgateway replace-style publication."
        )
        assert "delete_metrics_from_gateway" in text, (
            f"{doc_name} must document Pushgateway cleanup seam."
        )
        assert "manifest/ledger/CLI/explorer" in text, (
            f"{doc_name} must preserve Prometheus aggregate vs forensic boundary."
        )


@pytest.mark.architecture
def test_monitoring_index_is_concise_operator_entrypoint() -> None:
    """Monitoring index must stay the short routing surface for incidents."""
    text = MONITORING_INDEX_PATH.read_text(encoding="utf-8")

    required_tokens = (
        "Incident-Time Operator Index",
        "Architecture Map",
        "bioetl-overview-v2",
        "bioetl-runtime",
        "bioetl-provider-health-v2",
        "bioetl-dq-v2",
        "bioetl-control-plane-v1",
        "bioetl diagnostics guide",
        "bioetl checkpoint inspect",
        "report-observability-metric-inventory --json",
        "manifest/ledger/CLI/explorer surfaces",
    )
    for token in required_tokens:
        assert token in text, f"monitoring-index.md missing operator token: {token}"

    assert len(text.splitlines()) <= 130, (
        "monitoring-index.md must remain concise; move detailed setup/reference "
        "content to grafana/README.md or contract docs."
    )


@pytest.mark.architecture
def test_grafana_readme_does_not_republish_legacy_v1_as_active_dashboards() -> None:
    """README may mention legacy v1 only as archive, not active operator rows."""
    text = GRAFANA_README_PATH.read_text(encoding="utf-8")

    forbidden_active_rows = (
        "| BioETL Overview           | `bioetl-overview`",
        "| BioETL Provider Health    | `bioetl-provider-health`",
        "| BioETL Data Quality       | `bioetl-dq`",
        "Почему v1 и v2 дашборды сосуществуют?",
        "v1 дашборды оптимизированы",
    )
    for token in forbidden_active_rows:
        assert token not in text, (
            f"grafana/README.md reintroduced active legacy guidance: {token}"
        )

    assert "legacy v1 dashboard surfaces" in text
    assert "Metric lifecycle reference boundary" in text


@pytest.mark.architecture
def test_grafana_readme_health_metric_catalog_matches_canonical_label_policy() -> None:
    """Grafana README metric tables must stay aligned with bounded label policy."""
    text = GRAFANA_README_PATH.read_text(encoding="utf-8")

    assert "| `bioetl_infrastructure_validated`      | Gauge     | `pipeline`" in text
    assert (
        "`bioetl_infrastructure_validated`      | Gauge     | `pipeline`, `run_id`"
        not in text
    )
    assert text.count("`bioetl_health_check_latency_seconds`") == 1, (
        "grafana/README.md must not duplicate the "
        "`bioetl_health_check_latency_seconds` metric row."
    )
