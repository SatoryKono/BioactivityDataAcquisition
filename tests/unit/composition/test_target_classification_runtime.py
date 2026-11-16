"""Run-bound target classification: synthetic integration, not biological admission."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.services.target_classification_scope import (
    TARGET_CLASSIFICATION_DEPENDENCY_KEY,
    bind_target_classification_dependency,
    reset_target_classification_dependency,
)
from bioetl.application.services.workflow.control_plane.execution_service import (
    WorkflowExecutionService,
)
from bioetl.composition.factories.pipeline.transformer_builder import TransformerBuilder
from bioetl.composition.factories.services._record_processor_policy_support import (
    extract_hash_policy,
    extract_hash_policy_by_version,
)
from bioetl.composition.runtime_builders.config_access import load_pipeline_config
from bioetl.composition.target_classification import (
    preflight_workflow_target_dependencies,
    resolve_target_runtime_config,
    target_classification_config_source_refs,
    target_classification_source_refs,
    validate_target_runtime_dependency,
)
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from tests.helpers.clock import FIXED_TEST_TIME

pytestmark = pytest.mark.unit


@pytest.fixture
def shadow_config(tmp_path: Path) -> PipelineYamlConfig:
    def write(name: str, payload: object) -> dict[str, str]:
        raw = json.dumps(payload, sort_keys=True).encode()
        (tmp_path / name).write_bytes(raw)
        return {"path": name, "sha256": hashlib.sha256(raw).hexdigest()}

    targets = write(
        "targets.json",
        [
            {
                "targetId": 1,
                "type": "enzyme",
                "familyIds": [],
                "taxonId": "9606",
                "uniprotIds": ["P12345"],
                "name": "known enzyme",
                "synonyms": [],
            }
        ],
    )
    snapshot = write(
        "snapshot.json",
        {
            "artifact": "bioetl_iuphar_snapshot",
            "schema_version": 1,
            "format": "gtopdb_target_payload_v1",
            "snapshot_id": "synthetic-runtime-snapshot",
            "provider_release": "2026.3.1",
            "retrieved_at": "2026-11-16T00:00:00Z",
            "targets": targets,
            "species_taxon_ids": ["9606"],
            "required_target_types": ["enzyme"],
            "expected_target_count": 1,
            "provider_versions": "совпали",
            "coverage_approval_reference": "synthetic-fixture-only",
            "pagination_complete": True,
        },
    )
    profile = write(
        "profile.json",
        {
            "artifact": "bioetl_iuphar_profile",
            "schema_version": 1,
            "snapshot": snapshot,
            "acceptance": None,
            "normalization_version": "bioetl-iuphar-input-v1",
            "rules_version": "plan-v1-r8",
            "classification_schema_version": "3.1.0",
        },
    )
    payload = load_pipeline_config("chembl_target").model_dump(exclude_defaults=True)
    payload["target_classification"] = {
        "mode": "shadow",
        "snapshot_manifest": str(tmp_path / "profile.json"),
        "snapshot_manifest_sha256": profile["sha256"],
    }
    return PipelineYamlConfig.model_validate(payload)


def _transformer(config: PipelineYamlConfig, root: Path):
    return TransformerBuilder("chembl", "chembl_target", lambda _: "target").build(
        transformer_class=TargetTransformer,
        yaml_config=config,
        domain_config=yaml_config_to_domain(config),
        pandera_silver_schema=None,
        tracer=None,
        metrics=None,
        settings=SimpleNamespace(data_dir=root),
    )


def _context() -> PipelineContext:
    return PipelineContext(
        run_id=UUID("9d312112-8fcf-472d-a151-636b0184be16"),
        run_type=RunType.INCREMENTAL,
        logger=MagicMock(),
        started_at=FIXED_TEST_TIME,
        pipeline_name="chembl_target",
    )


def _admitted_synthetic_config(config: PipelineYamlConfig) -> PipelineYamlConfig:
    """Tagged fixture only; no claim of executed scientific reference admission."""
    from bioetl.infrastructure.adapters.iuphar.snapshot_loader import OUTPUT_NAMES, REQUIRED_ACCEPTANCE_CHECKS

    path = Path(config.target_classification.snapshot_manifest)
    profile = json.loads(path.read_bytes())
    receipt = {
        "artifact": "bioetl_iuphar_acceptance", "schema_version": 1,
        "fixture_kind": "synthetic_contract_fixture", "scope": "offline_target_integration",
        "status": "PASS", "snapshot_manifest_sha256": profile["snapshot"]["sha256"],
        "stage0_manifest_sha256": "a" * 64, "expected_labels_sha256": "b" * 64,
        "output_sha256": dict.fromkeys(OUTPUT_NAMES, "c" * 64),
        "checks": dict.fromkeys(REQUIRED_ACCEPTANCE_CHECKS, "PASS"),
        "reference_cases_accepted": True, "biological_accuracy_accepted": False,
        "run_id": "synthetic-contract-run", "reviewer_reference": "synthetic-unit-test-only",
        "normalization_version": "bioetl-iuphar-input-v1", "rules_version": "plan-v1-r8",
        "classification_schema_version": "3.1.0",
    }
    raw = json.dumps(receipt, sort_keys=True).encode()
    (path.parent / "synthetic-acceptance.json").write_bytes(raw)
    profile["acceptance"] = {"path": "synthetic-acceptance.json", "sha256": hashlib.sha256(raw).hexdigest()}
    raw = json.dumps(profile, sort_keys=True).encode()
    path.write_bytes(raw)
    classification = config.target_classification.model_copy(update={
        "mode": "enrich", "snapshot_manifest_sha256": hashlib.sha256(raw).hexdigest(),
    })
    return config.model_copy(update={"target_classification": classification})


@pytest.mark.asyncio
async def test_enrich_uses_v31_schema_and_identical_direct_staged_hash(shadow_config, tmp_path):
    from bioetl.domain.normalization.profiles.chembl_target_classification import target_v31_normalization_profile
    from bioetl.composition.factories.storage._layer_writers import load_contract_rollout_policy
    from bioetl.composition.target_classification import target_classification_normalization_identity

    config = _admitted_synthetic_config(shadow_config)
    direct = _transformer(config, tmp_path / "direct")
    staged = _transformer(config, tmp_path / "staged")
    context = _context()
    data = {"target_chembl_id": "CHEMBL1", "target_type": "SINGLE PROTEIN", "pref_name": "known enzyme",
        "tax_id": 9606, "organism": "Homo sapiens", "species_group_flag": False,
        "target_components": [{"accession": "P12345", "component_id": 1, "component_type": "PROTEIN",
            "relationship": "SINGLE PROTEIN", "target_component_synonyms": [], "target_component_xrefs": []}]}
    result = await direct.transform(context, data, 0)
    payload = await staged.transform_pre_silver(context, data, 0)
    pipeline = SimpleNamespace(transformer=staged)
    includes, excludes = extract_hash_policy(pipeline)
    normalizer = RecordNormalizationProcessor(
        "chembl", "target", profile=target_v31_normalization_profile(),
        content_hash_policy_authoritative=True, content_hash_include_fields=includes,
        content_hash_exclude_fields=excludes,
        content_hash_policy_by_version=extract_hash_policy_by_version(pipeline, include_fields=includes, exclude_fields=excludes),
    )
    assert result == normalizer.finalize_pre_silver(payload, context, 0)
    assert result["iuphar_class"] == "Enzyme"
    assert result["target_class_profile_sha256"] == config.target_classification.snapshot_manifest_sha256
    assert direct._contract_policy.active_version == "3.1.0"
    assert direct._contract_policy.rollout.write_versions == ["3.1.0"]
    writer_policy = load_contract_rollout_policy(config)
    assert writer_policy.active_version == "3.1.0"
    assert writer_policy.mode == "single"
    assert target_classification_normalization_identity(config)[2] == target_v31_normalization_profile().identity.profile_hash


@pytest.mark.asyncio
async def test_shadow_preserves_old_output_and_staged_direct_parity(
    shadow_config, tmp_path
):
    off = load_pipeline_config("chembl_target")
    direct = _transformer(shadow_config, tmp_path / "direct")
    staged = _transformer(shadow_config, tmp_path / "staged")
    legacy = _transformer(off, tmp_path / "legacy")
    legacy_staged = _transformer(off, tmp_path / "legacy-staged")
    context = _context()
    raw = {
        "target_chembl_id": "CHEMBL1",
        "target_type": "SINGLE PROTEIN",
        "pref_name": "  known enzyme  ",
        "tax_id": 9606,
        "organism": "Homo sapiens",
        "species_group_flag": False,
        "target_components": [
            {
                "accession": "P12345",
                "component_id": 1,
                "component_type": "PROTEIN",
                "relationship": "SINGLE PROTEIN",
                "target_component_synonyms": [],
                "target_component_xrefs": [],
            }
        ],
    }
    direct_result = await direct.transform(context, raw, 0)
    legacy_result = await legacy.transform(context, raw, 0)
    payload = await staged.transform_pre_silver(context, raw, 0)
    pipeline = SimpleNamespace(transformer=staged)
    includes, excludes = extract_hash_policy(pipeline)
    normalizer = RecordNormalizationProcessor(
        "chembl",
        "target",
        content_hash_policy_authoritative=True,
        content_hash_include_fields=includes,
        content_hash_exclude_fields=excludes,
        content_hash_policy_by_version=extract_hash_policy_by_version(
            pipeline, include_fields=includes, exclude_fields=excludes
        ),
    )
    staged_result = normalizer.finalize_pre_silver(payload, context, 0)
    assert direct_result is not None
    legacy_payload = await legacy_staged.transform_pre_silver(context, raw, 0)
    assert direct_result == legacy_result
    assert staged_result == normalizer.finalize_pre_silver(legacy_payload, context, 0)
    # The existing V30 direct and staged routes have distinct set-like hashing.
    assert {k: v for k, v in direct_result.items() if k != "content_hash"} == {
        k: v for k, v in staged_result.items() if k != "content_hash"
    }
    assert "iuphar_class" not in direct_result
    assert direct_result["pref_name"] == "known enzyme"
    direct.finalize_target_classification(context)
    staged.finalize_target_classification(context)
    manifests = list((tmp_path / "direct").rglob("manifest.json"))
    assert len(manifests) == 1
    evidence = json.loads(manifests[0].read_text())
    assert evidence["status"] == "complete"
    assert evidence["row_count"] == 1


def test_target_preflight_uses_actual_writer_paths_even_when_off(monkeypatch, tmp_path):
    from bioetl.composition.factories.services.preflight import _validate_target_dependencies

    silver = MagicMock()
    gold = MagicMock()
    silver._resolve_table_path.return_value = str(tmp_path / "configured-silver")
    gold._resolve_table_path.return_value = str(tmp_path / "configured-gold")
    pipeline = SimpleNamespace(
        services=SimpleNamespace(storage=SimpleNamespace(silver=silver, gold=gold)),
        config=SimpleNamespace(effective_silver_table="chembl.target", effective_gold_table="chembl.target"),
    )
    guard = MagicMock()
    monkeypatch.setattr("bioetl.composition.factories.services.preflight.assert_target_table_compatibility", guard)
    _validate_target_dependencies(pipeline, load_pipeline_config("chembl_target"))
    guard.assert_called_once_with(silver_path=tmp_path / "configured-silver", gold_path=tmp_path / "configured-gold", mode="off")
    silver._resolve_table_path.assert_called_once_with("chembl.target")
    gold._resolve_table_path.assert_called_once_with("chembl.target")


def test_target_exact_replay_restores_saved_profile(shadow_config, monkeypatch):
    from bioetl.composition.runtime_builders._exact_replay_cached_bronze_context import restore_target_replay_config

    parent = SimpleNamespace(pipeline_name="chembl_target", resolved_config=shadow_config.model_dump())
    monkeypatch.setattr("bioetl.composition.runtime_builders._exact_replay_cached_bronze_context._resolve_replay_parent_manifest", lambda **kwargs: parent)
    ctx = SimpleNamespace(pipeline_name="chembl_target", exact_replay=True, replay_of_manifest_id="parent-manifest")
    restored = restore_target_replay_config(ctx=ctx, settings=SimpleNamespace(), current_config=load_pipeline_config("chembl_target"))
    assert restored.target_classification == shadow_config.target_classification
    assert evidence["mode"] == "shadow"
    assert evidence["artifact_sha256"]


def test_workflow_dependency_pins_profile_and_rechecks_bytes(
    shadow_config, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        "bioetl.composition.target_classification.load_pipeline_config",
        lambda _: shadow_config,
    )
    workflow = SimpleNamespace(steps=[SimpleNamespace(pipeline_name="chembl_target")])
    launch = preflight_workflow_target_dependencies(workflow, {})
    binding = launch[TARGET_CLASSIFICATION_DEPENDENCY_KEY]
    assert (
        binding["profile_sha256"]
        == shadow_config.target_classification.snapshot_manifest_sha256
    )
    token = bind_target_classification_dependency(binding)
    try:
        pinned = resolve_target_runtime_config(load_pipeline_config("chembl_target"))
        assert pinned.target_classification.mode == "shadow"
        validate_target_runtime_dependency(pinned)
        assert preflight_workflow_target_dependencies(workflow, launch) == launch
        (tmp_path / "targets.json").write_text("[]")
        with pytest.raises(ValueError, match="hash|SHA|digest"):
            validate_target_runtime_dependency(pinned)
    finally:
        reset_target_classification_dependency(token)


def test_snapshot_and_profile_anchored_in_both_artifact_refs(shadow_config):
    refs = target_classification_source_refs(shadow_config)
    assert refs[0].provider == "iuphar"
    assert len(refs[0].input_snapshots) == 2
    config_refs = target_classification_config_source_refs(shadow_config)
    assert {ref.source_hash for ref in config_refs} == {
        snapshot.content_hash for snapshot in refs[0].input_snapshots
    }
    assert all(ref.source_hash_strategy == "raw_bytes" for ref in config_refs)


def test_workflow_resume_rejects_changed_dependency_identity(
    shadow_config, monkeypatch
):
    monkeypatch.setattr(
        "bioetl.composition.target_classification.load_pipeline_config",
        lambda _: shadow_config,
    )
    workflow = SimpleNamespace(steps=[SimpleNamespace(pipeline_name="chembl_target")])
    launch = preflight_workflow_target_dependencies(workflow, {})
    launch[TARGET_CLASSIFICATION_DEPENDENCY_KEY]["snapshot_manifest_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="identity changed"):
        preflight_workflow_target_dependencies(workflow, launch)


def test_enrich_refuses_missing_acceptance_before_session(shadow_config, tmp_path):
    config = shadow_config.model_copy(
        update={
            "target_classification": shadow_config.target_classification.model_copy(
                update={"mode": "enrich"}
            )
        }
    )
    with pytest.raises(ValueError, match="acceptance"):
        _transformer(config, tmp_path / "enrich")


@pytest.mark.asyncio
async def test_workflow_dependency_failure_precedes_first_step_and_manifest_write():
    runner = SimpleNamespace(run_workflow=AsyncMock())
    manifests = MagicMock()
    lock = SimpleNamespace(acquire=AsyncMock(return_value="lock"), release=AsyncMock())

    def reject(config, launch):
        raise ValueError("snapshot dependency rejected")

    service = WorkflowExecutionService(
        workflow_runner=runner,
        manifest_service=manifests,
        workflow_ledger_port=MagicMock(),
        workflow_ledger_factory=MagicMock(),
        workflow_state_port=MagicMock(),
        workflow_lock_port=lock,
        run_id_factory=lambda: _context().run_id,
        now_factory=lambda: FIXED_TEST_TIME,
        dependency_preflight=reject,
    )
    config = WorkflowConfig(
        name="chembl_baseline",
        steps=(
            WorkflowStepConfig(step_id="assay", pipeline_name="chembl_assay"),
            WorkflowStepConfig(
                step_id="target", pipeline_name="chembl_target", depends_on=("assay",)
            ),
        ),
    )
    with pytest.raises(ValueError, match="dependency rejected"):
        await service.run_workflow(config)
    runner.run_workflow.assert_not_awaited()
    assert not manifests.mock_calls
    lock.release.assert_awaited_once()


@pytest.mark.asyncio
async def test_postrun_failure_never_completes_classification_evidence():
    from bioetl.application.core.runner_execution_flow import run_postrun_phase

    transformer = SimpleNamespace(finalize_target_classification=MagicMock())
    host = SimpleNamespace(
        _config=SimpleNamespace(pipeline_name="chembl_target"),
        _pipeline=SimpleNamespace(transformer=transformer, context=_context()),
        _executor=SimpleNamespace(get_dq_context=lambda: None),
        _postrun_service=SimpleNamespace(
            run=AsyncMock(side_effect=ValueError("write failed"))
        ),
    )
    with pytest.raises(ValueError, match="write failed"):
        await run_postrun_phase(host)
    transformer.finalize_target_classification.assert_not_called()


@pytest.mark.asyncio
async def test_real_runner_shadow_persists_both_layers_and_completes_evidence(
    shadow_config, tmp_path
):
    """Actual Application runner and Delta writers on explicitly synthetic rows."""
    from deltalake import DeltaTable
    from bioetl.composition.factories.pipeline.assembler import create_pipeline_factory
    from bioetl.composition.factories.pipeline.registry import chembl_target_factory
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.ports import PipelineCreateRunnerRequest
    from bioetl.domain.types import HealthStatus
    from bioetl.infrastructure.config.settings_api import Settings
    from tests.integration.pipelines.observability import (
        build_test_observability_bundle,
    )

    class SyntheticSource:
        provider_name = "chembl"

        async def __aenter__(self):
            return self

        async def __aexit__(self, *args):
            await self.aclose()

        async def aclose(self):
            pass

        async def health_check(self):
            return HealthStatus.HEALTHY

        async def fetch(self, entity_type, **kwargs):
            yield {
                "target_chembl_id": "CHEMBL1",
                "target_type": "SINGLE PROTEIN",
                "pref_name": "known enzyme",
                "tax_id": 9606,
                "organism": "Homo sapiens",
                "species_group_flag": False,
                "target_components": [
                    {
                        "accession": "P12345",
                        "component_id": 1,
                        "component_type": "PROTEIN",
                        "relationship": "SINGLE PROTEIN",
                        "target_component_synonyms": [],
                        "target_component_xrefs": [],
                    }
                ],
            }

    source = SyntheticSource()
    factory = create_pipeline_factory(
        "chembl_target",
        chembl_target_factory.pipeline_class,
        "chembl",
        silver_schema=chembl_target_factory.silver_schema,
        gold_schema=chembl_target_factory.gold_schema,
        pandera_silver_schema=chembl_target_factory.pandera_silver_schema,
        transformer_class=TargetTransformer,
        data_source_creator=lambda *args, **kwargs: source,
    )
    settings = Settings(
        test_mode=True, data_dir=tmp_path / "runner-data", _env_file=None
    )
    runner = factory.create_runner(
        PipelineCreateRunnerRequest(
            run_id=_context().run_id,
            started_at=FIXED_TEST_TIME,
            runtime=RuntimeConfig(run_type=RunType.INCREMENTAL, limit=1),
            settings=settings,
            config=shadow_config,
            observability=build_test_observability_bundle(),
        )
    )
    await runner.run()
    assert runner.execution_metrics["records_silver"] == 1
    assert runner.execution_metrics["records_gold"] == 1
    silver = DeltaTable(settings.silver_path / "chembl/target").to_pyarrow_table()
    gold = DeltaTable(settings.gold_path / "chembl/target").to_pyarrow_table()
    assert silver.num_rows == gold.num_rows == 1
    assert "iuphar_class" not in silver.column_names
    manifest_path = (
        settings.data_dir
        / "output/control/target_classification"
        / str(_context().run_id)
        / "manifest.json"
    )
    evidence = json.loads(manifest_path.read_text())
    assert evidence["status"] == "complete"
    assert evidence["row_count"] == 1
