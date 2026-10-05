"""ADR-062: Re-execute the assay merge from sealed inputs with live reads disabled."""

from bioetl.composition.bootstrap.runtime.assay_replay_capture import (
    prepare_assay_replay,
)

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pyarrow as pa
from bioetl.application.services.run_reports.artifact_digest import (
    canonical_report_sha256,
)
import json
import pytest

from bioetl.application.composite.merger_orchestration import (
    build_merge_execution_request,
)
from bioetl.application.composite.runtime_wiring_api import (
    JOIN_KEY_NORMALIZATION_POLICIES,
)
from bioetl.composition.bootstrap.runtime.composite_merge_service_builder import (
    build_composite_merge_service,
)
from bioetl.composition.factories.services.composite_support_services_factory import (
    CompositeSupportServicesFactory,
)
from bioetl.domain.composite.result import EnrichmentResult
from bioetl.infrastructure.config.composite_config_api import (
    load_composite_config,
    resolve_composite_gold_schema,
)
from bioetl.infrastructure.storage.composite_replay_inputs import (
    CompositeInputCapture,
    CompositeReplayInputReader,
)
from tests.helpers.clock import FixedClock

pytestmark = [pytest.mark.integration, pytest.mark.asyncio]


@pytest.mark.parametrize("family", ["activity", "molecule", "publication", "target"])
async def test_other_composite_families_replay_physical_outputs(
    tmp_path, family, monkeypatch
):
    """Exercise each real family config and production writer without network I/O."""
    from uuid import UUID
    import httpx
    from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
    from bioetl.composition.bootstrap.runtime.composite_support_helpers import (
        _load_field_group_registry,
    )
    from bioetl.composition.bootstrap.runtime.assay_replay import replay_assay
    from bioetl.domain.composite.result import (
        DependencyResult,
        DependencyStatus,
        EnrichmentStatus,
    )
    from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing
    from bioetl.domain.types import RunID, RunType
    from bioetl.domain.value_objects.run_context import RunContext
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.infrastructure.storage.composite_replay_bundle import digest_bytes

    config = load_composite_config(family)
    monkeypatch.setattr(
        httpx.AsyncClient,
        "request",
        AsyncMock(side_effect=AssertionError("HTTP during replay")),
    )
    timestamp = datetime(2026, 10, 3, tzinfo=UTC)
    run_id = "22222222-2222-4222-8222-222222222222"
    logger = NoOpLogger()
    registry = _load_field_group_registry(config.name, logger)
    settings = Settings.model_validate(
        {"data_dir": tmp_path / "live", "report_root": tmp_path / "reports"}
    )
    storage = bootstrap_storage_adapter(
        run_context=RunContext(
            run_id=RunID(UUID(run_id)),
            run_type=RunType.REBUILD,
            started_at=timestamp,
            pipeline_name=config.name,
            provider="composite",
            entity=family,
        ),
        logger=logger,
        metrics=NoOpMetrics(),
        tracing=NoOpTracing(),
        settings=settings,
    )
    record = {
        "entity_id": "1" * 64,
        "content_hash": "a" * 64,
        "activity_id": "1",
        "assay_id": "CHEMBL1",
        "molecule_id": "CHEMBL25",
        "publication_id": "CHEMBL1",
        "target_id": "CHEMBL1",
        "pref_name": "Example",
        "title": "Example publication",
        "doi": "10.1234/example",
        "publication_year": 2024,
        "target_type": "SINGLE PROTEIN",
        "organism": "Homo sapiens",
        "tax_id": 9606,
        "inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N",
        "canonical_smiles": "CC(=O)O",
    }
    tables = {config.seed.silver_table: pa.Table.from_pylist([record])}
    dependency_results = {}
    # Activity's dual-key dependency must be part of the sealed replay inputs.
    dependencies = config.dependencies if family == "activity" else ()
    for dependency in dependencies:
        tables[dependency.silver_table or f"silver/{dependency.pipeline}"] = (
            pa.Table.from_pylist([record])
        )
        dependency_results[dependency.pipeline] = DependencyResult.success(
            dependency.pipeline, 1, 1
        )
    if family == "target":
        dependencies = config.dependencies
        dependency_results = {
            item.pipeline: DependencyResult(item.pipeline, DependencyStatus.FAILED)
            for item in dependencies
        }
    live = AsyncMock(read_table=AsyncMock(side_effect=lambda name: tables[name]))
    reader, hook = prepare_assay_replay(
        config=config,
        reader=live,
        storage=storage,
        settings=settings,
        logger=logger,
        field_group_registry=registry,
    )
    merger = build_composite_merge_service(
        config=config,
        storage=storage,
        resolve_gold_schema=resolve_composite_gold_schema,
        delta_reader=reader,
        field_group_registry=registry,
        cross_validator=None,
        logger=logger,
        system_columns_to_drop=CompositeSupportServicesFactory._SYSTEM_COLUMNS_TO_DROP,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
        execution_hook=hook,
        clock=FixedClock(timestamp),
    )
    request = build_merge_execution_request(
        seed_table=config.seed.silver_table,
        seed_pipeline=config.seed.pipeline,
        enrichers=config.enrichers,
        enrichment_results={
            item.pipeline: EnrichmentResult(item.pipeline, EnrichmentStatus.NOT_RUN)
            for item in config.enrichers
        },
        dependencies=dependencies,
        dependency_results=dependency_results,
        run_id=run_id,
        metadata_timestamp=timestamp,
    )
    try:
        result = await merger.execute_request(request)
        assert result.records_merged == 1
    finally:
        await storage.aclose()
    root = settings.report_root / "pipeline" / config.name / run_id / "replay"
    digest = digest_bytes((root / "parent.json").read_bytes())
    tables.clear()
    live.read_table.side_effect = AssertionError("Live input during replay")
    receipt = await replay_assay(root, digest, tmp_path / "offline")
    assert receipt["silver_equal"] is True and receipt["gold_equal"] is True
    assert receipt["records"] == 1


async def test_assay_merge_replays_nullable_foreign_keys_without_live_reads(tmp_path):
    config = load_composite_config("assay")
    tables = {
        "silver/chembl/assay": pa.table(
            {
                "entity_id": ["1", "2", "3"],
                "assay_id": ["A1", "A2", "A3"],
                "cell_id": ["C1", None, None],
                "tissue_id": [None, "T1", None],
                "assay_type": ["B", "F", "B"],
            }
        ),
        "silver/chembl/cell_line": pa.table({"cell_id": ["C1"], "cell_name": ["Cell"]}),
        "silver/chembl/tissue": pa.table(
            {"tissue_id": ["T1"], "pref_name": ["Tissue"]}
        ),
    }
    live = AsyncMock(read_table=AsyncMock(side_effect=lambda name: tables[name]))
    capture = CompositeInputCapture(tmp_path / "inputs", live)
    timestamp = datetime(2026, 10, 3, tzinfo=UTC)
    request = build_merge_execution_request(
        seed_table=config.seed.silver_table,
        seed_pipeline=config.seed.pipeline,
        enrichers=config.enrichers,
        enrichment_results={
            enricher.pipeline: EnrichmentResult.success(enricher.pipeline, 1, 1)
            for enricher in config.enrichers
        },
        run_id="11111111-1111-4111-8111-111111111111",
        metadata_timestamp=timestamp,
    )

    def service(reader, storage):
        return build_composite_merge_service(
            config=config,
            storage=storage,
            resolve_gold_schema=resolve_composite_gold_schema,
            delta_reader=reader,
            field_group_registry=None,
            cross_validator=None,
            logger=MagicMock(),
            system_columns_to_drop=CompositeSupportServicesFactory._SYSTEM_COLUMNS_TO_DROP,
            normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
            clock=FixedClock(timestamp),
        )

    original_output = AsyncMock()
    original = await service(capture, original_output).execute_request(request)
    assert original.records_merged == 3
    digest = capture.seal(required_tables=frozenset(tables))
    tables.clear()
    live.read_table.side_effect = AssertionError("Live access during offline replay")
    replay_reader = CompositeReplayInputReader(
        tmp_path / "inputs", envelope_sha256=digest
    )
    replay_output = AsyncMock()
    replay = await service(replay_reader, replay_output).execute_request(request)
    assert replay.records_merged == 3
    for layer in ("silver", "gold"):
        original_write = getattr(original_output, f"write_{layer}_merged")
        replay_write = getattr(replay_output, f"write_{layer}_merged")
        original_write.assert_awaited_once()
        replay_write.assert_awaited_once()
        assert replay_write.call_args == original_write.call_args
        records = replay_write.call_args.args[1]
        assert len(records) == 3
        assert {record["chembl.assay.assay_id"] for record in records} == {
            "A1",
            "A2",
            "A3",
        }
    assert live.read_table.await_count == 3


async def test_assay_replay_compares_physical_production_outputs(tmp_path, monkeypatch):
    import asyncio
    import httpx
    from click.testing import CliRunner
    from bioetl.interfaces.cli.commands.replay_assay import replay_assay_command
    from uuid import UUID
    from bioetl.composition.bootstrap.assembly.storage import bootstrap_storage_adapter
    from bioetl.composition.bootstrap.runtime.assay_replay import (
        replay_assay,
    )
    from bioetl.infrastructure.storage.composite_replay_evidence import (
        replay_artifacts,
        project_assay_replay,
    )
    from bioetl.domain.ports.noop import NoOpMetrics, NoOpTracing
    from bioetl.domain.types import RunID, RunType
    from bioetl.domain.value_objects.run_context import RunContext
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger
    from bioetl.infrastructure.storage.composite_replay_bundle import digest_bytes

    timestamp = datetime(2026, 10, 3, tzinfo=UTC)
    run_id = "11111111-1111-4111-8111-111111111111"
    config = load_composite_config("assay")
    settings = Settings.model_validate(
        {"data_dir": tmp_path / "live", "report_root": tmp_path / "reports"}
    )
    logger = NoOpLogger()
    storage = bootstrap_storage_adapter(
        run_context=RunContext(
            run_id=RunID(UUID(run_id)),
            run_type=RunType.REBUILD,
            started_at=timestamp,
            pipeline_name=config.name,
            provider="composite",
            entity="assay",
        ),
        logger=logger,
        metrics=NoOpMetrics(),
        tracing=NoOpTracing(),
        settings=settings,
    )
    tables = {
        config.seed.silver_table: pa.table(
            {
                "entity_id": ["1" * 64, "2" * 64, "3" * 64],
                "content_hash": ["a" * 64, "b" * 64, "c" * 64],
                "assay_id": ["CHEMBL1", "CHEMBL2", "CHEMBL3"],
                "cell_id": ["CHEMBL10", None, None],
                "tissue_id": [None, "CHEMBL20", None],
                "assay_type": ["B", "F", "B"],
            }
        ),
        "silver/chembl/cell_line": pa.table(
            {"cell_id": ["CHEMBL10"], "cell_name": ["Cell"]}
        ),
        "silver/chembl/tissue": pa.table(
            {"tissue_id": ["CHEMBL20"], "pref_name": ["Tissue"]}
        ),
    }
    reader, hook = prepare_assay_replay(
        config=config,
        reader=AsyncMock(read_table=AsyncMock(side_effect=lambda name: tables[name])),
        storage=storage,
        settings=settings,
        logger=logger,
    )
    merger = build_composite_merge_service(
        config=config,
        storage=storage,
        resolve_gold_schema=resolve_composite_gold_schema,
        delta_reader=reader,
        field_group_registry=None,
        cross_validator=None,
        logger=logger,
        system_columns_to_drop=CompositeSupportServicesFactory._SYSTEM_COLUMNS_TO_DROP,
        normalization_policies=JOIN_KEY_NORMALIZATION_POLICIES,
        execution_hook=hook,
        clock=FixedClock(timestamp),
    )
    request = build_merge_execution_request(
        seed_table=config.seed.silver_table,
        seed_pipeline=config.seed.pipeline,
        enrichers=config.enrichers,
        enrichment_results={
            item.pipeline: EnrichmentResult.success(item.pipeline, 1, 1)
            for item in config.enrichers
        },
        run_id=run_id,
        metadata_timestamp=timestamp,
    )
    try:
        result = await merger.execute_request(request)
        assert result.records_merged == 3
    finally:
        await storage.aclose()
    run_root = settings.report_root / "pipeline" / config.name / run_id
    root = run_root / "replay"
    digest = digest_bytes((root / "parent.json").read_bytes())
    artifacts = replay_artifacts(settings.report_root, config.name, run_id)
    manifest, probe = project_assay_replay(
        run_root, run_id, {"artifacts": list(artifacts)}, {"objects": {}}
    )
    assert probe["result"] == "pass"
    assert manifest["exact_replay_supported"] is True
    tables.clear()
    monkeypatch.setattr(
        httpx.AsyncClient,
        "request",
        AsyncMock(side_effect=AssertionError("HTTP during offline replay")),
    )
    receipt = await replay_assay(root, digest, tmp_path / "standalone", logger=logger)
    assert receipt["silver_equal"] and receipt["gold_equal"]
    assert receipt["records"] == 3
    cli = await asyncio.to_thread(
        CliRunner().invoke,
        replay_assay_command,
        [
            "--envelope",
            str(root / "parent.json"),
            "--sha256",
            digest,
            "--output",
            str(tmp_path / "cli-replay"),
        ],
    )
    assert cli.exit_code == 0, cli.output
    assert "Silver/Gold equal" in cli.output
    # Re-enable HTTP only for the real local production health server below.
    monkeypatch.undo()
    await _verify_production_http_chain(
        tmp_path, settings, run_id, artifacts, monkeypatch
    )
    (root / "expected/gold.arrow").unlink()
    _, probe = project_assay_replay(
        run_root, run_id, {"artifacts": list(artifacts)}, {"objects": {}}
    )
    assert probe["result"] == "fail"
    with pytest.raises(FileNotFoundError):
        await replay_assay(root, digest, tmp_path / "missing-input", logger=logger)


async def _verify_production_http_chain(
    tmp_path, settings, run_id, artifacts, monkeypatch
):
    from dataclasses import replace
    from uuid import UUID
    import httpx
    from bioetl.application.services.run_reports.writer import write_pipeline_run_report
    from bioetl.composition.bootstrap.assembly import health_server as assembly
    from bioetl.domain.control_plane import (
        ReplayCapability,
        RunInputSnapshotRef,
        RunSourceRef,
    )
    from bioetl.domain.normalization.json import stable_json_hash
    from bioetl.domain.run_reports.pipeline_report_assembly import (
        build_pipeline_run_report,
    )
    from bioetl.domain.run_reports.selected_status import DOMAINS
    from bioetl.domain.types import RunID
    from bioetl.infrastructure.control_plane.file_effective_config_artifact_store import (
        FileEffectiveConfigArtifactStore,
    )
    from bioetl.infrastructure.storage.composite_replay_bundle import digest_bytes
    from bioetl.interfaces.cli.commands.domains.health import (
        server_integration_deps as cli,
    )
    from bioetl.interfaces.http import run_report_ops
    from tests.unit.application.services.run_manifest_test_support import (
        RunManifestOverrides,
        make_run_manifest,
    )

    monkeypatch.setattr(assembly, "get_settings", lambda: settings)
    monkeypatch.setattr(cli, "load_settings", lambda: settings)
    monkeypatch.setattr(
        run_report_ops, "_effective_root", lambda root: settings.report_root
    )
    deps = assembly.create_health_server_dependencies(
        metrics=MagicMock(),
        checkpoint_port_factory=lambda _: AsyncMock(),
        data_root=settings.data_dir,
    )
    control = settings.data_dir / "output/control"
    config = {"identity_version": "effective-config-v1", "config_data": {"limit": 100}}
    FileEffectiveConfigArtifactStore(control / "effective_config").save(
        artifact_id="assay-config",
        run_id=RunID(UUID(run_id)),
        payload={
            "artifact_id": "assay-config",
            "semantic_artifact": {"effective_execution_config": config},
        },
    )
    lock = b"locked dependency fixture"
    lock_hash = digest_bytes(lock)
    lock_path = control / "dependency_locks" / lock_hash
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    lock_path.write_bytes(lock)
    child_artifacts = []
    identities = []
    child_paths = []
    for index, entity in enumerate(("assay", "cell_line", "tissue", "parent"), 1):
        parent = entity == "parent"
        selected_id = run_id if parent else f"00000000-0000-4000-8000-{index:012d}"
        pipeline = "composite_assay" if parent else f"chembl_{entity}"
        artifact_id = f"config-{entity}"
        FileEffectiveConfigArtifactStore(control / "effective_config").save(
            artifact_id=artifact_id,
            run_id=RunID(UUID(selected_id)),
            payload={
                "artifact_id": artifact_id,
                "semantic_artifact": {"effective_execution_config": config},
            },
        )
        bronze = settings.data_dir / f"output/bronze/chembl/{entity}/batch.jsonl"
        bronze.parent.mkdir(parents=True, exist_ok=True)
        bronze.write_bytes(b'{"saved":true}\n')
        manifest = make_run_manifest(
            run_id=RunID(UUID(selected_id)),
            limit=100,
            replay_capability=ReplayCapability.REBUILD_ONLY
            if parent
            else ReplayCapability.EXACT_REPLAY_SUPPORTED,
            source_refs=()
            if parent
            else (
                RunSourceRef(
                    provider="chembl",
                    entity=entity,
                    pipeline_name=pipeline,
                    input_snapshots=(
                        RunInputSnapshotRef(
                            snapshot_id="batch",
                            content_hash=digest_bytes(bronze.read_bytes()),
                            immutable_uri="bronze://batch.jsonl",
                        ),
                    ),
                ),
            ),
            overrides=RunManifestOverrides(
                pipeline_name=pipeline,
                provider="composite" if parent else "chembl",
                effective_config_hash=stable_json_hash(config),
                effective_config_artifact_id=artifact_id,
                dependency_lock_hash="sha256:" + lock_hash,
            ),
        )
        manifest = replace(manifest, manifest_id=f"manifest-{entity}", entity=entity)
        deps.run_manifest_port.save(manifest)
        draft = build_pipeline_run_report(
            identity={
                "pipeline_name": pipeline,
                "run_id": selected_id,
                "manifest_id": manifest.manifest_id,
                "status": "success",
                "run_type": "incremental",
                "started_at": "2026-10-03T00:00:00+00:00",
                "completed_at": "2026-10-03T00:01:00+00:00",
            },
            metrics={},
        )
        report = replace(
            draft,
            observations={
                name: {"verdict": "OK", "reason": "checked", "facts": {}}
                for name in DOMAINS[1:]
            },
            artifacts=tuple(child_artifacts) + artifacts if parent else (),
        )
        path = write_pipeline_run_report(
            report, root=settings.report_root, store=deps.run_report_store
        ).json_path
        if not parent:
            child_paths.append(path)
            child_artifacts.append(
                {
                    "kind": "composite_child_run_report",
                    "pipeline_name": pipeline,
                    "run_id": selected_id,
                    "manifest_id": manifest.manifest_id,
                    "ref": f"pipeline/{pipeline}/{selected_id}/pipeline-run-report.json",
                    "sha256": canonical_report_sha256(
                        json.loads(path.read_text(encoding="utf-8"))
                    ),
                }
            )
        identities.append((pipeline, selected_id))
    server = cli.build_health_server(
        host="127.0.0.1", port=0, deps=deps, quarantine_service=None
    )
    await server.start()
    try:
        port = server._server.sockets[0].getsockname()[1]
        async with httpx.AsyncClient(trust_env=False) as client:
            for pipeline, selected_id in identities:
                response = await client.get(
                    f"http://127.0.0.1:{port}/ops/observability/selected-run-status",
                    params={"pipeline": pipeline, "run_id": selected_id},
                )
                response.raise_for_status()
                status = response.json()
                assert status["replay_readiness"][0]["verdict"] == "READY", status[
                    "replay_readiness"
                ][0]["explanation"]
                assert status["verdict"] == "OK", status
                assert status["evidence_completeness"] == "COMPLETE", status
            for path in child_paths:
                original = path.read_bytes()
                path.write_bytes(b"corrupted child")
                response = await client.get(
                    f"http://127.0.0.1:{port}/ops/observability/selected-run-status",
                    params={"pipeline": "composite_assay", "run_id": run_id},
                )
                assert response.json()["replay_readiness"][0]["verdict"] == "BLOCKED"
                path.write_bytes(original)
    finally:
        await server.stop()
