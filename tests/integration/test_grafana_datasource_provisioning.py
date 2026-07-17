"""Integration checks for Grafana datasource provisioning assets."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from scripts.ops.observability import (
    start_read_only_audit_stack as audit_stack_subject,
)


pytestmark = pytest.mark.integration

RENDERER_IMAGE = (
    "grafana/grafana-image-renderer"
    "@sha256:c0c920e6974b0d30ae25313051344afcd2054362529968ebd9545a4b2bc8119b"
)


class _ProbeResponse:
    def __init__(self, payload: object) -> None:
        self._payload = (
            payload if isinstance(payload, bytes) else json.dumps(payload).encode()
        )

    def __enter__(self) -> _ProbeResponse:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def read(self) -> bytes:
        return self._payload


def _load_monitoring_compose() -> dict[str, object]:
    compose_path = Path("docker-compose.monitoring.yml")
    return yaml.safe_load(compose_path.read_text(encoding="utf-8"))


def _load_monitoring_audit_override() -> dict[str, object]:
    compose_path = Path("scripts/ops/observability/docker-compose.monitoring.audit.yml")
    return yaml.safe_load(compose_path.read_text(encoding="utf-8"))


def test_quarantine_explorer_datasource_is_repo_provisioned() -> None:
    """Quarantine explorer datasource should be provisioned from repository files."""
    path = Path("grafana/provisioning/datasources-core/quarantine-explorer.yml")
    assert path.exists(), "Missing datasource provisioning file for Quarantine Explorer"

    content = path.read_text(encoding="utf-8")
    assert "name: Quarantine Explorer" in content
    assert "uid: quarantine-explorer" in content
    assert "type: yesoreyeram-infinity-datasource" in content
    assert "BIOETL_QUARANTINE_EXPLORER_URL" in content
    assert ":-" not in content


def test_quarantine_explorer_backend_contract_is_documented() -> None:
    """Docs and env template must declare the long-lived backend contract."""
    readme = Path("grafana/README.md").read_text(encoding="utf-8")
    env_example = Path(".env.example").read_text(encoding="utf-8")

    assert "bioetl quarantine serve --host 0.0.0.0 --port 8081" in readme
    assert "dedicated long-lived BioETL HTTP" in readme
    assert "compatibility entrypoint" in readme
    assert (
        "BIOETL_QUARANTINE_EXPLORER_URL=http://host.docker.internal:8081" in env_example
    )


def test_quarantine_explorer_compose_uses_service_dns_backend() -> None:
    """Grafana should resolve the in-compose Quarantine Explorer service by default."""
    monitoring = _load_monitoring_compose()
    grafana = monitoring["services"]["grafana"]
    root = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    bioetl = root["services"]["bioetl"]

    assert (
        "BIOETL_QUARANTINE_EXPLORER_URL=${BIOETL_QUARANTINE_EXPLORER_URL:-http://quarantine-explorer:8081}"
        in grafana["environment"]
    )
    assert "host.docker.internal:host-gateway" in grafana["extra_hosts"]
    assert "quarantine-explorer" not in monitoring["services"]
    assert "quarantine-explorer" in bioetl["networks"]["monitoring"]["aliases"]
    assert root["networks"]["monitoring"] == {
        "external": True,
        "name": "bioetl-monitoring",
    }
    assert monitoring["networks"]["monitoring"] == root["networks"]["monitoring"]
    assert bioetl["command"] == [
        "quarantine",
        "serve",
        "--host",
        "0.0.0.0",
        "--port",
        "8081",
    ]
    assert "127.0.0.1:8081:8081" in bioetl["ports"]
    assert "8000:8000" not in bioetl["ports"], (
        "Quarantine Explorer must not occupy the BioETL /metrics host port."
    )


def test_grafana_compose_installs_infinity_plugin() -> None:
    """Grafana container must install the Infinity datasource plugin."""
    compose_path = Path("docker-compose.monitoring.yml")
    content = compose_path.read_text(encoding="utf-8")
    assert "GF_PLUGINS_PREINSTALL=yesoreyeram-infinity-datasource" in content
    assert "GF_INSTALL_PLUGINS" not in content


def test_quarantine_explorer_defaults_to_monitoring_service_backend() -> None:
    """Monitoring compose should route explorer traffic through service DNS by default."""
    compose_path = Path("docker-compose.monitoring.yml")
    content = compose_path.read_text(encoding="utf-8")
    monitoring = _load_monitoring_compose()
    assert (
        "BIOETL_QUARANTINE_EXPLORER_URL=${BIOETL_QUARANTINE_EXPLORER_URL:-http://quarantine-explorer:8081}"
        in content
    )
    assert monitoring["networks"]["monitoring"]["name"] == "bioetl-monitoring"
    assert monitoring["networks"]["monitoring"]["external"] is True


def test_audit_profile_mounts_explicit_roots_read_only_and_uses_bounded_loki_job() -> (
    None
):
    services = _load_monitoring_audit_override()["services"]
    audit_backend = services["quarantine-explorer-audit"]
    audit_promtail = services["promtail-audit"]

    assert audit_backend["profiles"] == ["audit"]
    assert audit_backend["command"][-2:] == [
        "--data-root",
        "${BIOETL_AUDIT_DATA_ROOT:?Pass an explicit absolute data root}",
    ]
    assert audit_backend["volumes"] == [
        "${BIOETL_AUDIT_DATA_ROOT:?Pass an explicit absolute data root}:"
        "${BIOETL_AUDIT_DATA_ROOT:?Pass an explicit absolute data root}:ro"
    ]
    assert audit_promtail["profiles"] == ["audit"]
    assert (
        "${BIOETL_AUDIT_LOG_ROOT:?Pass an explicit absolute log root}:/audit-logs:ro"
        in (audit_promtail["volumes"])
    )
    assert (
        "${BIOETL_AUDIT_PROBE_LOG_ROOT:?Pass an explicit absolute probe log root}:"
        "/audit-probe:ro" in (audit_promtail["volumes"])
    )
    assert "audit" in services["loki"]["profiles"]

    promtail = yaml.safe_load(
        Path("grafana/promtail-config.yml").read_text(encoding="utf-8")
    )
    audit_jobs = [
        job for job in promtail["scrape_configs"] if job["job_name"] == "bioetl-audit"
    ]
    assert len(audit_jobs) == 1
    audit_labels = {
        tuple(sorted(config["labels"].items()))
        for config in audit_jobs[0]["static_configs"]
    }
    assert audit_labels == {
        (("__path__", "/audit-logs/*.log"), ("job", "bioetl-audit")),
        (("__path__", "/audit-probe/*.log"), ("job", "bioetl-audit")),
    }
    assert services["grafana"]["environment"] == [
        "BIOETL_QUARANTINE_EXPLORER_URL=http://quarantine-explorer-audit:8081"
    ]
    assert services["grafana"]["depends_on"]["quarantine-explorer-audit"] == {
        "condition": "service_healthy"
    }
    assert audit_promtail["depends_on"]["loki"] == {"condition": "service_started"}
    assert audit_promtail["healthcheck"] == {"disable": True}
    assert audit_promtail["ports"] == ["127.0.0.1:19080:9080"]


def test_audit_launcher_blocks_failed_promtail_sentinel_delivery(
    tmp_path: Path,
) -> None:
    data_root = tmp_path / "data"
    log_root = tmp_path / "logs"
    probe_log_root = tmp_path / "probe-logs"
    data_root.mkdir()
    log_root.mkdir()
    ticks = iter((0.0, 0.1, 1.1))

    def fake_open(url: str, **_kwargs: object) -> _ProbeResponse:
        if url == audit_stack_subject.READY_URL:
            return _ProbeResponse({"data_root": str(data_root.resolve())})
        if url == audit_stack_subject.CATALOG_URL:
            return _ProbeResponse({"items": []})
        if url == audit_stack_subject.PROMTAIL_READY_URL:
            return _ProbeResponse(b"Ready\n")
        assert url.startswith(audit_stack_subject.LOKI_QUERY_RANGE_URL)
        return _ProbeResponse({"status": "success", "data": {"result": []}})

    with pytest.raises(RuntimeError, match="promtail_state=pending"):
        audit_stack_subject.start_and_verify_audit_stack(
            data_root=data_root.resolve(),
            log_root=log_root.resolve(),
            timeout_seconds=1.0,
            run=lambda *_args, **_kwargs: object(),
            opener=fake_open,
            monotonic=lambda: next(ticks),
            sleep=lambda _seconds: None,
            wall_time_ns=lambda: 1_700_000_000_000_000_000,
            sentinel_id="not-delivered",
            probe_log_root=probe_log_root,
        )

    sentinel = probe_log_root / "bioetl-promtail-audit-sentinel-not-delivered.log"
    assert audit_stack_subject.PROMTAIL_SENTINEL_PREFIX in sentinel.read_text(
        encoding="utf-8"
    )
    assert list(log_root.iterdir()) == []


def test_promtail_probe_reports_unavailable_shipper() -> None:
    def unavailable(*_args: object, **_kwargs: object) -> _ProbeResponse:
        raise OSError("connection refused")

    result = audit_stack_subject.probe_promtail_audit_delivery(
        marker=f"{audit_stack_subject.PROMTAIL_SENTINEL_PREFIX}unavailable",
        opener=unavailable,
    )

    assert result.state is audit_stack_subject.PromtailAuditState.DOWN
    assert "connection refused" in result.detail


def test_default_runtime_log_sink_reaches_canonical_loki_dashboard_job() -> None:
    compose = _load_monitoring_compose()
    promtail_service = compose["services"]["promtail"]
    assert "./reports/logs:/workspace-report-logs:ro" in promtail_service["volumes"]

    logging_source = Path(
        "src/bioetl/infrastructure/observability/logging_config.py"
    ).read_text(encoding="utf-8")
    assert (
        '_DEFAULT_LOG_FILE = Path("reports") / "logs" / "bioetl.log"' in logging_source
    )

    promtail = yaml.safe_load(
        Path("grafana/promtail-config.yml").read_text(encoding="utf-8")
    )
    assert promtail["clients"] == [
        {
            "url": "http://loki:3100/loki/api/v1/push",
            "backoff_config": {
                "min_period": "500ms",
                "max_period": "5s",
                "max_retries": 20,
            },
            "timeout": "10s",
        }
    ]
    assert promtail_service["depends_on"]["loki"] == {"condition": "service_started"}
    runtime_jobs = [
        job
        for job in promtail["scrape_configs"]
        if job["job_name"] == "bioetl-runtime-reports"
    ]
    assert len(runtime_jobs) == 1
    assert runtime_jobs[0]["static_configs"] == [
        {
            "targets": ["localhost"],
            "labels": {
                "job": "bioetl",
                "__path__": "/workspace-report-logs/*.log",
            },
        }
    ]

    dashboard = json.loads(
        Path("grafana/dashboards/bioetl-runtime.json").read_text(encoding="utf-8")
    )
    pending = list(dashboard["panels"])
    panels: dict[int, dict[str, object]] = {}
    while pending:
        panel = pending.pop()
        panels[int(panel["id"])] = panel
        nested = panel.get("panels")
        if isinstance(nested, list):
            pending.extend(nested)
    for panel_id in (250, 251, 257):
        expressions = [
            str(target.get("expr", "")) for target in panels[panel_id]["targets"]
        ]
        assert expressions
        assert all('{job="bioetl"}' in expression for expression in expressions)
        assert all("bioetl-reports" not in expression for expression in expressions)


def test_monitoring_images_are_pinned_and_legacy_pushgateway_datasource_is_inert() -> (
    None
):
    monitoring = _load_monitoring_compose()
    assert monitoring["services"]["prometheus"]["image"] == (
        "prom/prometheus:v3.13.1@sha256:3c42b892cf723fa54d2f262c37a0e1f80aa8c8ddb1da7b9b0df9455a35a7f893"
    )
    assert monitoring["services"]["pushgateway"]["image"] == (
        "prom/pushgateway:v1.11.3@sha256:"
        "74fa117cef2d7e383112d25139ff1c2d2e309c35389a9e0554a47136a1482e48"
    )

    legacy = yaml.safe_load(
        Path("grafana/provisioning/datasources-local/grafana-datasource.yml").read_text(
            encoding="utf-8"
        )
    )
    assert legacy["datasources"] == []


def test_grafana_uses_remote_renderer_sidecar() -> None:
    """Grafana monitoring stack should use a supported remote renderer service."""
    monitoring = _load_monitoring_compose()
    grafana = monitoring["services"]["grafana"]
    renderer = monitoring["services"]["renderer"]

    assert (
        "GF_RENDERING_SERVER_URL=http://renderer:8081/render" in grafana["environment"]
    )
    assert "GF_RENDERING_CALLBACK_URL=http://grafana:3000/" in grafana["environment"]
    assert (
        "GF_RENDERING_RENDERER_TOKEN=${GF_RENDERING_RENDERER_TOKEN:?GF_RENDERING_RENDERER_TOKEN is required}"
        in grafana["environment"]
    )
    assert grafana["entrypoint"] == [
        "/bin/sh",
        "/usr/local/bin/bioetl-bootstrap-grafana.sh",
    ]
    assert renderer["image"] == RENDERER_IMAGE
    assert renderer["shm_size"] == "1gb"
    assert renderer["healthcheck"]["test"] == [
        "CMD",
        "grafana-image-renderer",
        "healthcheck",
    ]
    assert (
        "AUTH_TOKEN=${GF_RENDERING_RENDERER_TOKEN:?GF_RENDERING_RENDERER_TOKEN is required}"
        in renderer["environment"]
    )
    assert (
        "BROWSER_FLAGS=--no-sandbox,--disable-dev-shm-usage" in renderer["environment"]
    )
    assert (
        "BROWSER_READINESS_TIMEOUT=${GRAFANA_IMAGE_RENDERER_READINESS_TIMEOUT:-90s}"
        in renderer["environment"]
    )
    assert (
        "GOMEMLIMIT=${GRAFANA_IMAGE_RENDERER_GOMEMLIMIT:-1GiB}"
        in renderer["environment"]
    )
    assert not any(
        item.startswith("RENDERING_ARGS=") for item in renderer["environment"]
    )


def test_prometheus_scrapes_remote_renderer_metrics() -> None:
    """Renderer metrics must be observable when Grafana render API fails."""
    prometheus = yaml.safe_load(
        Path("grafana/prometheus.yml").read_text(encoding="utf-8")
    )
    jobs = {item["job_name"]: item for item in prometheus["scrape_configs"]}

    renderer = jobs["grafana-image-renderer"]

    assert renderer["metrics_path"] == "/metrics"
    assert renderer["static_configs"] == [{"targets": ["renderer:8081"]}]


def test_prometheus_scrapes_quarantine_explorer_metrics_endpoint() -> None:
    """Quarantine Explorer health probes must not be scraped as Prometheus text."""
    prometheus = yaml.safe_load(
        Path("grafana/prometheus.yml").read_text(encoding="utf-8")
    )
    jobs = {item["job_name"]: item for item in prometheus["scrape_configs"]}

    quarantine = jobs["quarantine-explorer"]

    assert quarantine["metrics_path"] == "/metrics"
    assert quarantine["static_configs"] == [{"targets": ["quarantine-explorer:8081"]}]


def test_tracing_datasource_default_matches_optional_tracing_profile() -> None:
    """Tracing datasources must auto-detect Loki/Tempo when the profile is present."""
    compose = _load_monitoring_compose()
    services = compose["services"]
    loki = services["loki"]
    promtail = services["promtail"]
    tempo = services["tempo"]
    grafana = services["grafana"]

    assert loki["profiles"] == ["tracing"]
    assert promtail["profiles"] == ["tracing"]
    assert tempo["profiles"] == ["tracing"]
    assert loki["healthcheck"] == {"disable": True}
    assert (
        "BIOETL_ENABLE_TRACING_DATASOURCES=${BIOETL_ENABLE_TRACING_DATASOURCES:-auto}"
        in grafana["environment"]
    ), (
        "Grafana tracing datasources must auto-detect Loki/Tempo reachability when "
        "their profile-gated services are available"
    )


def test_grafana_readme_matches_tracing_datasource_default() -> None:
    """Operator docs must describe the same tracing datasource default as compose."""
    content = Path("grafana/README.md").read_text(encoding="utf-8")
    assert "`BIOETL_ENABLE_TRACING_DATASOURCES`            | `auto`" in content


def test_bootstrap_script_detects_tracing_datasource_reachability() -> None:
    """Bootstrap script must auto-detect Loki/Tempo before pruning datasources."""
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )
    assert "BIOETL_ENABLE_TRACING_DATASOURCES:-auto" in content
    assert "AUTO_WAIT_SECONDS=30" in content
    assert "AUTO_POLL_SECONDS=1" in content
    assert "deadline=$(($(date +%s) + AUTO_WAIT_SECONDS))" in content
    assert 'remaining="$(remaining_auto_wait_seconds)"' in content
    assert 'requested_timeout="${2:-2}"' in content
    assert '--timeout="${probe_timeout}"' in content
    assert "wait_for_auto_tracing_ready()" in content
    assert 'probe_ready "http://loki:3100/ready" "${remaining}"' in content
    assert 'probe_ready "http://tempo:3200/ready" "${remaining}"' in content
    assert "deleteDatasources:" in content
    assert "name: Loki" in content
    assert "name: Tempo" in content


@pytest.mark.parametrize(
    ("timeout_args", "expected_timeout"),
    [
        ((), "--timeout=2"),
        (("1",), "--timeout=1"),
        (("10",), "--timeout=2"),
    ],
)
def test_bootstrap_probe_ready_honors_one_and_two_argument_forms(
    tmp_path: Path,
    timeout_args: tuple[str, ...],
    expected_timeout: str,
) -> None:
    fake_bin = tmp_path / "bin"
    fake_bin.mkdir()
    wget = fake_bin / "wget"
    wget.write_text(
        '#!/bin/sh\nprintf \'%s\\n\' "$@" > "$BIOETL_WGET_ARGS_FILE"\n',
        encoding="utf-8",
    )
    wget.chmod(0o755)
    args_file = tmp_path / "wget-args.txt"
    environment = os.environ.copy()
    environment.update(
        {
            "BIOETL_BOOTSTRAP_PROBE_ONLY": "1",
            "BIOETL_WGET_ARGS_FILE": str(args_file),
            "PATH": f"{fake_bin}{os.pathsep}{environment['PATH']}",
        }
    )

    result = subprocess.run(
        [
            "sh",
            "grafana/scripts/bootstrap-datasources.sh",
            "http://loki:3100/ready",
            *timeout_args,
        ],
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )

    assert result.returncode == 0, result.stderr
    assert expected_timeout in args_file.read_text(encoding="utf-8").splitlines()


def test_bootstrap_script_prunes_stale_local_renderer_plugin_in_remote_mode() -> None:
    """Remote renderer mode must delete stale local plugin installs from the Grafana data volume."""
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )
    assert 'RENDERING_SERVER_URL="${GF_RENDERING_SERVER_URL:-}"' in content
    assert (
        'STALE_RENDERER_PLUGIN_DIR="/var/lib/grafana/plugins/grafana-image-renderer"'
        in content
    )
    assert 'rm -rf "${STALE_RENDERER_PLUGIN_DIR}"' in content
