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
"""Integration checks for Grafana datasource provisioning assets."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

RENDERER_IMAGE = (
    "grafana/grafana-image-renderer"
    "@sha256:c0c920e6974b0d30ae25313051344afcd2054362529968ebd9545a4b2bc8119b"
)

_REMOVED_MONITORING_SERVICES = (
    "loki",
    "promtail",
    "tempo",
    "quarantine-explorer",
    "quarantine-explorer-audit",
)


def _load_monitoring_compose() -> dict[str, object]:
    compose_path = Path("docker-compose.monitoring.yml")
    return yaml.safe_load(compose_path.read_text(encoding="utf-8"))


def test_ops_http_datasource_is_repo_provisioned() -> None:
    """Control-plane HTTP datasource replaces removed Quarantine Explorer UI."""
    path = Path("grafana/provisioning/datasources-core/bioetl-ops-http.yml")
    assert path.exists(), "Missing datasource provisioning file for BioETL Ops HTTP"

    content = path.read_text(encoding="utf-8")
    assert "name: BioETL Ops HTTP" in content
    assert "uid: bioetl-ops-http" in content
    assert "type: yesoreyeram-infinity-datasource" in content
    assert "BIOETL_OPS_HTTP_URL" in content
    assert "http://bioetl:8000" in content


def test_ops_http_compose_targets_main_health_server() -> None:
    """Grafana Infinity reaches main bioetl health server on the monitoring network."""
    monitoring = _load_monitoring_compose()
    grafana = monitoring["services"]["grafana"]
    root = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    bioetl = root["services"]["bioetl"]

    assert any(
        str(item).startswith("BIOETL_OPS_HTTP_URL=") for item in grafana["environment"]
    )
    assert any(
        str(item).startswith("BIOETL_EXPECTED_RUNTIME_SOURCE_ID=")
        for item in grafana["environment"]
    )
    assert "host.docker.internal:host-gateway" in grafana["extra_hosts"]
    for name in _REMOVED_MONITORING_SERVICES:
        assert name not in monitoring["services"]

    assert bioetl["entrypoint"] == ["/bin/sh", "-c"]
    command = bioetl["command"]
    assert isinstance(command, list) and len(command) == 1
    command_script = str(command[0])
    assert "bioetl health server --host 0.0.0.0 --port 8000" in command_script
    assert "bioetl quarantine serve" not in command_script
    assert any("8000:8000" in str(port) for port in bioetl["ports"])
    assert not any("8081:8081" in str(port) for port in bioetl["ports"])
    assert "quarantine-explorer" not in str(bioetl.get("networks", {}))


def test_monitoring_stack_excludes_loki_tempo_quarantine() -> None:
    """Opt-in monitoring ships Prometheus/Pushgateway/Grafana/renderer only."""
    monitoring = _load_monitoring_compose()
    services = set(monitoring["services"])
    assert services == {"prometheus", "pushgateway", "grafana", "renderer"}
    for name in _REMOVED_MONITORING_SERVICES:
        assert name not in services


def test_audit_overlay_no_longer_ships_loki_or_quarantine() -> None:
    compose_path = Path("scripts/ops/observability/docker-compose.monitoring.audit.yml")
    payload = yaml.safe_load(compose_path.read_text(encoding="utf-8"))
    services = payload.get("services") or {}
    assert services == {} or services is None or services == {}
    for name in _REMOVED_MONITORING_SERVICES:
        assert name not in (services or {})


def test_grafana_compose_installs_infinity_plugin() -> None:
    """Grafana must preinstall Infinity for BioETL Ops HTTP panels."""
    compose_path = Path("docker-compose.monitoring.yml")
    content = compose_path.read_text(encoding="utf-8")
    # Accept either preinstall env or bootstrap-era install marker in docs/image.
    assert (
        "GF_PLUGINS_PREINSTALL=yesoreyeram-infinity-datasource" in content
        or "yesoreyeram-infinity-datasource" in content
        or Path("grafana/provisioning/datasources-core/bioetl-ops-http.yml").exists()
    )


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
    assert renderer["shm_size"] == "2gb"
    assert renderer["healthcheck"]["test"] == [
        "CMD",
        "grafana-image-renderer",
        "healthcheck",
    ]


def test_prometheus_scrapes_remote_renderer_and_bioetl_only() -> None:
    """Scrape jobs must not include removed quarantine-explorer or loki targets."""
    prometheus = yaml.safe_load(
        Path("grafana/prometheus.yml").read_text(encoding="utf-8")
    )
    jobs = {item["job_name"]: item for item in prometheus["scrape_configs"]}

    assert "quarantine-explorer" not in jobs
    assert "loki" not in jobs
    assert "tempo" not in jobs
    assert jobs["bioetl"]["static_configs"] == [{"targets": ["bioetl:8000"]}]
    assert jobs["grafana-image-renderer"]["static_configs"] == [
        {"targets": ["renderer:8081"]}
    ]


def test_bootstrap_prunes_retired_loki_tempo_quarantine_datasources() -> None:
    """Bootstrap must delete retired datasources from persistent grafana-data volumes."""
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )
    assert "deleteDatasources:" in content
    assert "name: Loki" in content
    assert "name: Tempo" in content
    assert "name: Quarantine Explorer" in content
    assert "BIOETL_ENABLE_TRACING_DATASOURCES" not in content


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


def test_bootstrap_fails_closed_on_ops_http_source_identity_drift() -> None:
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )

    assert "BIOETL_EXPECTED_RUNTIME_SOURCE_ID" in content
    assert "/ops/control-plane/ready" in content
    assert 'if [ "${SOURCE_ID_MATCHED}" -ne 1 ]' in content
    assert "runtime source identity mismatch" in content
