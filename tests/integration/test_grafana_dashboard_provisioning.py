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

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.integration

_PROVISIONING_DIR = Path("grafana/provisioning/dashboards")
_CANONICAL_PROVIDER_FILE = _PROVISIONING_DIR / "bioetl.yaml"
_REMOVED_DUPLICATE_PROVIDER_FILE = _PROVISIONING_DIR / "dashboards.yml"


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


def test_single_canonical_dashboard_provider_owns_shipped_json_directory() -> None:
    """Exactly one file provider may target the shipped dashboards directory."""
    assert _CANONICAL_PROVIDER_FILE.is_file(), (
        "canonical dashboard provider grafana/provisioning/dashboards/bioetl.yaml "
        "must exist"
    )
    assert not _REMOVED_DUPLICATE_PROVIDER_FILE.exists(), (
        "duplicate provider grafana/provisioning/dashboards/dashboards.yml must not "
        "be reintroduced; it double-loads /var/lib/grafana/dashboards"
    )

    payload = yaml.safe_load(_CANONICAL_PROVIDER_FILE.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    providers = payload.get("providers")
    assert isinstance(providers, list) and len(providers) == 1, (
        "canonical provider file must declare exactly one provider"
    )
    provider = providers[0]
    assert isinstance(provider, dict)
    assert provider.get("name") == "BioETL"
    assert provider.get("folder") == "BioETL"
    assert provider.get("folderUid") == "bioetl"
    assert provider.get("type") == "file"
    assert provider.get("updateIntervalSeconds") == 30
    assert provider.get("allowUiUpdates") is False
    assert provider.get("options", {}).get("path") == "/var/lib/grafana/dashboards"

    yaml_files = sorted(_PROVISIONING_DIR.glob("*.y*ml"))
    assert yaml_files == [_CANONICAL_PROVIDER_FILE], (
        "dashboard provisioning directory must contain only the canonical "
        f"bioetl.yaml provider; found {[path.name for path in yaml_files]}"
    )

    all_paths: list[str] = []
    for path in yaml_files:
        all_paths.extend(
            _provider_paths(yaml.safe_load(path.read_text(encoding="utf-8")))
        )
    assert all_paths == ["/var/lib/grafana/dashboards"]
    assert len(all_paths) == len(set(all_paths)), (
        "two providers must not target the same effective dashboard directory"
    )
