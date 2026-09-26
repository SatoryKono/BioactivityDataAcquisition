"""Terminal workflow snapshots retain measured pipeline telemetry on every exit."""

from __future__ import annotations

import asyncio
from types import SimpleNamespace

import pytest
from prometheus_client import CollectorRegistry, Counter, generate_latest

from bioetl.infrastructure.observability._metrics_gateway_publication import (
    publish_metrics_to_gateway,
)
from bioetl.interfaces.cli.commands._workflow_run_support import (
    _execute_workflow_and_publish_metrics,
    _workflow_metrics_run_type,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    ("run_types", "expected"),
    [(("backfill", "backfill"), "backfill"), (("backfill", "incremental"), None)],
)
def test_workflow_publication_uses_actual_step_run_types(run_types, expected) -> None:
    config = SimpleNamespace(
        pipeline_steps=[
            SimpleNamespace(run_options=SimpleNamespace(run_type=t)) for t in run_types
        ],
        defaults=SimpleNamespace(merged_with=lambda options: options),
    )
    assert _workflow_metrics_run_type(config) == expected


@pytest.mark.parametrize("failure", [None, RuntimeError, asyncio.CancelledError])
def test_full_snapshot_survives_short_workflow_exit(failure) -> None:
    registry = CollectorRegistry()
    counter = Counter(
        "bioetl_control_plane_ledger_appends_total",
        "Measured ledger writes",
        ["pipeline", "status"],
        registry=registry,
    )
    publications = Counter(
        "bioetl_metrics_publication_events_total",
        "Publication results",
        ["pipeline", "run_type", "target", "status"],
        registry=registry,
    )
    bodies: list[bytes] = []

    class Service:
        def record_expected_pipeline_metrics(self, config):
            pass

        async def run_workflow(self, config, **kwargs):
            # Both pipeline scopes belong to one short-lived process; zero is
            # an explicit observation, not an exporter/rule fallback.
            counter.labels("chembl_assay", "failed").inc(0)
            counter.labels("chembl_target", "success").inc(1)
            if failure is not None:
                raise failure("terminal error")
            return "complete"

    def push(**kwargs):
        return publish_metrics_to_gateway(
            registry=registry,
            publication_metric=publications,
            push_gateway=lambda gateway, **request: bodies.append(
                generate_latest(request["registry"])
            ),
            metric_names=kwargs.get("metric_names"),
        )

    def execute():
        return _execute_workflow_and_publish_metrics(
            get_workflow_execution_service_fn=lambda **kwargs: Service(),
            ensure_metrics_server_started_fn=lambda: True,
            publish_metrics_safely_fn=push,
            config=SimpleNamespace(
                name="chembl_core",
                pipeline_names=("chembl_assay", "chembl_target"),
                single_pipeline_name=None,
            ),
            registry=None,
            dry_run=False,
            only_steps=None,
            resume_last=False,
            resume_manifest_id=None,
            resume_run_id=None,
            force_steps=None,
            repair_steps=None,
            incremental=False,
        )

    if failure is None:
        assert execute() == "complete"
    else:
        with pytest.raises(failure, match="terminal error"):
            execute()
    # Terminal publication partitions both pipeline scopes instead of using
    # one global replace group. Inspect all emitted bodies on every exit.
    terminal_snapshot = b"\n".join(bodies)
    assert (
        b'bioetl_control_plane_ledger_appends_total{pipeline="chembl_assay",status="failed"} 0.0'
        in terminal_snapshot
    )
    assert (
        b'bioetl_control_plane_ledger_appends_total{pipeline="chembl_target",status="success"} 1.0'
        in terminal_snapshot
    )


def test_gateway_address_is_loaded_from_environment(monkeypatch) -> None:
    from bioetl.infrastructure.config.settings_api import Settings

    monkeypatch.setenv("BIOETL_PUSHGATEWAY_URL", "http://pushgateway:9091")
    assert Settings(_env_file=None).pushgateway_url == "http://pushgateway:9091"
