"""Integration checks for Grafana datasource provisioning assets."""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.integration


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
