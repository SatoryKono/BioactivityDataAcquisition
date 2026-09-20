"""Stream B CMP: remaining adapter, snapshot, serializer, and factory branches."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest

from bioetl.composition.bootstrap.assembly.health_service import (
    _DATA_SOURCE_CREATOR_HEALTH_PROVIDERS,
)
from bioetl.composition.bootstrap.cli import storage as cli_storage
from bioetl.composition.bootstrap.runtime import (
    _composite_control_plane_payloads as payloads,
)
from bioetl.composition.bootstrap.runtime.composite_runtime_management_builder import (
    _resolve_expected_effective_config_hash,
)
from bioetl.composition.bootstrap.runtime.pipeline_context_builder import (
    RunOptions,
    _coerce_run_id,
    _resolve_pipeline_run_id,
)
from bioetl.composition.factories.datasource.pubchem import _create_executor_runner
from bioetl.composition.factories.dq.context_resolver import _create_dq_report_service
from bioetl.composition.factories.pipeline_support.registry_validation_helpers import (
    _validate_entity_contract_fields,
)
from bioetl.composition.providers import _registration_biblio_adapters as biblio
from bioetl.composition.runtime_builders import input_snapshot_resolution as snapshots
from bioetl.composition.runtime_builders import (
    _manifest_publication_context_support as publication,
)
from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import (
    bind_cached_bronze_context,
    _collect_manifest_bronze_dates,
    _extract_bronze_date,
)
from bioetl.composition.runtime_builders.config_access import (
    load_dq_config_for_pipeline,
)
from bioetl.composition.runtime_builders.run_manifest_data_roots import (
    _private_fallback_data_root_with_mode,
)
from bioetl.composition.services.effective_config_serializer import (
    EffectiveConfigSerializer,
)
from bioetl.domain.control_plane.effective_config_artifact import (
    ConfigResolutionPolicy,
    ConfigSourceRef,
    RuntimeOverrideSnapshot,
)
from bioetl.domain.types.dq_contracts import DQDisposition

pytestmark = pytest.mark.unit


def test_biblio_adapter_credential_and_guard_paths() -> None:
    class _Secret:
        def get_secret_value(self) -> str:
            return "secret"

    settings = SimpleNamespace(
        default_email="a@b.c",
        pubmed_api_key=_Secret(),
        openalex_api_key=_Secret(),
    )
    assert biblio._get_pubmed_api_key(settings) == "secret"
    assert biblio._get_openalex_api_key(settings) == "secret"
    with pytest.raises(ValueError, match="email"):
        biblio._build_pubmed_adapter_from_settings(
            adapter_cls=object,  # type: ignore[arg-type]
            http_client=object(),  # type: ignore[arg-type]
            logger=object(),  # type: ignore[arg-type]
            settings=None,
        )
    with pytest.raises(ValueError, match="http_client"):
        biblio._build_pubmed_adapter_from_settings(
            adapter_cls=object,  # type: ignore[arg-type]
            http_client=None,
            logger=object(),  # type: ignore[arg-type]
            settings=SimpleNamespace(default_email="a@b.c", pubmed_api_key=None),
        )
    with pytest.raises(ValueError, match="logger"):
        biblio._build_pubmed_adapter_from_settings(
            adapter_cls=object,  # type: ignore[arg-type]
            http_client=object(),  # type: ignore[arg-type]
            logger=None,
            settings=SimpleNamespace(default_email="a@b.c", pubmed_api_key=None),
        )
    with pytest.raises(ValueError, match="api_key or mailto"):
        biblio._build_openalex_adapter_from_settings(
            adapter_cls=object,  # type: ignore[arg-type]
            http_client=object(),  # type: ignore[arg-type]
            logger=object(),  # type: ignore[arg-type]
            settings=None,
        )
    with pytest.raises(ValueError, match="http_client"):
        biblio._build_openalex_adapter_from_settings(
            adapter_cls=object,  # type: ignore[arg-type]
            http_client=None,
            logger=object(),  # type: ignore[arg-type]
            settings=SimpleNamespace(default_email="a@b.c", openalex_api_key=None),
            mailto="a@b.c",
        )
    with pytest.raises(ValueError, match="logger"):
        biblio._build_openalex_adapter_from_settings(
            adapter_cls=object,  # type: ignore[arg-type]
            http_client=object(),  # type: ignore[arg-type]
            logger=None,
            settings=SimpleNamespace(default_email="a@b.c", openalex_api_key=None),
            mailto="a@b.c",
        )


def test_manifest_publication_identity_resolution(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert publication._resolve_provider_entity(
        pipeline_name="chembl", yaml_config=object()
    ) == ("chembl", "chembl")
    repro = SimpleNamespace(required_persistence_profile="degraded_observable")
    monkeypatch.setattr(
        publication,
        "resolve_manifest_reproducibility_context",
        lambda **_k: repro,
    )
    monkeypatch.setattr(
        publication,
        "resolve_contract_identity",
        lambda **_k: "cid",
    )
    ctx = SimpleNamespace(exact_replay=False)
    resolved = publication.ensure_manifest_publication_identity(
        ctx=ctx,  # type: ignore[arg-type]
        inputs=object(),  # type: ignore[arg-type]
        provider="chembl",
        entity="activity",
    )
    assert resolved[0] is repro
    kwargs = publication.build_manifest_publication_identity_kwargs(
        ctx,  # type: ignore[arg-type]
        object(),  # type: ignore[arg-type]
        "chembl",
        "activity",
    )
    assert kwargs["provider"] == "chembl"


def test_input_snapshot_resolution_branches(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    manifest = SimpleNamespace(source_refs=(SimpleNamespace(input_snapshots=(1, 2)),))
    assert snapshots.collect_manifest_input_snapshot_refs(manifest) == (1, 2)  # type: ignore[arg-type]
    orig_load = snapshots._load_manifest
    monkeypatch.setattr(
        snapshots, "resolve_cached_bronze_input_snapshot_refs", lambda **_k: ()
    )
    monkeypatch.setattr(
        snapshots,
        "_load_manifest",
        lambda **_k: SimpleNamespace(
            source_refs=(SimpleNamespace(input_snapshots=("parent",)),)
        ),
    )
    refs = snapshots.resolve_pipeline_input_snapshot_refs(
        ctx=SimpleNamespace(replay_of_manifest_id="m", replay_of_run_id=None),  # type: ignore[arg-type]
        cached_bronze=None,
        settings=object(),  # type: ignore[arg-type]
        provider="chembl",
        entity="activity",
    )
    assert refs == ("parent",)
    monkeypatch.setattr(snapshots, "_load_manifest", orig_load)

    class _Store:
        def __init__(self, **_k: object) -> None:
            return None

        def get(self, manifest_id: str) -> str | None:
            return "loaded" if manifest_id == "hit" else None

        def get_by_run_id(self, _run_id: object) -> object:
            raise ValueError("bad uuid path")

    monkeypatch.setattr(snapshots, "FileRunManifestStore", _Store)
    monkeypatch.setattr(snapshots, "control_plane_root", lambda *_a, **_k: tmp_path)
    assert (
        snapshots._load_manifest(
            settings=object(),  # type: ignore[arg-type]
            manifest_id="hit",
            run_id=None,
        )
        == "loaded"
    )
    assert (
        snapshots._load_manifest(
            settings=object(),  # type: ignore[arg-type]
            manifest_id="miss",
            run_id=None,
        )
        is None
    )
    assert (
        snapshots._load_manifest(
            settings=object(),  # type: ignore[arg-type]
            manifest_id="miss",
            run_id="not-a-uuid",
        )
        is None
    )
    assert (
        snapshots.resolve_manifest_input_snapshot_refs(
            settings=object(),  # type: ignore[arg-type]
            manifest_id="miss",
        )
        == ()
    )


def test_effective_config_serializer_optional_fields() -> None:
    serializer = EffectiveConfigSerializer()
    ref = ConfigSourceRef(
        source_type="file",
        source_path="x.yaml",
        source_hash="abc",
        raw_source_hash="raw",
        source_hash_strategy="canonical_yaml",
    )
    encoded = serializer._source_ref_to_dict(ref)
    assert encoded["source_hash"] == "abc"
    assert encoded["source_hash_strategy"] == "canonical_yaml"
    overrides = RuntimeOverrideSnapshot(
        cli_overrides={"a": 1},
        env_overrides={"b": 2},
        runtime_adjustments={"c": 3},
        override_hash="h",
    )
    mapped = serializer._runtime_overrides_to_dict(overrides)
    assert mapped["env_overrides"]["b"] == 2
    assert mapped["runtime_adjustments"]["c"] == 3
    assert serializer._normalize_value((DQDisposition.PASS,))
    policy = ConfigResolutionPolicy()
    assert serializer._normalize_section(policy)["merge_strategy"] == "hierarchical"
    assert serializer._normalize_section({"z": 1})["z"] == 1
    assert serializer._normalize_section("plain")["value"] == "plain"


def test_storage_export_and_composite_payloads(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        cli_storage, "get_settings", lambda: SimpleNamespace(data_dir=str(tmp_path))
    )
    monkeypatch.setattr(cli_storage, "create_noop_logger", lambda: MagicMock())
    monkeypatch.setattr(cli_storage, "DeltaReader", lambda **_k: object())
    monkeypatch.setattr(cli_storage, "ExportCatalogAdapter", lambda: object())
    monkeypatch.setattr(cli_storage, "ExportWriterAdapter", lambda: object())
    monkeypatch.setattr(cli_storage, "ExportService", lambda **_k: "export-svc")
    assert cli_storage.bootstrap_export_service() == "export-svc"

    assert payloads._resolve_provider_entity("chembl") == ("chembl", "chembl")
    runtime = SimpleNamespace(
        replay_of_manifest_id="m",
        replay_of_run_id=None,
        use_cached_bronze=False,
        cached_bronze_path=None,
        cached_bronze_date=None,
    )
    with pytest.raises(ValueError, match="Settings"):
        payloads._build_composite_input_snapshots(
            runtime=runtime,  # type: ignore[arg-type]
            settings=None,
            provider="chembl",
            entity="activity",
            pipeline_name="chembl_activity",
        )
    runtime.replay_of_manifest_id = None
    runtime.use_cached_bronze = True
    with pytest.raises(ValueError, match="Settings"):
        payloads._build_composite_input_snapshots(
            runtime=runtime,  # type: ignore[arg-type]
            settings=None,
            provider="chembl",
            entity="activity",
            pipeline_name="chembl_activity",
        )
    provider_root = tmp_path / "chembl" / "activity"
    provider_root.mkdir(parents=True)
    root = payloads._resolve_composite_bronze_root(
        runtime=SimpleNamespace(cached_bronze_path=str(tmp_path)),  # type: ignore[arg-type]
        settings=None,
        provider="chembl",
        entity="activity",
        pipeline_name="chembl_activity",
    )
    assert root == provider_root
    pipeline_root = tmp_path / "other" / "chembl_activity"
    pipeline_root.mkdir(parents=True)
    root = payloads._resolve_composite_bronze_root(
        runtime=SimpleNamespace(cached_bronze_path=str(tmp_path / "other")),  # type: ignore[arg-type]
        settings=None,
        provider="missing",
        entity="missing",
        pipeline_name="chembl_activity",
    )
    assert root == pipeline_root


def test_runtime_hash_and_pubchem_executor(monkeypatch: pytest.MonkeyPatch) -> None:
    class _BoomDict:
        def to_dict(self) -> dict[str, object]:
            raise TypeError("cannot serialize")

    with pytest.raises(ValueError, match="serialize"):
        _resolve_expected_effective_config_hash(
            config=_BoomDict(),  # type: ignore[arg-type]
            control_plane_bundle=None,
        )

    class _NotMapping:
        def to_dict(self) -> list[str]:
            return ["x"]

    with pytest.raises(ValueError, match="mapping"):
        _resolve_expected_effective_config_hash(
            config=_NotMapping(),  # type: ignore[arg-type]
            control_plane_bundle=None,
        )

    class _BadHash:
        def to_dict(self) -> dict[str, object]:
            return {"a": object()}

    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.compute_config_hash",
        lambda _payload: (_ for _ in ()).throw(TypeError("hash")),
    )
    with pytest.raises(ValueError, match="compute"):
        _resolve_expected_effective_config_hash(
            config=_BadHash(),  # type: ignore[arg-type]
            control_plane_bundle=None,
        )

    class _EmptyHash:
        def to_dict(self) -> dict[str, str]:
            return {"a": "b"}

    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.compute_config_hash",
        lambda _payload: "abc",
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime.composite_runtime_management_builder.normalize_control_plane_sha256",
        lambda _value: "",
    )
    with pytest.raises(ValueError, match="empty"):
        _resolve_expected_effective_config_hash(
            config=_EmptyHash(),  # type: ignore[arg-type]
            control_plane_bundle=None,
        )

    async def _run_executor() -> int:
        with ThreadPoolExecutor(max_workers=1) as pool:
            runner = _create_executor_runner(pool)
            return await runner(lambda: 7)

    import asyncio

    assert asyncio.run(_run_executor()) == 7

    class _Adapter:
        provider_name = "pubchem"

        def __init__(self, **_k: object) -> None:
            raise RuntimeError("adapter boom")

    from bioetl.composition.factories.datasource import pubchem as pubchem_mod

    monkeypatch.setattr(pubchem_mod, "PubChemAdapter", _Adapter)
    monkeypatch.setattr(pubchem_mod, "PUBCHEM_ASSEMBLY_ERRORS", (RuntimeError,))
    with pytest.raises(RuntimeError, match="adapter boom"):
        pubchem_mod.create_pubchem_adapter(logger=MagicMock())


def test_exact_replay_and_small_seams(monkeypatch: pytest.MonkeyPatch) -> None:
    class _Mutable:
        cached_bronze = "old"

    bound = bind_cached_bronze_context(_Mutable(), "new")  # type: ignore[arg-type]
    assert bound.cached_bronze == "new"

    manifest = SimpleNamespace(
        provider="chembl",
        entity="activity",
        source_refs=(
            SimpleNamespace(
                provider="chembl",
                entity="activity",
                input_snapshots=(SimpleNamespace(immutable_uri=None),),
            ),
        ),
    )
    with pytest.raises(RuntimeError, match="immutable_uri"):
        _collect_manifest_bronze_dates(manifest)  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="empty Bronze date"):
        _extract_bronze_date("bronze://   ")

    preferred = Path.home() / ".cache" / "bioetl-data"
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.run_manifest_data_roots._private_fallback_data_root",
        lambda: preferred,
    )
    path, mode = _private_fallback_data_root_with_mode()
    assert mode in {"private_cache", "tmp"}
    assert path == preferred or mode == "tmp"

    run_id = uuid4()
    assert _coerce_run_id(run_id) == run_id
    assert isinstance(
        _resolve_pipeline_run_id(
            options=RunOptions(),
            run_id="aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa",
            run_id_factory=None,
        ),
        UUID,
    )
    factory_id = _resolve_pipeline_run_id(
        options=RunOptions(),
        run_id=None,
        run_id_factory=lambda: run_id,
    )
    assert factory_id == run_id

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.config_access.resolve_configs_root",
        lambda _root: Path("configs"),
    )
    monkeypatch.setattr(
        "bioetl.composition.runtime_builders.config_access._load_dq_config_for_pipeline",
        lambda *_a, **_k: {"ok": True},
    )
    assert load_dq_config_for_pipeline("chembl_activity") == {"ok": True}

    monkeypatch.setattr(
        "bioetl.composition.factories.dq.context_resolver.DQReportService",
        lambda **_k: "dq",
    )
    assert (
        _create_dq_report_service(
            logger=MagicMock(),
            bronze_analyzer=object(),
            silver_analyzer=object(),
            gold_analyzer=object(),
            report_writer=object(),
            metrics=None,
        )
        == "dq"
    )
    assert (
        _validate_entity_contract_fields(
            "p.yaml", {"contracts": {"primary_key": ["id"]}}
        )
        == []
    )
    assert "uniprot_idmapping" in _DATA_SOURCE_CREATOR_HEALTH_PROVIDERS

    from bioetl.composition import _pipeline_execution as pe

    monkeypatch.setattr(pe, "build_pipeline_context", lambda *_a, **_k: object())
    monkeypatch.setattr(
        pe, "_create_pipeline_runner_from_context", lambda _ctx: "runner"
    )
    assert pe.create_pipeline_runner("chembl_activity", object()) == "runner"  # type: ignore[arg-type]

    from bioetl.composition.bootstrap.runtime._composite_plan_support import (
        bootstrap_runtime_basics_impl,
        build_runner_factories_impl,
    )

    sentinel = object()
    assert (
        bootstrap_runtime_basics_impl(
            config=object(),  # type: ignore[arg-type]
            run_id=None,
            bootstrap_runtime_basics_builder_fn=lambda **_k: sentinel,
            settings_provider=lambda: object(),  # type: ignore[arg-type]
            logger_bootstrapper=lambda *_a: MagicMock(),
            tracer_bootstrapper=lambda _s: MagicMock(),
            storage_bootstrapper=lambda **_k: object(),
            lock_factory=lambda: object(),  # type: ignore[arg-type]
            uuid_factory=uuid4,
        )
        is sentinel
    )
    assert (
        build_runner_factories_impl(
            config=object(),  # type: ignore[arg-type]
            runtime=object(),  # type: ignore[arg-type]
            logger=MagicMock(),
            build_runner_factories_builder_fn=lambda **_k: sentinel,
            runner_factory_builder_cls=object,
            filter_extraction_service_cls=object,
            pipeline_runner_builder=object(),
            resolve_bronze_opts_fn=lambda *_a, **_k: None,
        )
        is sentinel
    )

    from bioetl.composition.bootstrap.runtime._composite_control_plane_builder_support import (
        _composite_contract_identity_field_values,
        _composite_manifest_contract_identity_kwargs,
        _resolve_composite_contract_coordinates,
    )

    monkeypatch.setattr(
        "bioetl.composition.bootstrap.runtime._composite_control_plane_builder_support.build_contract_identity_field_values",
        lambda **_k: {"contract_ref": "c"},
    )
    assert (
        _composite_contract_identity_field_values(
            contract_ref="c",
            contract_version="1",
            contract_schema_hash=None,
            dq_policy_ref=None,
            rule_bundle_version=None,
            normalization_profile_ref=None,
            normalization_profile_version=None,
            normalization_profile_hash=None,
        )["contract_ref"]
        == "c"
    )
    artifacts = SimpleNamespace(
        contract_ref="c",
        contract_version="1",
        contract_schema_hash=None,
        dq_policy_ref=None,
        rule_bundle_version=None,
        normalization_profile_ref=None,
        normalization_profile_version=None,
        normalization_profile_hash=None,
    )
    assert (
        _composite_manifest_contract_identity_kwargs(artifacts)["contract_ref"] == "c"
    )  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="non-empty name"):
        _resolve_composite_contract_coordinates(SimpleNamespace(name=""))  # type: ignore[arg-type]
    with pytest.raises(RuntimeError, match="does not resolve"):
        _resolve_composite_contract_coordinates(SimpleNamespace(name="composite_"))  # type: ignore[arg-type]
    assert (
        _resolve_composite_contract_coordinates(
            SimpleNamespace(name="composite_activity")  # type: ignore[arg-type]
        )[1]
        == "activity"
    )

    from bioetl.composition.factories.pipeline import runner_assembly as assembly

    monkeypatch.setattr(assembly, "_build_preflight_service_impl", lambda _ctx: "pre")
    monkeypatch.setattr(assembly, "_build_observer_impl", lambda _ctx: "obs")
    monkeypatch.setattr(
        assembly, "_build_batch_executor_impl", lambda *_a, **_k: "batch"
    )
    assert assembly._build_preflight_service(object()) == "pre"  # type: ignore[arg-type]
    assert assembly._build_observer(object()) == "obs"  # type: ignore[arg-type]
    assert (
        assembly._build_batch_executor(
            object(),  # type: ignore[arg-type]
            checkpoint_manager=object(),  # type: ignore[arg-type]
            lock_runtime_service=object(),  # type: ignore[arg-type]
            observer=object(),  # type: ignore[arg-type]
        )
        == "batch"
    )

    from bioetl.composition.factories.services.pipeline_batch_executor_builder import (
        _resolve_effective_gold_table,
    )

    pipeline = SimpleNamespace(
        config=SimpleNamespace(
            effective_gold_table="",
            table=SimpleNamespace(gold_table="gold_t"),
            provider="chembl",
            entity_type="activity",
        )
    )
    assert _resolve_effective_gold_table(pipeline) == "gold_t"  # type: ignore[arg-type]

    from bioetl.composition.factories.services.factory import BaseServicesFactory

    monkeypatch.setattr(
        "bioetl.composition.factories.services.factory.create_metrics",
        lambda _settings: "metrics",
    )
    monkeypatch.setattr(
        "bioetl.composition.factories.services.factory.resolve_tracer",
        lambda tracer: tracer or "noop",
    )
    assert BaseServicesFactory._create_metrics(object()) == "metrics"  # type: ignore[arg-type]
    assert BaseServicesFactory._resolve_tracer(None) == "noop"

    from bioetl.composition.runtime_builders._runner_control_plane_policy import (
        validate_artifact_recorder_attachment,
    )

    monkeypatch.setattr(
        "bioetl.composition.runtime_builders._runner_control_plane_policy._validate_artifact_recorder_attachment",
        lambda **_k: None,
    )
    validate_artifact_recorder_attachment(
        required_profile="forensic_grade",
        candidate_count=1,
        attached_count=1,
        missing_attach_method_count=0,
        failed_count=0,
    )

    from bioetl.composition.providers.registration_bio import _get_uniprot_api_key

    class _UniSecret:
        def get_secret_value(self) -> str:
            return "u"

    assert _get_uniprot_api_key(SimpleNamespace(uniprot_api_key=_UniSecret())) == "u"
    assert _get_uniprot_api_key(None) is None
