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

import json
import os
from pathlib import Path
import shutil
import subprocess

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
    assert "GF_DATE_FORMATS_FULL_DATE=YYYY-MM-DD HH:mm" in [
        str(item) for item in grafana["environment"]
    ]
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


def test_monitoring_images_are_pinned_and_pushgateway_is_not_a_datasource() -> None:
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

    core = yaml.safe_load(
        Path("grafana/provisioning/datasources-core/prometheus.yml").read_text(
            encoding="utf-8"
        )
    )
    assert [datasource["name"] for datasource in core["datasources"]] == ["Prometheus"]
    prometheus = core["datasources"][0]
    assert prometheus["uid"] == "prometheus"
    assert prometheus["url"] == "http://prometheus:9090"
    assert prometheus["jsonData"]["timeInterval"] == "30s"
    assert "pushgateway:9091" not in str(core).lower()


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
    assert renderer["shm_size"] == "512mb"
    flags = next(
        item
        for item in renderer["environment"]
        if str(item).startswith("BROWSER_FLAGS=")
    )
    assert "--disable-dev-shm-usage" not in flags
    assert "--disable-software-rasterizer" not in flags
    assert renderer["healthcheck"]["test"] == [
        "CMD",
        "grafana-image-renderer",
        "healthcheck",
    ]
    assert renderer["healthcheck"]["start_period"] == "45s"


def test_grafana_does_not_hard_depend_on_renderer_health() -> None:
    """UI must start without waiting for Chromium renderer (optional screenshots)."""
    monitoring = _load_monitoring_compose()
    depends = monitoring["services"]["grafana"].get("depends_on") or {}
    assert "renderer" not in depends
    assert depends.get("prometheus", {}).get("condition") == "service_healthy"
    assert depends.get("pushgateway", {}).get("condition") == "service_started"


def test_grafana_renderer_fail_fast_and_recovery_contract() -> None:
    """Dead renderer must not hang Grafana; recovery is renderer-only."""
    monitoring = _load_monitoring_compose()
    grafana_env = monitoring["services"]["grafana"]["environment"]
    renderer = monitoring["services"]["renderer"]

    assert (
        "GF_RENDERING_RENDERING_TIMEOUT=${GF_RENDERING_RENDERING_TIMEOUT:-60s}"
        in grafana_env
    )
    renderer_env = renderer["environment"]
    assert any(
        str(item).startswith("BROWSER_READINESS_DISABLE_NETWORK_WAIT=")
        for item in renderer_env
    )
    assert any(
        str(item).startswith("BROWSER_READINESS_GIVE_UP_ON_ALL_QUERIES=")
        for item in renderer_env
    )
    assert any(
        str(item).startswith("BROWSER_WS_URL_READ_TIMEOUT=") for item in renderer_env
    )
    assert (
        "GF_RENDERING_CONCURRENT_RENDER_REQUEST_LIMIT="
        "${GF_RENDERING_CONCURRENT_RENDER_REQUEST_LIMIT:-1}" in grafana_env
    )
    assert renderer["restart"] == "on-failure:3"
    assert renderer.get("oom_score_adj") == 800

    recover_ps1 = Path("scripts/ops/observability/grafana/recover_renderer.ps1")
    recover_sh = Path("scripts/ops/observability/grafana/recover_renderer.sh")
    assert recover_ps1.is_file()
    assert recover_sh.is_file()
    ps1 = recover_ps1.read_text(encoding="utf-8")
    assert "force-recreate" in ps1
    assert "renderer" in ps1
    assert "UI stays up" in ps1


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


def test_bootstrap_prunes_retired_and_non_query_datasources() -> None:
    """Bootstrap must delete retired datasources from persistent grafana-data volumes."""
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )
    assert "deleteDatasources:" in content
    assert "name: Loki" in content
    assert "name: Tempo" in content
    assert "name: Quarantine Explorer" in content
    assert "name: Pushgateway" in content
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
    """Ops HTTP trust is optional; Grafana UI start is not blocked by default.

    Soft mode: short ready poll (5×1s), Prometheus first, then defer Ops on
    timeout/mismatch/unmanaged identity and still exec /run.sh.
    Fail-closed only when BIOETL_GRAFANA_REQUIRE_OPS_HTTP=1 (longer poll + exit 1).
    """
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )

    assert "BIOETL_EXPECTED_RUNTIME_SOURCE_ID" in content
    assert "/ops/control-plane/ready" in content
    assert 'REQUIRE_OPS_HTTP="${BIOETL_GRAFANA_REQUIRE_OPS_HTTP:-0}"' in content
    # Soft defaults are short; fail-closed uses 30×2s.
    assert 'OPS_READY_ATTEMPTS="${BIOETL_GRAFANA_OPS_READY_ATTEMPTS:-5}"' in content
    assert 'OPS_READY_SLEEP_SEC="${BIOETL_GRAFANA_OPS_READY_SLEEP_SEC:-1}"' in content
    assert 'OPS_READY_ATTEMPTS="${BIOETL_GRAFANA_OPS_READY_ATTEMPTS:-30}"' in content
    assert 'OPS_READY_SLEEP_SEC="${BIOETL_GRAFANA_OPS_READY_SLEEP_SEC:-2}"' in content
    assert "fail_or_defer_ops" in content
    assert (
        "provision_prometheus_only" in content
        or "starting Grafana with Prometheus only" in content
    )
    # Prometheus must be provisioned before the Ops ready poll (no 60s block).
    prom_idx = content.index("provision_prometheus_only")
    poll_idx = content.index("Ops HTTP ready poll:")
    assert prom_idx < poll_idx
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
    grafana = monitoring["services"]["grafana"]
    grafana_environment = grafana["environment"]
    assert (
        "BIOETL_GRAFANA_REQUIRE_OPS_HTTP=${BIOETL_GRAFANA_REQUIRE_OPS_HTTP:-0}"
        in grafana_environment
    )
    # Empty compose defaults: bootstrap picks soft 5×1s or fail-closed 30×2s.
    assert any(
        "BIOETL_GRAFANA_OPS_READY_ATTEMPTS=" in item for item in grafana_environment
    )
    assert any(
        "BIOETL_GRAFANA_OPS_READY_SLEEP_SEC=" in item for item in grafana_environment
    )
    volumes = {str(item) for item in grafana["volumes"]}
    assert (
        "./grafana/provisioning/dashboards:"
        "/etc/bioetl-grafana/dashboard-providers/full:ro" in volumes
    )
    assert (
        "./grafana/provisioning/dashboards-prometheus-only:"
        "/etc/bioetl-grafana/dashboard-providers/prometheus-only:ro" in volumes
    )
    assert (
        "./grafana/dashboards-prometheus-only:"
        "/var/lib/grafana/dashboards-prometheus-only:ro" in volumes
    )
    assert not any(
        item.endswith(":/etc/grafana/provisioning/dashboards:ro") for item in volumes
    )


def _run_bootstrap_profile(
    tmp_path: Path,
    *,
    runtime_source_id: str,
    ready: bool,
) -> tuple[subprocess.CompletedProcess[str], Path, Path, Path]:
    shell = shutil.which("sh")
    if shell is None:
        pytest.skip("POSIX sh is required for the Grafana bootstrap integration test")

    datasource_target = tmp_path / "datasources"
    datasource_core = tmp_path / "datasources-core"
    provider_target = tmp_path / "dashboard-providers-target"
    provider_full = tmp_path / "dashboard-providers-full"
    provider_fallback = tmp_path / "dashboard-providers-prometheus-only"
    status_file = tmp_path / "bootstrap-status.json"
    datasource_core.mkdir()
    provider_full.mkdir()
    provider_fallback.mkdir()
    (datasource_core / "prometheus.yml").write_text(
        "apiVersion: 1\ndatasources: []\n", encoding="utf-8"
    )
    (provider_full / "bioetl.yaml").write_text(
        "apiVersion: 1\nprofile: full\n", encoding="utf-8"
    )
    (provider_fallback / "bioetl.yaml").write_text(
        "apiVersion: 1\nprofile: prometheus_only\n", encoding="utf-8"
    )

    env = os.environ.copy()
    env.update(
        {
            "BIOETL_GRAFANA_DATASOURCE_TARGET_DIR": str(datasource_target),
            "BIOETL_GRAFANA_DATASOURCE_CORE_DIR": str(datasource_core),
            "BIOETL_GRAFANA_DASHBOARD_PROVIDER_TARGET_DIR": str(provider_target),
            "BIOETL_GRAFANA_DASHBOARD_PROVIDER_FULL_DIR": str(provider_full),
            "BIOETL_GRAFANA_DASHBOARD_PROVIDER_FALLBACK_DIR": str(provider_fallback),
            "BIOETL_GRAFANA_BOOTSTRAP_STATUS_FILE": str(status_file),
            "BIOETL_GRAFANA_RUN_SCRIPT": shutil.which("true") or "/bin/true",
            "BIOETL_EXPECTED_RUNTIME_SOURCE_ID": runtime_source_id,
            "BIOETL_OPS_HTTP_URL": "http://bioetl:8000",
            "BIOETL_GRAFANA_REQUIRE_OPS_HTTP": "0",
            "BIOETL_GRAFANA_OPS_READY_ATTEMPTS": "1",
            "BIOETL_GRAFANA_OPS_READY_SLEEP_SEC": "0",
            "GF_RENDERING_SERVER_URL": "",
        }
    )
    if ready:
        fake_bin = tmp_path / "bin"
        fake_bin.mkdir()
        wget = fake_bin / "wget"
        wget.write_text(
            "#!/bin/sh\nprintf '%s\\n' "
            f'\'{{"runtime_source_id":"{runtime_source_id}"}}\'\n',
            encoding="utf-8",
        )
        wget.chmod(0o755)
        plugin_dir = tmp_path / "plugins" / "yesoreyeram-infinity-datasource"
        plugin_dir.mkdir(parents=True)
        (plugin_dir / "plugin.json").write_text(
            '{\n  "version": "3.8.0"\n}\n', encoding="utf-8"
        )
        env["PATH"] = f"{fake_bin}{os.pathsep}{env.get('PATH', '')}"
        env["BIOETL_INFINITY_PLUGIN_DIR"] = str(plugin_dir)

    result = subprocess.run(
        [shell, str(Path("grafana/scripts/bootstrap-datasources.sh").resolve())],
        cwd=Path.cwd(),
        env=env,
        capture_output=True,
        text=True,
        check=False,
        timeout=15,
    )
    return result, datasource_target, provider_target, status_file


def test_bootstrap_selects_static_dashboard_profile_when_ops_http_is_deferred(
    tmp_path: Path,
) -> None:
    result, datasource_target, provider_target, status_file = _run_bootstrap_profile(
        tmp_path,
        runtime_source_id="unmanaged",
        ready=False,
    )

    assert result.returncode == 0, result.stderr
    assert "profile: prometheus_only" in (provider_target / "bioetl.yaml").read_text(
        encoding="utf-8"
    )
    assert not (datasource_target / "bioetl-ops-http.yml").exists()
    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert status["ops_http"] == "deferred"
    assert status["reason"] == "invalid_or_unmanaged_identity"
    assert status["dashboard_profile"] == "prometheus_only"


def test_bootstrap_selects_full_dashboard_profile_after_identity_match(
    tmp_path: Path,
) -> None:
    runtime_source_id = "a" * 64
    result, datasource_target, provider_target, status_file = _run_bootstrap_profile(
        tmp_path,
        runtime_source_id=runtime_source_id,
        ready=True,
    )

    assert result.returncode == 0, result.stderr
    assert "profile: full" in (provider_target / "bioetl.yaml").read_text(
        encoding="utf-8"
    )
    assert (datasource_target / "bioetl-ops-http.yml").exists()
    status = json.loads(status_file.read_text(encoding="utf-8"))
    assert status["ops_http"] == "ready"
    assert status["reason"] == "identity_matched"
    assert status["dashboard_profile"] == "full"


def test_monitoring_compose_local_resource_budget() -> None:
    """Grafana+renderer must not reserve ~32 GiB peak on local hosts."""
    monitoring = _load_monitoring_compose()
    prom = monitoring["services"]["prometheus"]
    grafana = monitoring["services"]["grafana"]
    renderer = monitoring["services"]["renderer"]
    pushgateway = monitoring["services"]["pushgateway"]

    assert prom["mem_limit"] == "3g"
    assert prom.get("memswap_limit") == "3g"
    prom_env = prom.get("environment") or []
    assert any("GOMEMLIMIT=" in str(item) for item in prom_env)
    assert any("GOGC=" in str(item) for item in prom_env)
    prom_cmd = prom.get("command") or []
    assert "--query.max-concurrency=2" in prom_cmd
    assert "--storage.tsdb.retention.size=2GB" in prom_cmd
    assert grafana["mem_limit"] == "2g"
    assert renderer["mem_limit"] == "3g"
    assert pushgateway["mem_limit"] == "512m"
    assert renderer["shm_size"] == "512mb"
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
