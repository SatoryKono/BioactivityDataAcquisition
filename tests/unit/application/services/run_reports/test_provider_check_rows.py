"""Saved provider checks stay incomplete when the run did not record a provider id."""

from datetime import UTC, datetime

import pytest

from bioetl.application.services.run_reports.observations import (
    bind_run_observations,
    observed_health_report,
    reset_run_observations,
    run_observations,
)
from bioetl.domain.run_reports.selected_status import (
    provider_check_rows,
    provider_selector_options,
)
from bioetl.domain.types import ComponentHealthResult, HealthStatus

pytestmark = pytest.mark.unit


def test_missing_provider_observation_is_not_ok() -> None:
    rows = provider_check_rows({})
    assert rows == [
        {
            "provider": "—",
            "check_result": "INCOMPLETE",
            "evidence": "Данные проверки провайдера для этого запуска не сохранены",
            "observed_at": None,
        }
    ]


def test_observed_health_report_records_provider_identity() -> None:
    token = bind_run_observations()
    try:
        observed_health_report(
            [
                ComponentHealthResult(
                    component="data_source",
                    status=HealthStatus.DEGRADED,
                    duration_seconds=0.2,
                    provider="uniprot",
                    latency_ms=15.0,
                    error_message="slow",
                    probe_fallback_reason="timeout",
                )
            ],
            datetime(2026, 9, 26, tzinfo=UTC),
        )
        report = {"observations": run_observations()}
    finally:
        reset_run_observations(token)
    rows = provider_check_rows(report)
    assert rows[0]["provider"] == "uniprot"
    assert rows[0]["check_result"] == "WARN"
    assert rows[0]["evidence"] == "PRESENT"
    assert rows[0]["observed_at"] == "2026-09-26T00:00:00+00:00"


def test_saved_identity_provider_keeps_ok_when_facts_omit_name() -> None:
    rows = provider_check_rows(
        {
            "identity": {"provider": "uniprot", "pipeline_name": "uniprot_protein"},
            "io": {"use_cached_bronze": False},
            "observations": {
                "Provider": {
                    "verdict": "OK",
                    "reason": "run_preflight_provider_observation",
                    "facts": {
                        "status": "HEALTHY",
                        "observed_at": "2026-09-26T00:43:32.171206+00:00",
                        "probe_fallback_reason": None,
                    },
                }
            },
        }
    )
    assert rows == [
        {
            "provider": "uniprot",
            "check_result": "OK",
            "evidence": "PRESENT",
            "observed_at": "2026-09-26T00:43:32.171206+00:00",
        }
    ]


def test_selector_options_follow_saved_run_provider() -> None:
    options = provider_selector_options(
        {
            "identity": {"provider": "uniprot"},
            "observations": {
                "Provider": {
                    "verdict": "OK",
                    "facts": {"status": "HEALTHY"},
                }
            },
        }
    )
    assert options == [{"text": "uniprot", "value": "uniprot"}]
    assert all(item["value"] != "$__all" for item in options)


def test_ok_verdict_without_provider_id_stays_incomplete() -> None:
    rows = provider_check_rows(
        {
            "observations": {
                "Provider": {
                    "verdict": "OK",
                    "reason": "run_preflight_provider_observation",
                    "facts": {
                        "status": "HEALTHY",
                        "observed_at": "2026-09-26T00:43:32.171206+00:00",
                        "probe_fallback_reason": None,
                    },
                }
            }
        }
    )
    assert rows == [
        {
            "provider": "—",
            "check_result": "INCOMPLETE",
            "evidence": "INCOMPLETE",
            "observed_at": "2026-09-26T00:43:32.171206+00:00",
        }
    ]
