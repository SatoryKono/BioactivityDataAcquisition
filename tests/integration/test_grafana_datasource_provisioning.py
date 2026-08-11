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
INFINITY_PLUGIN_VERSION = "3.8.0"

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

    payload = yaml.safe_load(content)
    datasource = payload["datasources"][0]
    expected_backend_url = "${BIOETL_OPS_HTTP_URL:-http://bioetl:8000}"
    assert datasource["uid"] == "bioetl-ops-http"
    assert datasource["access"] == "proxy"
    assert datasource["url"] == expected_backend_url
    assert datasource["jsonData"]["allowedHosts"] == [expected_backend_url]


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


def test_grafana_compose_pins_compatible_infinity_plugin() -> None:
    """Grafana must enforce the Infinity version compatible with Grafana 12.0."""
    monitoring = _load_monitoring_compose()
    grafana_environment = monitoring["services"]["grafana"]["environment"]
    assert (
        "BIOETL_INFINITY_PLUGIN_VERSION="
        "${BIOETL_INFINITY_PLUGIN_VERSION:-3.8.0}" in grafana_environment
    )
    assert not any(
        str(item).startswith("GF_INSTALL_PLUGINS=") for item in grafana_environment
    )

    bootstrap = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )
    assert (
        'INFINITY_PLUGIN_VERSION="${BIOETL_INFINITY_PLUGIN_VERSION:-3.8.0}"'
        in bootstrap
    )
    assert '"${INFINITY_PLUGIN_ID}" "${INFINITY_PLUGIN_VERSION}"' in bootstrap
    assert INFINITY_PLUGIN_VERSION in bootstrap


def test_monitoring_images_are_pinned_and_legacy_pushgateway_datasource_is_inert() -> (
    None
):
    monitoring = _load_monitoring_compose()
    assert monitoring["services"]["grafana"]["image"] == (
        "grafana/grafana:12.0.0@sha256:"
        "263cbefd5d9b179893c47c415daab4da5c1f3d6770154741eca4f45c81119884"
    )
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
    # Local budget: small shm (BROWSER_FLAGS disables /dev/shm); was 2gb.
    assert renderer["shm_size"] == "256mb"
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


def test_bootstrap_ops_http_identity_gate_is_soft_by_default() -> None:
    """Ops HTTP trust is fail-closed; Grafana UI start is not blocked by default.

    Cold start polls bioetl:8000 ready (default 30×2s). On timeout/mismatch/
    unmanaged identity the script defers Ops HTTP and still execs /run.sh unless
    BIOETL_GRAFANA_REQUIRE_OPS_HTTP=1. Prometheus is always provisioned as fallback.
    """
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )

    assert "BIOETL_EXPECTED_RUNTIME_SOURCE_ID" in content
    assert "/ops/control-plane/ready" in content
    assert 'REQUIRE_OPS_HTTP="${BIOETL_GRAFANA_REQUIRE_OPS_HTTP:-0}"' in content
    assert 'OPS_READY_ATTEMPTS="${BIOETL_GRAFANA_OPS_READY_ATTEMPTS:-30}"' in content
    assert 'OPS_READY_SLEEP_SEC="${BIOETL_GRAFANA_OPS_READY_SLEEP_SEC:-2}"' in content
    assert "fail_or_defer_ops" in content
    assert (
        "provision_prometheus_only" in content
        or "starting Grafana with Prometheus only" in content
    )
    assert "is_valid_ops_http_url" in content
    assert (
        "invalid_or_unmanaged_identity" in content or "invalid_ops_http_url" in content
    )
    assert (
        "identity_mismatch_or_timeout" in content
        or "identity_mismatch" in content
        or "identity_timeout_or_unreachable" in content
    )
    assert "bioetl-bootstrap-status.json" in content
    assert "exec /run.sh" in content
    # Hard fail only when audit/render explicitly requires Ops HTTP.
    assert 'if [ "${REQUIRE_OPS_HTTP}" = "1" ]' in content
    assert (
        "Ops HTTP required but unavailable" in content or "REQUIRE_OPS_HTTP" in content
    )


def test_monitoring_compose_exposes_ops_http_soft_gate_env() -> None:
    monitoring = _load_monitoring_compose()
    grafana_environment = monitoring["services"]["grafana"]["environment"]
    assert (
        "BIOETL_GRAFANA_REQUIRE_OPS_HTTP=${BIOETL_GRAFANA_REQUIRE_OPS_HTTP:-0}"
        in grafana_environment
    )
    assert (
        "BIOETL_GRAFANA_OPS_READY_ATTEMPTS=${BIOETL_GRAFANA_OPS_READY_ATTEMPTS:-30}"
        in grafana_environment
    )
    assert (
        "BIOETL_GRAFANA_OPS_READY_SLEEP_SEC=${BIOETL_GRAFANA_OPS_READY_SLEEP_SEC:-2}"
        in grafana_environment
    )


def test_monitoring_compose_local_resource_budget() -> None:
    """Grafana+renderer must not reserve ~32 GiB peak on local hosts."""
    monitoring = _load_monitoring_compose()
    prom = monitoring["services"]["prometheus"]
    grafana = monitoring["services"]["grafana"]
    renderer = monitoring["services"]["renderer"]
    pushgateway = monitoring["services"]["pushgateway"]

    assert prom["mem_limit"] == "3g"
    assert grafana["mem_limit"] == "2g"
    assert renderer["mem_limit"] == "3g"
    assert pushgateway["mem_limit"] == "512m"
    assert renderer["shm_size"] == "256mb"
    assert (
        "RENDERING_CLUSTERING_MAX_CONCURRENCY="
        "${GRAFANA_IMAGE_RENDERER_MAX_CONCURRENCY:-1}" in renderer["environment"]
    )
    assert (
        "GOMEMLIMIT=${GRAFANA_IMAGE_RENDERER_GOMEMLIMIT:-1GiB}"
        in renderer["environment"]
    )
    assert (
        "BIOETL_GRAFANA_REQUIRE_OPS_HTTP=${BIOETL_GRAFANA_REQUIRE_OPS_HTTP:-0}"
        in grafana["environment"]
    )


def test_bootstrap_validates_ops_http_url_before_probe() -> None:
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )
    fn_idx = content.index("is_valid_ops_http_url()")
    gate_idx = content.index('if is_valid_ops_http_url "${BIOETL_OPS_HTTP_URL}"')
    wget_idx = content.index('wget -qO- -T 3 "${OPS_READY_URL}"')
    assert fn_idx < gate_idx < wget_idx
