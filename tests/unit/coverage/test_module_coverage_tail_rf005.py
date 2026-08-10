# pyright: reportArgumentType=false
# pyright: reportPrivateUsage=false
"""Focused regression tests for the canonical module-coverage tail."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

import bioetl.composition.factories.datasource.data_source_factory as datasource_module
import bioetl.composition.providers as providers_module
import bioetl.domain.types as domain_types_module
import bioetl.infrastructure.checkpoint._local_checkpoint_integrity as integrity_module
from bioetl.composition.bootstrap.assembly.health_server import _ReadOnlyHealthMonitor
from bioetl.composition.factories.datasource.data_source_factory import (
    DataSourceFactory,
)
from bioetl.domain.control_plane.run_manifest import (
    RunCodeProvenance,
    validate_production_provenance,
)
from bioetl.domain.types import HealthStatus, RunID, RunType
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult
from bioetl.infrastructure.checkpoint._local_checkpoint_integrity import (
    CHECKPOINT_PAYLOAD_SHA256_KEY,
    _checksum_matches,
)
from bioetl.infrastructure.checkpoint._local_checkpoint_io import (
    atomic_write_text,
    extract_manifest_id,
    latest_history_checkpoint_path,
    read_json_file,
)
from bioetl.infrastructure.control_plane import FileRunManifestStore
from bioetl.infrastructure.control_plane._raw_run_manifest_inspection import (
    _raw_schema_errors,
)
from bioetl.infrastructure.locking.memory_lock import MemoryLock
from bioetl.infrastructure.system.memory_monitor import MemoryMonitor
from bioetl.domain.config import MemoryConfig
from bioetl.domain.ports import MemoryStats

pytestmark = pytest.mark.unit


def test_read_only_health_monitor_protocol_methods_are_deterministic() -> None:
    monitor = _ReadOnlyHealthMonitor(metrics=MagicMock())
    result = MagicMock(status=HealthStatus.HEALTHY)

    assert monitor.update_from_health_check_result(result, logger=object()) is (
        HealthStatus.HEALTHY
    )
    assert monitor.record_success("chembl") is HealthStatus.HEALTHY
    assert monitor.record_error("chembl") is HealthStatus.DEGRADED
    assert monitor.get_all_states() == {}


def test_datasource_factory_rejects_unknown_defaults_and_covers_early_returns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry = MagicMock()
    registry.list_providers.return_value = []
    registry.is_registered.return_value = False
    monkeypatch.setattr(
        datasource_module,
        "resolve_provider_registry",
        lambda *_args, **_kwargs: registry,
    )
    monkeypatch.setattr(
        datasource_module,
        "_get_default_provider_names",
        lambda: frozenset({"chembl"}),
    )

    with pytest.raises(KeyError, match="Unknown provider: absent"):
        datasource_module.get_data_source_creator("absent")

    monkeypatch.setattr(
        datasource_module.AdapterHelpersFactory,
        "supports_provider",
        staticmethod(lambda _provider: True),
    )
    DataSourceFactory._inject_adapter_helpers(
        provider="chembl",
        logger=None,
        adapter_kwargs={},
    )
    complete_kwargs = {
        "error_handler": object(),
        "adapter_metrics": object(),
        "request_collector": object(),
        "fallback_fetch_service": object(),
    }
    DataSourceFactory._inject_adapter_helpers(
        provider="chembl",
        logger=MagicMock(),
        adapter_kwargs=complete_kwargs,
    )

    registry.list_providers.return_value = ["chembl"]
    monkeypatch.setattr(
        datasource_module, "_resolve_provider_registry", lambda: registry
    )
    assert DataSourceFactory.list_providers() == ["chembl"]


def test_lazy_package_directories_and_unknown_provider_export() -> None:
    with pytest.raises(AttributeError, match="has no attribute 'absent'"):
        providers_module.__getattr__("absent")

    assert providers_module.__dir__() == sorted(providers_module.__dir__())
    assert domain_types_module.__dir__() == sorted(domain_types_module.__dir__())


def test_production_provenance_reports_and_rejects_missing_fields() -> None:
    provenance = RunCodeProvenance()

    assert provenance.missing_production_fields()
    with pytest.raises(ValueError, match="code_provenance is incomplete"):
        validate_production_provenance(provenance)


def test_dq_result_normalizes_rule_outcome_lists() -> None:
    result = DQResult(
        error_rate=0.0,
        status=DQEvaluationStatus.PASSED,
        rule_outcomes=[],  # type: ignore[arg-type]
    )

    assert result.rule_outcomes == ()


def test_checkpoint_checksum_rejects_incomplete_invalid_and_unhashable_envelopes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    digest = "0" * 64
    assert not _checksum_matches({CHECKPOINT_PAYLOAD_SHA256_KEY: digest})

    invalid_types = {
        CHECKPOINT_PAYLOAD_SHA256_KEY: digest,
        "pipeline": "pipeline",
        "run_id": "run-id",
        "metadata": [],
        "version": "2.0",
    }
    assert not _checksum_matches(invalid_types)

    valid_shape = {**invalid_types, "metadata": {}}

    def _raise_type_error(_envelope: object) -> str:
        raise TypeError("not serializable")

    monkeypatch.setattr(
        integrity_module,
        "compute_checkpoint_payload_sha256",
        _raise_type_error,
    )
    assert not _checksum_matches(valid_shape)


def test_checkpoint_io_handles_nested_ids_invalid_history_and_atomic_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert extract_manifest_id({"run_context": {"manifest_id": " nested "}}) == (
        "nested"
    )

    invalid_json = tmp_path / "invalid.json"
    invalid_json.write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a dictionary"):
        read_json_file(invalid_json)

    history_root = tmp_path / ".history" / "by_pipeline" / "pipeline"
    history_root.mkdir(parents=True)
    (history_root / "not-a-directory").write_text("ignored", encoding="utf-8")
    assert latest_history_checkpoint_path(tmp_path, "pipeline") is None

    destination = tmp_path / "checkpoint.json"

    def _raise_replace(_self: Path, _target: Path) -> Path:
        raise OSError("replace failed")

    monkeypatch.setattr(Path, "replace", _raise_replace)
    with pytest.raises(OSError, match="replace failed"):
        atomic_write_text(destination, "payload")
    assert not tuple(tmp_path.glob(".checkpoint_*.tmp"))


def test_raw_manifest_inspection_classifies_io_shape_and_field_errors(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileRunManifestStore(tmp_path)
    path = tmp_path / "manifest-io.json"
    path.write_text("{}", encoding="utf-8")

    original_read_text = Path.read_text

    def _raise_for_manifest(candidate: Path, *args: object, **kwargs: object) -> str:
        if candidate == path:
            raise OSError("read failed")
        return original_read_text(candidate, *args, **kwargs)

    monkeypatch.setattr(Path, "read_text", _raise_for_manifest)
    inspection = store.inspect_raw_manifest("manifest-io")
    assert inspection.schema_errors == ("manifest_read_error",)

    monkeypatch.setattr(Path, "read_text", original_read_text)
    path.write_text("[]", encoding="utf-8")
    inspection = store.inspect_raw_manifest("manifest-io")
    assert inspection.schema_errors == ("manifest_payload_not_object",)

    errors = _raw_schema_errors(
        {
            "manifest_id": "other-id",
            "execution_fingerprint": " ",
            "schema_version": "invalid",
            "created_at": "invalid",
            "run_id": 3,
            "run_type": "invalid",
            "pipeline_name": "pipeline",
            "provider": "provider",
            "entity": "entity",
            "runtime_config": [],
            "planned_artifacts": {},
            "workflow_name": 4,
        },
        expected_manifest_id="manifest-io",
    )
    assert "manifest_launch_context_missing" in errors
    assert "manifest_source_refs_missing" in errors
    assert "manifest_runtime_config_not_object" in errors
    assert "manifest_planned_artifacts_not_array" in errors
    assert "manifest_workflow_name_not_string" in errors
    assert "manifest_run_type_invalid" in errors
    assert "manifest_schema_version_invalid" in errors


def test_file_manifest_store_reports_missing_materialization_and_invalid_payload(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    store = FileRunManifestStore(tmp_path)
    assert store.list_all() == ()
    manifest = SimpleNamespace(
        manifest_id="manifest-tail",
        run_id=RunID("run-tail"),
        pipeline_name="pipeline",
        run_type=RunType.INCREMENTAL,
    )

    with pytest.raises(RuntimeError, match="manifest file is not materialized"):
        store.assert_saved(manifest)  # type: ignore[arg-type]

    (tmp_path / "manifest-tail.json").write_text("{}", encoding="utf-8")
    run_index = tmp_path / "_by_run_id" / "run-tail.txt"
    run_index.parent.mkdir(parents=True)
    run_index.write_text("manifest-tail", encoding="utf-8")
    missing_scope = tmp_path / "missing-scope.txt"
    monkeypatch.setattr(
        FileRunManifestStore,
        "_latest_scope_index_path",
        lambda *_args, **_kwargs: missing_scope,
    )
    with pytest.raises(RuntimeError, match="latest-scope index is not materialized"):
        store.assert_saved(manifest)  # type: ignore[arg-type]

    missing_scope.write_text("manifest-tail", encoding="utf-8")
    with pytest.raises(RuntimeError, match="latest-scope catalog is not materialized"):
        store.assert_saved(manifest)  # type: ignore[arg-type]

    (tmp_path / "invalid.json").write_text("[]", encoding="utf-8")
    with pytest.raises(ValueError, match="must be a JSON object"):
        store._load_manifest("invalid")


@pytest.mark.asyncio
async def test_memory_lock_reports_contention_timeout_and_owner_mismatches() -> None:
    lock = MemoryLock()
    owner = RunID("owner")
    other = RunID("other")

    assert await lock.acquire("key", owner) is not None
    assert await lock._try_acquire("key", other) is None
    assert await lock.acquire("key", other, wait=True, wait_timeout=0) is None
    assert await lock.release("missing", owner) is False
    assert await lock.heartbeat("missing", owner) is False
    assert await lock.heartbeat("key", other) is False
    await lock.aclose()


def test_memory_monitor_accessors_and_psutil_dispatch(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monitor = MemoryMonitor(config=MemoryConfig())
    expected = MemoryStats(
        used_mb=1.0,
        available_mb=2.0,
        total_mb=3.0,
        percent_used=1 / 3,
        process_mb=0.5,
    )
    monkeypatch.setattr(monitor, "_psutil_available", True)
    monkeypatch.setattr(monitor, "_get_stats_psutil", lambda: expected)

    assert monitor.get_monitor_mode() == "unknown"
    assert monitor.get_last_pressure_state() is None
    assert monitor.get_memory_stats() is expected
