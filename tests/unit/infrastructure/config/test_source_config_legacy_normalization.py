from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import pytest

from bioetl.infrastructure.config.source_config_loader import (
    load_source_config_uncached,
)
from bioetl.infrastructure.config.source_normalizers.source import (
    normalize_source_config,
)
from bioetl.infrastructure.schemas.source_config import SourceYamlConfig

SNAPSHOT_FILE = Path("tests/snapshots/source_config_legacy_normalization.json")


def _dump_source_config(payload: dict[str, Any]) -> dict[str, Any]:
    normalized = normalize_source_config(payload)
    config = SourceYamlConfig.model_validate(normalized)
    return config.model_dump(mode="json", exclude_none=True)


def _load_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_FILE.exists():
        return {}
    with open(SNAPSHOT_FILE, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _save_snapshot(payload: dict[str, Any]) -> None:
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SNAPSHOT_FILE, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


_CASE_CHEMBL_LEGACY: dict[str, Any] = {
    "source": {
        "type": "api",
        "load_strategy": "full",
        "provider_config": {
            "provider": "chembl",
            "base_url": "https://example.chembl/api",
            "auth_type": "public",
            "api_version": "v1",
            "client": {"timeout_sec": 60.0, "max_retries": 3},
            "pagination": {"id_batch_size": 25},
        },
        "rate_limit": {
            "requests_per_second": 3.0,
            "burst": 10,
            "with_api_key": {"requests_per_second": 6.0, "burst": 20},
        },
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
        "health_check": {"endpoint": "/health", "timeout": 5},
    }
}

_CASE_CHEMBL_NEW: dict[str, Any] = {
    "source": {
        "type": "api",
        "load_strategy": "full",
        "provider_config": {
            "provider": "chembl",
            "base_url": "https://example.chembl/api",
            "auth_type": "public",
            "api_version": "v1",
            "client": {"timeout": 60.0, "max_retries": 3},
            "pagination": {"id_batch_size": 25},
        },
        "rate_limit": {
            "requests_per_second": 3.0,
            "burst": 10,
            "authenticated": {"requests_per_second": 6.0, "burst": 20},
        },
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
        "health_check": {"endpoint": "/health", "timeout_sec": 5},
    }
}

_CASE_CHEMBL_PAGINATION_LEGACY: dict[str, Any] = {
    "source": {
        "type": "api",
        "load_strategy": "full",
        "provider_config": {
            "provider": "chembl",
            "base_url": "https://example.chembl/api",
            "auth_type": "public",
            "api_version": "v1",
            "client": {"timeout_sec": 60.0, "max_retries": 3},
            "pagination": {
                "page_size": 250,
                "max_url_length": 2200,
            },
        },
        "rate_limit": {
            "requests_per_second": 3.0,
            "burst": 10,
            "with_api_key": {"requests_per_second": 6.0, "burst": 20},
        },
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
        "health_check": {"endpoint": "/health", "timeout": 5},
    }
}

_CASE_CHEMBL_PAGINATION_NEW: dict[str, Any] = {
    "source": {
        "type": "api",
        "load_strategy": "full",
        "provider_config": {
            "provider": "chembl",
            "base_url": "https://example.chembl/api",
            "auth_type": "public",
            "api_version": "v1",
            "client": {"timeout": 60.0, "max_retries": 3},
            "pagination": {
                "page_size": 250,
                "max_url_length": 2200,
            },
        },
        "rate_limit": {
            "requests_per_second": 3.0,
            "burst": 10,
            "authenticated": {"requests_per_second": 6.0, "burst": 20},
        },
        "circuit_breaker": {"failure_threshold": 5, "recovery_timeout": 300},
        "health_check": {"endpoint": "/health", "timeout_sec": 5},
    }
}

_GOLDEN_CASES: dict[str, tuple[dict[str, Any], dict[str, Any]]] = {
    "chembl_canonical_and_shorthand_batch": (_CASE_CHEMBL_LEGACY, _CASE_CHEMBL_NEW),
    "chembl_canonical_and_shorthand_pagination": (
        _CASE_CHEMBL_PAGINATION_LEGACY,
        _CASE_CHEMBL_PAGINATION_NEW,
    ),
}


@pytest.mark.parametrize("canonical_payload,shorthand_payload", _GOLDEN_CASES.values())
def test_canonical_and_shorthand_payloads_are_equivalent(
    canonical_payload: dict[str, Any], shorthand_payload: dict[str, Any]
) -> None:
    canonical_dump = _dump_source_config(canonical_payload)
    shorthand_dump = _dump_source_config(shorthand_payload)
    assert canonical_dump == shorthand_dump


@pytest.mark.parametrize(
    "payload",
    [
        {
            "source": {
                "type": "api",
                "load_strategy": "full",
                "api": {
                    "base_url": "https://example.chembl/api",
                    "auth_type": "public",
                    "api_version": "v1",
                },
                "client": {"timeout": 60.0, "max_retries": 3},
                "batch": {"batch_size": 25},
                "provider_config": {"provider": "chembl"},
            }
        },
        {
            "source": {
                "type": "api",
                "load_strategy": "full",
                "api": {
                    "base_url": "https://example.chembl/api",
                    "auth_type": "public",
                    "api_version": "v1",
                },
                "client": {"timeout": 60.0, "max_retries": 3},
                "batch": {"page_size": 250, "max_url_length": 2200},
                "provider_config": {"provider": "chembl"},
            }
        },
    ],
)
def test_retired_source_transport_aliases_are_rejected(
    payload: dict[str, Any],
) -> None:
    with pytest.raises(ValueError, match="Retired source transport aliases"):
        _dump_source_config(payload)


def test_source_legacy_normalization_golden_snapshot() -> None:
    current = {
        name: _dump_source_config(payloads[0])
        for name, payloads in _GOLDEN_CASES.items()
    }
    update_snapshots = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
    if update_snapshots:
        _save_snapshot(current)
        return

    snapshot = _load_snapshot()
    if not snapshot:
        pytest.fail(
            "Missing source normalization snapshot. "
            "Run with UPDATE_SNAPSHOTS=1 to create baseline."
        )
    assert current == snapshot


@pytest.mark.parametrize(
    ("payload", "expected_fragment"),
    [
        (
            {
                "source": {
                    "provider_config": {
                        "provider": "chembl",
                        "batch_size": 25,
                    }
                }
            },
            "batch_size",
        ),
        (
            {
                "source": {
                    "provider_config": {
                        "provider": "chembl",
                        "page_size": 250,
                    }
                }
            },
            "page_size",
        ),
        (
            {
                "source": {
                    "provider_config": {
                        "provider": "chembl",
                        "cursor_pagination": True,
                    }
                }
            },
            "cursor_pagination",
        ),
    ],
)
def test_retired_provider_pagination_aliases_are_rejected(
    payload: dict[str, Any], expected_fragment: str
) -> None:
    with pytest.raises(
        ValueError, match="Retired source provider pagination aliases"
    ) as exc:
        _dump_source_config(payload)

    assert expected_fragment in str(exc.value)


def test_load_source_config_uncached_calls_pipeline_in_order(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[str] = []

    def fake_read(
        provider: str,
        *,
        configs_root: Path | None = None,
    ) -> dict[str, Any]:
        assert provider == "chembl"
        assert configs_root is None or configs_root.name == "configs"
        events.append("read")
        return {"raw": True}

    def fake_normalize(payload: dict[str, Any]) -> dict[str, Any]:
        assert payload == {"raw": True}
        events.append("normalize")
        return {"normalized": True}

    validated = SourceYamlConfig.model_validate(
        {"source": {"provider_config": {"provider": "chembl"}}}
    )

    def fake_validate(payload: dict[str, Any]) -> SourceYamlConfig:
        assert payload == {"normalized": True}
        events.append("validate")
        return validated

    def fake_map(payload: SourceYamlConfig) -> SourceYamlConfig:
        assert payload is validated
        events.append("map")
        return payload

    import bioetl.infrastructure.config.source_config_loader as module

    monkeypatch.setattr(module, "read_source_config_payload", fake_read)
    monkeypatch.setattr(module, "normalize_source_config_payload", fake_normalize)
    monkeypatch.setattr(module, "validate_source_config_payload", fake_validate)
    monkeypatch.setattr(module, "map_source_config", fake_map)

    loaded = load_source_config_uncached("chembl")
    assert loaded is validated
    assert events == ["read", "normalize", "validate", "map"]
