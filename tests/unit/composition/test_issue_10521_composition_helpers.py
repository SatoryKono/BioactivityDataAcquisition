"""Stream B CMP: remaining composition private helpers and error branches."""

from __future__ import annotations

import os
import stat
from datetime import datetime, UTC
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.application.services.ops.health_service import HealthResult
from bioetl.composition.bootstrap.assembly.health_service import (
    _DATA_SOURCE_CREATOR_HEALTH_PROVIDERS,
    _HealthCheckDataSourceFactory,
)
from bioetl.composition.factories.pipeline_support.registry_validation_helpers import (
    _display_path,
    _is_legacy_composite_entity_stub,
    _iter_entity_files,
    _load_yaml_mapping,
    _pipeline_name,
    _validate_entity_config_against_registry,
    _validate_entity_contract_fields,
    _validate_registry_entry,
)
from bioetl.composition.runtime_builders._context_field_binding import (
    _copy_object_context_without_constructor,
    bind_context_fields,
)
from bioetl.composition.runtime_builders._inputs_resolution_support import (
    apply_tracing_override,
)
from bioetl.composition.runtime_builders._ledger_metadata_candidates import (
    _collect_metadata_writer_candidates,
    _iter_unique_candidates,
    _metadata_from_layer_writer,
)
from bioetl.composition.runtime_builders._run_manifest_snapshot_resolution import (
    as_runtime_config_mapping,
    coerce_optional_text,
    resolve_mapping_text,
    resolve_name_component,
    resolve_replay_parentage_mapping_value,
)
from bioetl.composition.runtime_builders.run_manifest_data_roots import (
    _assert_private_runtime_dir,
    _private_fallback_data_root_with_mode,
)

pytestmark = pytest.mark.unit


def test_private_data_root_and_runtime_dir_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    class _BoomPath:
        def resolve(self) -> Path:
            raise OSError("resolve failed")

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.run_manifest_data_roots._private_fallback_data_root",
        lambda: _BoomPath(),
    )
    path, mode = _private_fallback_data_root_with_mode()
    assert mode == "tmp"
    assert path is not None

    file_path = tmp_path / "not-a-dir"
    file_path.write_text("x", encoding="utf-8")
    with pytest.raises(OSError, match="not a directory"):
        _assert_private_runtime_dir(file_path)

    class _FakeRuntimePath:
        def __init__(self, *, stat_value: object | BaseException) -> None:
            self._stat_value = stat_value

        def is_dir(self) -> bool:
            return True

        def stat(self) -> object:
            if isinstance(self._stat_value, BaseException):
                raise self._stat_value
            return self._stat_value

        def chmod(self, _mode: int) -> None:
            return None

        def __str__(self) -> str:
            return "fake-runtime"

    with pytest.raises(OSError, match="unable to stat"):
        _assert_private_runtime_dir(
            _FakeRuntimePath(stat_value=OSError("stat failed"))  # type: ignore[arg-type]
        )

    def _getuid_type_error() -> int:
        raise TypeError("no uid")

    monkeypatch.setattr(os, "getuid", _getuid_type_error, raising=False)
    _assert_private_runtime_dir(
        _FakeRuntimePath(stat_value=SimpleNamespace(st_uid=1, st_mode=0o40700))  # type: ignore[arg-type]
    )

    class _UidMismatch:
        st_uid = 99
        st_mode = 0o40700

    monkeypatch.setattr(os, "getuid", lambda: 7, raising=False)
    with pytest.raises(OSError, match="not owned by current user"):
        _assert_private_runtime_dir(
            _FakeRuntimePath(stat_value=_UidMismatch())  # type: ignore[arg-type]
        )

    class _WorldWritable:
        st_uid = 7
        st_mode = stat.S_IFDIR | 0o777

    monkeypatch.setattr(os, "name", "posix")
    with pytest.raises(OSError, match="not owner-private"):
        _assert_private_runtime_dir(
            _FakeRuntimePath(stat_value=_WorldWritable())  # type: ignore[arg-type]
        )


def test_ledger_metadata_and_snapshot_helpers() -> None:
    class _GetRaises:
        def get_metadata_writer(self) -> object:
            raise RuntimeError("nope")

    assert _metadata_from_layer_writer(_GetRaises()) is None

    class _GetOk:
        def get_metadata_writer(self) -> str:
            return "from-get"

    assert _metadata_from_layer_writer(_GetOk()) == "from-get"

    class _Attr:
        metadata_writer = object()

    writer = _Attr()
    assert _metadata_from_layer_writer(writer) is writer.metadata_writer

    class _Legacy:
        _metadata_writer = "legacy"

    assert _metadata_from_layer_writer(_Legacy()) == "legacy"

    shared = object()
    services = SimpleNamespace(
        metadata_writer=shared,
        storage=SimpleNamespace(
            bronze=SimpleNamespace(metadata_writer=shared),
            silver=None,
            gold=SimpleNamespace(_metadata_writer="gold"),
        ),
    )
    collected = _collect_metadata_writer_candidates(services)
    unique = _iter_unique_candidates(collected)
    assert shared in unique
    assert "gold" in unique

    assert as_runtime_config_mapping("x") == {}
    assert resolve_mapping_text("x", "k") is None
    assert coerce_optional_text("  ") is None
    assert resolve_name_component("  chembl  ", fallback="fb") == "chembl"
    assert resolve_name_component("  ", fallback="fb") == "fb"
    assert (
        resolve_replay_parentage_mapping_value(
            {"pipeline": {"control_plane": {"parent_run_id": "abc"}}},
            "parent_run_id",
        )
        == "abc"
    )
    assert resolve_replay_parentage_mapping_value({}, "missing") is None


def test_apply_tracing_override_copy_paths() -> None:
    class _Copyable:
        def __init__(self, **payload: object) -> None:
            self.__dict__.update(payload)

        def model_copy(self, *, update: dict[str, object]) -> _Copyable:
            merged = dict(self.__dict__)
            merged.update(update)
            return _Copyable(**merged)

    observability = _Copyable(tracing_enabled=False)
    settings = _Copyable(observability=observability, extra=1)
    updated = apply_tracing_override(settings=settings, enabled=True)  # type: ignore[arg-type]
    assert updated.observability.tracing_enabled is True  # type: ignore[union-attr]

    ns_obs = SimpleNamespace(tracing_enabled=False)
    ns_settings = SimpleNamespace(observability=ns_obs, extra=1)
    ns_updated = apply_tracing_override(settings=ns_settings, enabled=True)  # type: ignore[arg-type]
    assert ns_updated.observability.tracing_enabled is True  # type: ignore[union-attr]
    assert apply_tracing_override(settings=ns_settings, enabled=None) is ns_settings  # type: ignore[arg-type]
    bare = SimpleNamespace(observability=None)
    assert apply_tracing_override(settings=bare, enabled=True) is bare  # type: ignore[arg-type]


def test_registry_display_path_and_entry_errors(tmp_path: Path) -> None:
    other = Path("/unrelated/file.yaml")
    displayed = _display_path(other, repo_root=tmp_path)
    assert "unrelated" in displayed.replace("\\", "/")
    assert _pipeline_name("chembl", "activity") == "chembl_activity"
    assert _iter_entity_files(tmp_path / "missing") == []
    assert _is_legacy_composite_entity_stub(Path("configs/entities/composite/x.yaml"))
    assert _load_yaml_mapping.__name__ == "_load_yaml_mapping"

    entry = SimpleNamespace(
        pipeline_name="chembl_activity",
        provider="chembl",
        entity_type="activity",
        transformer_class=object(),
        gold_schema=None,
        pandera_silver_schema=None,
    )
    errors = _validate_registry_entry(
        entry,  # type: ignore[arg-type]
        resolved_configs_root=tmp_path,
        repo_root=tmp_path,
        seen_pipeline_names={"chembl_activity"},
        seen_provider_entities={("chembl", "activity")},
        registered_pipeline_names=set(),
        registered_provider_entities=set(),
    )
    assert any("duplicate pipeline_name" in item for item in errors)
    assert any("duplicate provider/entity" in item for item in errors)
    assert any("Gold contract" in item for item in errors)
    assert any("Pandera Silver" in item for item in errors)

    entity_dir = tmp_path / "entities" / "chembl"
    entity_dir.mkdir(parents=True)
    entity_path = entity_dir / "activity.yaml"
    entity_path.write_text(
        "\n".join(
            [
                "provider: other",
                "entity: molecule",
                "pipeline:",
                "  pipeline_name: other_name",
                "contracts:",
                "  primary_key:",
                "    business: []",
            ]
        ),
        encoding="utf-8",
    )
    entity_errors = _validate_entity_config_against_registry(
        entity_path,
        repo_root=tmp_path,
        registered_pipeline_names=set(),
        registered_provider_entities=set(),
    )
    assert entity_errors
    assert _validate_entity_contract_fields("p.yaml", {})
    assert _validate_entity_contract_fields("p.yaml", {"contracts": {}})
    assert _validate_entity_contract_fields(
        "p.yaml", {"contracts": {"primary_key": []}}
    )
    assert (
        _validate_entity_contract_fields(
            "p.yaml", {"contracts": {"primary_key": {"business": ["id"]}}}
        )
        == []
    )
    assert (
        _validate_entity_contract_fields(
            "p.yaml", {"contracts": {"primary_key": ["id"]}}
        )
        == []
    )


def test_health_factory_status_skip_and_create(monkeypatch: pytest.MonkeyPatch) -> None:
    import bioetl.composition.bootstrap.assembly.health_service as hs

    factory = _HealthCheckDataSourceFactory(
        logger=MagicMock(),
        metrics=MagicMock(),
        settings=MagicMock(),
    )
    factory.record_health_result(
        HealthResult(
            provider="chembl",
            status="unknown",
            checked_at=datetime(2026, 9, 16, 12, 0, tzinfo=UTC),
        )
    )
    factory.record_health_result(
        HealthResult(provider="chembl", status="healthy", checked_at=None)
    )

    created = object()

    class _FakeDataSourceFactory:
        @staticmethod
        def list_providers() -> list[str]:
            return ["chembl"]

        @staticmethod
        def create(*_a: object, **_k: object) -> object:
            return created

    monkeypatch.setattr(hs, "DataSourceFactory", _FakeDataSourceFactory)
    assert factory.list_providers() == ["chembl"]
    monkeypatch.setattr(
        hs,
        "resolve_provider_assembly_support",
        lambda _unused: SimpleNamespace(create_http_client=lambda *_a, **_k: object()),
    )
    assert factory.create("chembl") is created

    registry = SimpleNamespace(create_data_source=lambda *_a, **_k: created)
    monkeypatch.setattr(hs, "resolve_provider_registry", lambda *_a, **_k: registry)
    monkeypatch.setattr(hs, "load_pipeline_config", lambda *_a, **_k: object())
    provider = next(iter(_DATA_SOURCE_CREATOR_HEALTH_PROVIDERS))
    assert factory.create(provider) is created


def test_context_field_binding_constructor_fallbacks() -> None:
    class _NoKwargs:
        def __init__(self, value: int) -> None:
            self.value = value
            self.extra = "keep"

    source = _NoKwargs(1)
    copied = bind_context_fields(
        source,
        updates={"value": 2},
        unsupported_message="cannot bind",
    )
    assert copied.value == 2
    assert copied is not source

    with pytest.raises(TypeError, match="cannot bind"):
        _copy_object_context_without_constructor(
            [1],
            payload={"x": 1},
            unsupported_message="cannot bind",
        )

    class _SlotOnly:
        __slots__ = ("x",)

        def __init__(self, x: int) -> None:
            self.x = x

    with pytest.raises(TypeError, match="cannot bind"):
        _copy_object_context_without_constructor(
            _SlotOnly(1),
            payload={"x": 2, "y": 3},
            unsupported_message="cannot bind",
        )
