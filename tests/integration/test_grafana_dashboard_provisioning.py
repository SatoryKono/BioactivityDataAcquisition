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
"""Fail-closed contracts for Grafana dashboard file provisioning."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml

pytestmark = pytest.mark.integration

_PROVISIONING_DIR = Path("grafana/provisioning/dashboards")
_CANONICAL_PROVIDER_FILE = _PROVISIONING_DIR / "bioetl.yaml"
_REMOVED_DUPLICATE_PROVIDER_FILE = _PROVISIONING_DIR / "dashboards.yml"
_PROMETHEUS_ONLY_PROVISIONING_FILE = Path(
    "grafana/provisioning/dashboards-prometheus-only/bioetl.yaml"
)
_DASHBOARD_DIR = Path("grafana/dashboards")
_PROMETHEUS_ONLY_DASHBOARD_DIR = Path("grafana/dashboards-prometheus-only")


def _provider_paths(payload: object) -> list[str]:
    assert isinstance(payload, dict), "dashboard provisioning file must be a mapping"
    providers = payload.get("providers")
    assert isinstance(providers, list), "providers must be a list"
    paths: list[str] = []
    for entry in providers:
        assert isinstance(entry, dict), "each provider entry must be a mapping"
        options = entry.get("options")
        assert isinstance(options, dict), "provider options must be a mapping"
        path = options.get("path")
        assert isinstance(path, str) and path, "provider options.path must be a string"
        paths.append(path)
    return paths


@pytest.mark.parametrize("profile", ["dashboards", "dashboards-prometheus-only"])
def test_each_dashboard_has_one_provider_and_preserves_folder_access(profile: str) -> None:
    """Providers have disjoint files; only Run Explorer stays in BioETL."""
    directory = Path("grafana/provisioning") / profile
    files = sorted(directory.glob("*.y*ml"))
    assert files == [directory / "bioetl.yaml"]
    providers = yaml.safe_load(files[0].read_text(encoding="utf-8"))["providers"]
    expected = {path.name for path in (Path("grafana") / profile).glob("*.json")}
    paths = _provider_paths({"providers": providers})
    assert len(paths) == len(set(paths)) == len(expected) == 5
    assert {Path(path).name for path in paths} == expected
    assert len({p["name"] for p in providers}) == 5
    assert providers[0]["name"] == "BioETL"
    for provider in providers:
        path = provider["options"]["path"]
        assert path.startswith(f"/var/lib/grafana/{profile}/")
        explorer = path.endswith("/bioetl-run-explorer-v1.json")
        assert provider["folderUid"] == ("bioetl" if explorer else "bioetl-details")
        assert provider["folder"] == ("BioETL" if explorer else "Details")
        assert provider["type"] == "file"
        assert provider["updateIntervalSeconds"] == 30
        assert provider["allowUiUpdates"] is False
        assert provider["disableDeletion"] is True


def _walk_objects(value: object) -> list[dict[str, Any]]:
    objects: list[dict[str, Any]] = []
    if isinstance(value, dict):
        objects.append(value)
        for nested in value.values():
            objects.extend(_walk_objects(nested))
    elif isinstance(value, list):
        for nested in value:
            objects.extend(_walk_objects(nested))
    return objects


def test_prometheus_only_profile_preserves_uids_without_query_targets() -> None:
    full_dashboards = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(_DASHBOARD_DIR.glob("*.json"))
    }
    fallback_dashboards = {
        path.name: json.loads(path.read_text(encoding="utf-8"))
        for path in sorted(_PROMETHEUS_ONLY_DASHBOARD_DIR.glob("*.json"))
    }

    assert fallback_dashboards.keys() == full_dashboards.keys()
    assert len(fallback_dashboards) == 5
    for name, fallback in fallback_dashboards.items():
        full = full_dashboards[name]
        assert fallback["uid"] == full["uid"]
        assert fallback["title"] == full["title"]
        assert fallback["tags"] == [
            "bioetl",
            "prometheus-only",
            "ops-http-unavailable",
        ]
        assert len(fallback["panels"]) == 1
        panel = fallback["panels"][0]
        assert panel["type"] == "text"
        content = panel["options"]["content"]
        assert "Ops HTTP not provisioned" in content
        assert "dashboard_profile=full" in content
        assert "No retention, replay, identity, or run verdict" in content
        for item in _walk_objects(fallback):
            assert "datasource" not in item
            assert not item.get("targets")
