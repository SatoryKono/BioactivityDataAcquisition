# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Static and transport contracts for Prometheus HELP/TYPE metadata."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest
import yaml
from prometheus_client import REGISTRY, generate_latest

from bioetl.infrastructure.observability import server
from bioetl.infrastructure.observability.prometheus_metric_registries import (
    METRIC_REGISTRY_FAMILIES,
)

pytestmark = pytest.mark.unit
_REPO_ROOT = Path(__file__).resolve().parents[4]


def test_shipped_prometheus_scrapes_pushgateway_by_container_service_name() -> None:
    """Container-local localhost must not replace the Pushgateway service target."""
    config = yaml.safe_load(
        (_REPO_ROOT / "grafana/prometheus.yml").read_text(encoding="utf-8")
    )
    job = next(
        item for item in config["scrape_configs"] if item["job_name"] == "pushgateway"
    )

    assert job["static_configs"] == [{"targets": ["pushgateway:9091"]}]


def test_code_registry_has_help_and_type_for_every_registered_metric() -> None:
    """Code definitions are the authoritative static HELP/TYPE source."""
    registries = (
        ("counter", "counters"),
        ("gauge", "gauges"),
        ("histogram", "histograms"),
    )
    for family in METRIC_REGISTRY_FAMILIES:
        for expected_type, attribute in registries:
            metrics = getattr(family, attribute)
            for metric_name, metric in metrics.items():
                assert getattr(metric, "_documentation", "").strip(), metric_name
                assert getattr(metric, "_type", None) == expected_type, metric_name


def test_direct_and_restricted_exposition_preserve_dq_help_and_type(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Both direct scrape and bounded Pushgateway snapshots keep descriptors."""
    dq_score = next(
        family.gauges["bioetl_dq_validation_score"]
        for family in METRIC_REGISTRY_FAMILIES
        if "bioetl_dq_validation_score" in family.gauges
    )
    dq_count = next(
        family.gauges["bioetl_dq_validation_record_count"]
        for family in METRIC_REGISTRY_FAMILIES
        if "bioetl_dq_validation_record_count" in family.gauges
    )
    labels = {"pipeline": "metadata_contract", "entity": "activity"}
    dq_score.labels(**labels).set(0.97)
    dq_count.labels(**labels).set(100)

    direct_exposition = generate_latest(REGISTRY).decode("utf-8")
    expected_lines = (
        "# HELP bioetl_dq_validation_score ",
        "# TYPE bioetl_dq_validation_score gauge",
        "# HELP bioetl_dq_validation_record_count ",
        "# TYPE bioetl_dq_validation_record_count gauge",
    )
    assert all(line in direct_exposition for line in expected_lines)

    captured: dict[str, str] = {}

    def capture_push(_gateway: str, **kwargs: object) -> None:
        captured["exposition"] = generate_latest(kwargs["registry"]).decode("utf-8")

    monkeypatch.setattr(server, "push_to_gateway", capture_push)
    monkeypatch.setattr(server, "METRICS_PUBLICATION_EVENTS_TOTAL", MagicMock())
    assert server.push_metrics_to_gateway(
        gateway="pushgateway:9091",
        grouping_key={"pipeline": "metadata_contract", "run_type": "backfill"},
        metric_names=(
            "bioetl_dq_validation_score",
            "bioetl_dq_validation_record_count",
        ),
    )
    assert all(line in captured["exposition"] for line in expected_lines)
