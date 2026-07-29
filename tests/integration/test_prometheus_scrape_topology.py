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
"""Fail-closed contracts for the shipped Prometheus scrape topology."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

_PROMETHEUS_CONFIG = Path("grafana/prometheus.yml")
_GRAFANA_README = Path("grafana/README.md")


def _load_prometheus_config() -> dict[str, object]:
    payload = yaml.safe_load(_PROMETHEUS_CONFIG.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "prometheus.yml must deserialize to a mapping"
    return payload


def test_canonical_bioetl_scrape_target_is_compose_network_dns() -> None:
    """Shipped Prometheus config must scrape bioetl:8000 as the default topology."""
    payload = _load_prometheus_config()
    scrape_configs = payload.get("scrape_configs")
    assert isinstance(scrape_configs, list)
    bioetl_jobs = [
        job
        for job in scrape_configs
        if isinstance(job, dict) and job.get("job_name") == "bioetl"
    ]
    assert len(bioetl_jobs) == 1, "exactly one bioetl scrape job is required"
    job = bioetl_jobs[0]
    assert job.get("scrape_interval") == "30s", (
        "bioetl job must pin scrape_interval=30s (distinct from global defaults)"
    )
    static_configs = job.get("static_configs")
    assert isinstance(static_configs, list) and static_configs
    targets = static_configs[0].get("targets")
    assert targets == ["bioetl:8000"], (
        "canonical bioetl scrape target must be bioetl:8000 on the monitoring network"
    )


def test_operator_docs_document_canonical_target_and_optional_host_override() -> None:
    """README must not present host.docker.internal as the default bioetl scrape."""
    readme = _GRAFANA_README.read_text(encoding="utf-8")
    assert "targets: ['bioetl:8000']" in readme or 'targets: ["bioetl:8000"]' in readme
    assert "scrape_interval: 30s" in readme
    assert "host.docker.internal:8000" in readme
    # Host topology must be marked optional/override, not the primary default.
    assert "Host override" in readme or "host override" in readme.lower()
    assert (
        "canonical compose network" in readme.lower()
        or "bioetl:8000 (canonical" in readme
    )
