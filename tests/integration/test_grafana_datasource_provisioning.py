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


def test_grafana_compose_installs_infinity_plugin() -> None:
    """Grafana container must install the Infinity datasource plugin."""
    compose_path = Path("docker-compose.monitoring.yml")
    content = compose_path.read_text(encoding="utf-8")
    assert "GF_PLUGINS_PREINSTALL=yesoreyeram-infinity-datasource" in content
    assert "GF_INSTALL_PLUGINS=yesoreyeram-infinity-datasource" in content


def test_tracing_datasource_default_matches_optional_tracing_profile() -> None:
    """Tracing datasources must default off when Loki/Tempo are profile-gated."""
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
        "BIOETL_ENABLE_TRACING_DATASOURCES=${BIOETL_ENABLE_TRACING_DATASOURCES:-false}"
        in grafana["environment"]
    ), (
        "Grafana tracing datasources must default off when Loki/Tempo are not part "
        "of the default monitoring topology"
    )


def test_grafana_readme_matches_tracing_datasource_default() -> None:
    """Operator docs must describe the same tracing datasource default as compose."""
    content = Path("grafana/README.md").read_text(encoding="utf-8")
    assert "`BIOETL_ENABLE_TRACING_DATASOURCES`            | `false`" in content


def test_bootstrap_script_prunes_tracing_datasources_when_disabled() -> None:
    """Bootstrap script must delete Loki/Tempo datasources in tracing-off mode."""
    content = Path("grafana/scripts/bootstrap-datasources.sh").read_text(
        encoding="utf-8"
    )
    assert 'BIOETL_ENABLE_TRACING_DATASOURCES:-false' in content
    assert 'if [ "${TRACING_FLAG}" = "true" ]; then' in content
    assert "deleteDatasources:" in content
    assert "name: Loki" in content
    assert "name: Tempo" in content
