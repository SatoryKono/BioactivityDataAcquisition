"""Integration checks for Grafana datasource provisioning assets."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml


pytestmark = pytest.mark.integration


def _load_monitoring_compose() -> dict[str, object]:
    compose_path = Path("docker-compose.monitoring.yml")
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

    assert "bioetl quarantine serve --port 8081" in readme
    assert "dedicated long-lived BioETL HTTP" in readme
    assert "compatibility entrypoint" in readme
    assert "bioetl quarantine serve --port 8081" in env_example
    assert (
        "BIOETL_QUARANTINE_EXPLORER_URL=http://host.docker.internal:8081"
        in env_example
    )


def test_quarantine_explorer_compose_uses_host_gateway_backend() -> None:
    """Grafana must resolve the Quarantine Explorer backend through host-gateway by default."""
    monitoring = _load_monitoring_compose()
    grafana = monitoring["services"]["grafana"]
    root = yaml.safe_load(Path("docker-compose.yml").read_text(encoding="utf-8"))
    bioetl = root["services"]["bioetl"]

    assert (
        "BIOETL_QUARANTINE_EXPLORER_URL=${BIOETL_QUARANTINE_EXPLORER_URL:-http://host.docker.internal:8081}"
        in grafana["environment"]
    )
    assert "host.docker.internal:host-gateway" in grafana["extra_hosts"]
    assert bioetl["command"] == [
        "quarantine",
        "serve",
        "--host",
        "0.0.0.0",
        "--port",
        "8081",
    ]


def test_grafana_compose_installs_infinity_plugin() -> None:
    """Grafana container must install the Infinity datasource plugin."""
    compose_path = Path("docker-compose.monitoring.yml")
    content = compose_path.read_text(encoding="utf-8")
    assert "GF_PLUGINS_PREINSTALL=yesoreyeram-infinity-datasource" in content
    assert "GF_INSTALL_PLUGINS=yesoreyeram-infinity-datasource" in content


def test_quarantine_explorer_defaults_to_host_gateway_backend() -> None:
    """Monitoring compose should route explorer traffic through host-gateway by default."""
    compose_path = Path("docker-compose.monitoring.yml")
    content = compose_path.read_text(encoding="utf-8")
    monitoring = _load_monitoring_compose()
    assert (
        "BIOETL_QUARANTINE_EXPLORER_URL=${BIOETL_QUARANTINE_EXPLORER_URL:-http://host.docker.internal:8081}"
        in content
    )
    assert monitoring["networks"]["monitoring"]["name"] == "bioetl-monitoring"
    assert monitoring["networks"]["monitoring"]["external"] is True


def test_grafana_uses_remote_renderer_sidecar() -> None:
    """Grafana monitoring stack should use a supported remote renderer service."""
    monitoring = _load_monitoring_compose()
    grafana = monitoring["services"]["grafana"]
    renderer = monitoring["services"]["renderer"]

    assert (
        "GF_RENDERING_SERVER_URL=http://renderer:8081/render"
        in grafana["environment"]
    )
    assert "GF_RENDERING_CALLBACK_URL=http://grafana:3000/" in grafana["environment"]
    assert grafana["entrypoint"] == ["/bin/sh", "/usr/local/bin/bioetl-bootstrap-grafana.sh"]
    assert renderer["image"] == "grafana/grafana-image-renderer:latest"


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
    assert 'wget --quiet --tries=1 --timeout=2 -O /dev/null "$1"' in content
    assert 'probe_ready "http://loki:3100/ready"' in content
    assert 'probe_ready "http://tempo:3200/ready"' in content
    assert "deleteDatasources:" in content
    assert "name: Loki" in content
    assert "name: Tempo" in content


def test_bootstrap_script_prunes_stale_local_renderer_plugin_in_remote_mode() -> None:
    """Remote renderer mode must delete stale local plugin installs from the Grafana data volume."""
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )
    assert 'RENDERING_SERVER_URL="${GF_RENDERING_SERVER_URL:-}"' in content
    assert 'STALE_RENDERER_PLUGIN_DIR="/var/lib/grafana/plugins/grafana-image-renderer"' in content
    assert 'rm -rf "${STALE_RENDERER_PLUGIN_DIR}"' in content
