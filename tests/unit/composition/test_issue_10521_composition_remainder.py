"""Stream B CMP: leftover factory, filter, and policy branches."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from bioetl.composition.bootstrap.runtime._composite_control_plane_payloads import (
    _resolve_composite_bronze_root,
)
from bioetl.composition.bootstrap.runtime.composite_filter_extraction_service import (
    CompositeFilterExtractor,
)
from bioetl.composition.factories.pipeline import runner_assembly as assembly
from bioetl.composition.factories.services import common_service_wiring as wiring
from bioetl.composition.factories.services.factory import BaseServicesFactory
from bioetl.composition.factories.services.pipeline_batch_executor_builder import (
    _emit_gold_lifecycle_state,
    _resolve_effective_gold_table,
)
from bioetl.composition.providers import registration_bio as registration_bio
from bioetl.composition.providers.provider_registry import ProviderRegistry
from bioetl.composition.runtime_builders import (
    _exact_replay_cached_bronze_context as exact_replay,
)
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    bind_cached_bronze_context,
)
from bioetl.composition.runtime_builders._runner_control_plane_policy import (
    resolve_control_plane_flags,
)
from bioetl.composition.runtime_builders._runner_control_plane_policy_support import (
    resolve_required_artifact_lineage_layers,
    validate_required_persistence_profile,
)
from bioetl.composition.runtime_builders.config_access import load_pipeline_config
from bioetl.domain.control_plane.run_ledger import INPUT_SNAPSHOT_PUBLISHED_EVENT

pytestmark = pytest.mark.unit


def test_common_service_wiring_factories(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        wiring,
        "_StorageFactoryImpl",
        SimpleNamespace(create=lambda *_a, **_k: "storage"),
    )
    assert (
        wiring.StorageFactory.create(
            object(),  # type: ignore[arg-type]
            object(),  # type: ignore[arg-type]
            MagicMock(),
            MagicMock(),
            MagicMock(),
        )
        == "storage"
    )
    monkeypatch.setattr(wiring, "create_metrics", lambda _settings: "metrics")
    monkeypatch.setattr(wiring, "create_checkpoint", lambda _ctx: "ckpt")
    monkeypatch.setattr(wiring, "create_quarantine", lambda _settings: "q")
    assert wiring._create_metrics_from_settings(object()) == "metrics"  # type: ignore[arg-type]
    assert wiring._create_checkpoint_for_storage(object()) == "ckpt"  # type: ignore[arg-type]
    assert wiring._create_quarantine_from_settings(object()) == "q"  # type: ignore[arg-type]
    mapped = wiring._coerce_dq_service_bundle({"bronze_analyzer": 1})
    assert mapped.bronze_analyzer == 1
    bundle = wiring.DQServiceBundle()
    assert wiring._coerce_dq_service_bundle(bundle) is bundle
    assert wiring._coerce_dq_service_bundle("nope").bronze_analyzer is None


def test_filter_extraction_empty_values_and_missing_join_keys() -> None:
    service = CompositeFilterExtractor(logger=None)

    class _Keys:
        columns = ["id"]

        def __len__(self) -> int:
            return 1

        def select(self, _key: str) -> _Keys:
            return self

        def drop_nulls(self) -> _Keys:
            return self

        def to_series(self) -> _Keys:
            return self

        def to_list(self) -> list[object]:
            return []

    enricher = SimpleNamespace(pipeline="p", join_keys=("id",))
    assert service.extract_enricher_filters(enricher, _Keys()) == (None, None, None)  # type: ignore[arg-type]

    missing = SimpleNamespace(columns=["other"])
    missing.__len__ = lambda self: 1  # type: ignore[method-assign]
    dep_empty = SimpleNamespace(
        is_multi_field_filter=False,
        join_keys=("id", "other"),
        filter_field=None,
    )
    assert service.resolve_dependency_filter_inputs(dep_empty, _Keys()) == (
        None,
        None,
        None,
    )
    dep_missing = SimpleNamespace(
        is_multi_field_filter=False,
        join_keys=("missing",),
        filter_field=None,
    )
    assert service.resolve_dependency_filter_inputs(dep_missing, _Keys()) == (
        None,
        None,
        None,
    )


def test_registration_bio_filter_and_wrappers(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        registration_bio, "_get_adapter_config", lambda *_a, **_k: object()
    )
    monkeypatch.setattr(
        registration_bio,
        "_validate_extraction_input_filter_overlap",
        lambda *_a, **_k: None,
    )
    monkeypatch.setattr(registration_bio, "ExtractionParams", lambda **_k: object())
    monkeypatch.setattr(
        registration_bio, "_wrap_with_filter", lambda *_a, **_k: "wrapped"
    )
    monkeypatch.setattr(
        registration_bio, "_create_pubchem_adapter", lambda **_k: "pubchem-adapter"
    )
    assert (
        registration_bio._create_pubchem_data_source(
            settings=SimpleNamespace(strict_error_handling=False),  # type: ignore[arg-type]
            pipeline_config=object(),  # type: ignore[arg-type]
            logger=MagicMock(),
        )
        == "wrapped"
    )
    support = SimpleNamespace(
        create_http_client=lambda *_a, **_k: object(),
        create_adapter=lambda *_a, **_k: "chembl-adapter",
    )
    monkeypatch.setattr(
        registration_bio, "resolve_provider_assembly_support", lambda *_a, **_k: support
    )
    pipeline_config = SimpleNamespace(extraction_params={}, entity_type="activity")
    assert (
        registration_bio._create_chembl_data_source(
            settings=object(),  # type: ignore[arg-type]
            pipeline_config=pipeline_config,  # type: ignore[arg-type]
            logger=MagicMock(),
            filter_config=object(),  # type: ignore[arg-type]
        )
        == "wrapped"
    )

    class _Secret:
        def get_secret_value(self) -> str:
            return "u"

    assert (
        registration_bio._get_uniprot_api_key(
            SimpleNamespace(uniprot_api_key=_Secret())
        )
        == "u"
    )


def test_exact_replay_setattr_and_parent_manifest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class _Host:
        __slots__ = ("_store",)

        def __init__(self) -> None:
            object.__setattr__(self, "_store", {"cached_bronze": "old"})

        def __setattr__(self, name: str, value: object) -> None:
            self._store[name] = value

        def __getattr__(self, name: str) -> object:
            try:
                return self._store[name]
            except KeyError as exc:
                raise AttributeError(name) from exc

    bound = bind_cached_bronze_context(_Host(), "new")  # type: ignore[arg-type]
    assert bound.cached_bronze == "new"

    store = SimpleNamespace(get=lambda _mid: None, get_by_run_id=lambda _rid: "by-run")
    monkeypatch.setattr(exact_replay, "FileRunManifestStore", lambda **_k: store)
    monkeypatch.setattr(exact_replay, "control_plane_root", lambda *_a, **_k: Path("x"))
    ctx = SimpleNamespace(replay_of_manifest_id=None, replay_of_run_id=str(uuid4()))
    assert (
        exact_replay._resolve_replay_parent_manifest(ctx=ctx, settings=object())  # type: ignore[arg-type]
        == "by-run"
    )

    class _Entry:
        event_type = INPUT_SNAPSHOT_PUBLISHED_EVENT
        details = {"immutable_uri": None}

    monkeypatch.setattr(
        exact_replay, "_validated_ledger_snapshot_uri", lambda **_k: None
    )
    dates = exact_replay._collect_ledger_bronze_dates(
        manifest=SimpleNamespace(  # type: ignore[arg-type]
            manifest_id="m",
            provider="p",
            entity="e",
            source_refs=(),
        ),
        ledger_entries=(_Entry(),),  # type: ignore[arg-type]
    )
    assert dates == ()


def test_policy_support_skip_gold_and_strict_errors() -> None:
    yaml_config = SimpleNamespace(
        sink={
            "bronze": SimpleNamespace(enabled=True, save_metadata=False),
            "silver": SimpleNamespace(enabled=True, save_metadata=True),
            "gold": SimpleNamespace(enabled=True, save_metadata=False),
        }
    )
    active, _missing = resolve_required_artifact_lineage_layers(
        yaml_config=yaml_config,
        skip_gold=True,
    )
    assert "gold" not in active
    with pytest.raises(RuntimeError, match="run manifests"):
        validate_required_persistence_profile(
            manifest_enabled=False,
            ledger_enabled=True,
            required_profile="forensic_grade",
            execution_label="test",
        )
    with pytest.raises(RuntimeError, match="exact-replay"):
        validate_required_persistence_profile(
            manifest_enabled=True,
            ledger_enabled=True,
            required_profile="forensic_grade",
            execution_label="test",
            exact_replay_execution_context_supported=False,
        )
    with pytest.raises(RuntimeError, match="composite forensic"):
        validate_required_persistence_profile(
            manifest_enabled=True,
            ledger_enabled=True,
            required_profile="forensic_grade",
            execution_label="test",
            composite_resume_rich_replay_supported=False,
        )


def test_batch_executor_gold_table_and_metrics() -> None:
    pipeline = SimpleNamespace(
        config=SimpleNamespace(
            effective_gold_table="explicit",
            table=SimpleNamespace(gold_table="ignored"),
            provider="chembl",
            entity_type="activity",
        )
    )
    assert _resolve_effective_gold_table(pipeline) == "explicit"  # type: ignore[arg-type]
    _emit_gold_lifecycle_state(
        metrics=object(),
        pipeline_name="p",
        table_name="t",
        state="start",
    )
    metrics = SimpleNamespace(increment_counter=lambda *_a, **_k: None)
    _emit_gold_lifecycle_state(
        metrics=metrics,
        pipeline_name="p",
        table_name="t",
        state="start",
    )


def test_payloads_factory_registry_and_config(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    root = _resolve_composite_bronze_root(
        runtime=SimpleNamespace(cached_bronze_path=str(tmp_path)),  # type: ignore[arg-type]
        settings=None,
        provider="missing",
        entity="missing",
        pipeline_name="also-missing",
    )
    assert root == tmp_path
    monkeypatch.setattr(
        assembly, "create_pipeline_runner_from_payload", lambda _p: "runner"
    )
    assert assembly._create_pipeline_runner(object()) == "runner"  # type: ignore[arg-type]
    monkeypatch.setattr(
        "bioetl.composition.factories.services.factory.assemble_pipeline_service",
        lambda **_k: "svc",
    )
    assert (
        BaseServicesFactory._build_pipeline_services(
            data_source=object(),  # type: ignore[arg-type]
            storage_ctx=SimpleNamespace(adapter=object()),  # type: ignore[arg-type]
            lock=object(),  # type: ignore[arg-type]
            checkpoint=object(),  # type: ignore[arg-type]
            quarantine=object(),  # type: ignore[arg-type]
            metrics_port=object(),  # type: ignore[arg-type]
            tracer=object(),  # type: ignore[arg-type]
            logger=MagicMock(),
            dq_monitor=None,
            metadata_coordinator=None,
            dq_services=SimpleNamespace(
                bronze_analyzer=None,
                silver_analyzer=None,
                gold_analyzer=None,
                report_writer=None,
                report_service=None,
            ),  # type: ignore[arg-type]
        )
        == "svc"
    )
    registry = ProviderRegistry()
    monkeypatch.setattr(registry, "_get_registered_config", lambda *_a, **_k: object())
    monkeypatch.setattr(registry._creator, "has_data_source_creator", lambda _cfg: True)
    assert registry.has_data_source_creator("chembl") is True
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.config_access._load_pipeline_config",
        lambda _name: "cfg",
    )
    assert load_pipeline_config("chembl_activity") == "cfg"

    settings = SimpleNamespace(
        env="prod",
        debug=False,
        pipeline=SimpleNamespace(
            control_plane=SimpleNamespace(
                run_manifest_enabled=True,
                run_ledger_enabled=True,
                required_persistence_profile="degraded_observable",
            )
        ),
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._runner_control_plane_policy.is_critical_reproducibility_runtime",
        lambda **_k: True,
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._runner_control_plane_policy._validate_manifest_persistence_requirements",
        lambda **_k: None,
    )
    enabled, _ledger = resolve_control_plane_flags(
        settings=settings,
        yaml_config=SimpleNamespace(),
        skip_gold=False,
        exact_replay=True,
        required_profile_override=None,
        critical_runtime=None,
    )
    assert enabled is True
