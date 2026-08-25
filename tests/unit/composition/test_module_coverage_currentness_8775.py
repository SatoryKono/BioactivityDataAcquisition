"""Composition coverage regression vectors for #8775."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock
from uuid import UUID

import pytest

from bioetl.composition import _service_protocols, _services, registry_api
from bioetl.composition.factories.datasource import http_client
from bioetl.composition.factories.pipeline.control_plane_artifacts import (
    build_control_plane_artifacts,
)
from bioetl.composition.pipeline_runner_request import (
    _optional_cached_bronze,
    _optional_control_plane,
    _optional_filter_config,
    _optional_pipeline_config,
    _optional_str,
    _optional_str_tuple,
    _require_datetime,
    _require_observability,
    _require_run_id,
    _require_runtime,
    _require_settings,
)
from bioetl.composition.runtime_builders import _snapshot_mapping_support
from bioetl.composition.runtime_builders._snapshot_mapping_support import (
    normalize_snapshot,
    to_serializable_mapping,
)
from bioetl.domain.filtering import InputFilterConfig
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig


pytestmark = pytest.mark.unit


def test_service_protocol_module_is_runtime_importable() -> None:
    assert _service_protocols.HealthServerDependenciesProtocol is not None
    assert _service_protocols.BronzeCleanupServiceProtocol is not None


def test_bootstrap_export_must_be_callable(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(_services, "resolve_bootstrap_attr", lambda _name: object())

    with pytest.raises(TypeError, match="is not callable"):
        _services._invoke_bootstrap("broken")


def test_runner_request_coercion_accepts_declared_types() -> None:
    run_id = UUID("00000000-0000-0000-0000-000000000001")

    assert _require_run_id(run_id) == run_id
    assert _optional_str("value") == "value"
    assert _optional_control_plane(build_control_plane_artifacts()) is not None
    assert _optional_filter_config(InputFilterConfig()) is not None
    assert _optional_pipeline_config(PipelineYamlConfig.model_construct()) is not None
    assert _optional_cached_bronze(None) is None


@pytest.mark.parametrize(
    ("call", "pattern"),
    [
        (lambda: _require_run_id("not-a-uuid"), "run_id must be"),
        (lambda: _require_run_id(1), "run_id must be"),
        (lambda: _require_runtime(object()), "runtime must be"),
        (lambda: _require_datetime(object()), "started_at must be"),
        (lambda: _require_settings(object()), "settings must be"),
        (lambda: _require_observability(object()), "observability must be"),
        (lambda: _optional_str(1), "expected str"),
        (lambda: _optional_str_tuple((None,), size=2), "expected tuple"),
        (lambda: _optional_control_plane(object()), "control_plane must be"),
        (lambda: _optional_filter_config(object()), "filter_config must be"),
        (lambda: _optional_pipeline_config(object()), "config must be"),
        (lambda: _optional_cached_bronze(object()), "cached_bronze must be"),
    ],
)
def test_runner_request_coercion_rejects_invalid_types(
    call: object,
    pattern: str,
) -> None:
    with pytest.raises(TypeError, match=pattern):
        call()  # type: ignore[operator]


def test_snapshot_normalization_covers_temporal_and_path_scalars() -> None:
    assert normalize_snapshot(datetime(2026, 8, 14, tzinfo=UTC)).startswith("2026-")
    assert normalize_snapshot(timedelta(seconds=2)) == 2.0
    assert normalize_snapshot(Path("reports")) == "reports"


def test_http_config_uses_bounded_fallback_without_registry_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = MagicMock()
    registry.get_http_config.return_value = None
    monkeypatch.setattr(
        http_client, "_resolve_provider_registry", lambda _r=None: registry
    )

    def missing_source(_provider: str) -> object:
        raise ValueError("not configured")

    monkeypatch.setattr(http_client, "load_source_config", missing_source)

    resolved = http_client.HttpClientFactory._resolve_config("custom", None)

    assert (resolved.rate, resolved.capacity) == (5.0, 10)
    assert http_client.HttpClientFactory._api_key_setting_name("OTHER_KEY") is None


def test_pipeline_registration_delegate_preserves_explicit_scope(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    ensure = MagicMock()
    registry = MagicMock()
    monkeypatch.setattr(_services, "_ensure_registrations", ensure)
    monkeypatch.setattr(registry_api, "create_registry", lambda: registry)

    resolved = _services._ensure_pipeline_registrations()

    assert resolved is registry
    ensure.assert_called_once_with(registry=registry, scope="pipelines")


def test_snapshot_mapping_fails_closed_if_normalization_changes_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DumpHost:
        def model_dump(
            self, *, mode: str = "python", exclude_none: bool = False
        ) -> dict[str, object]:
            del mode, exclude_none
            return {"value": 1}

    monkeypatch.setattr(
        _snapshot_mapping_support,
        "normalize_snapshot",
        lambda _value: [],
    )

    with pytest.raises(TypeError, match="must return a mapping"):
        to_serializable_mapping(DumpHost())
