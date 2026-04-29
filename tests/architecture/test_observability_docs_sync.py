"""Architecture ratchets for canonical observability docs vocabulary."""

from __future__ import annotations

from pathlib import Path

import pytest


RULES_PATH = Path("docs/00-project/RULES.md")
METRICS_GUIDE_PATH = Path("docs/03-guides/metrics-monitoring.md")


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
