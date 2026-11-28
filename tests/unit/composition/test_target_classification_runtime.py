"""Run-bound target classification: synthetic integration, not biological admission."""

from __future__ import annotations

import hashlib
import json
from dataclasses import replace
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest

from bioetl.application.core.batch_transformer_attempt_success import (
    build_transform_success_outcome,
)
from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.application.pipelines.chembl.target_transformer import TargetTransformer
from bioetl.application.services.target_runtime.scope import (
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
from bioetl.composition.bootstrap.assembly.storage import (
    preflight_workflow_target_dependencies,
)
from bioetl.composition.bootstrap.assembly.target_classification_runtime import (
    resolve_target_runtime_config,
    validate_target_runtime_dependency,
)
from bioetl.composition.bootstrap.assembly.target_classification_identity import (
    load_target_aware_pipeline_config,
    target_classification_config_source_refs,
    target_classification_source_refs,
)
from bioetl.domain.config import DQConfig, FieldValidation
from bioetl.domain.context import PipelineContext
from bioetl.domain.exceptions.validation import ValidationError
from bioetl.domain.types import RunType
from bioetl.domain.workflow import WorkflowConfig, WorkflowStepConfig
from bioetl.infrastructure.config.converters import yaml_config_to_domain
from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig
from bioetl.infrastructure.schemas.target_classification_config import (
    TargetClassificationYamlConfig,
)
from tests.helpers.clock import FIXED_TEST_TIME

pytestmark = pytest.mark.unit


def _legacy_config() -> PipelineYamlConfig:
    return load_pipeline_config("chembl_target").model_copy(
        update={"target_classification": TargetClassificationYamlConfig(mode="off")}
    )


@pytest.fixture
def shadow_config(tmp_path: Path, monkeypatch) -> PipelineYamlConfig:
    from bioetl.infrastructure.config.settings_api import Settings

    settings = Settings(
        test_mode=True, data_dir=tmp_path / "workflow-data", _env_file=None
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.get_settings",
        lambda: settings,
    )

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
            "rules_version": "local-rules-2026.11.23",
            "classification_schema_version": "3.1.0",
            "matching_policy_version": "rf002-uniprot-roles-2026-11-23",
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
    from tests.helpers.iuphar_snapshot import (
        synthetic_snapshot_bundle,
        synthetic_reference_receipt,
        write_fixture_json,
    )

    path = Path(config.target_classification.snapshot_manifest)
    output, bundle = synthetic_snapshot_bundle(path.parent / "verified-v2")
    profile = json.loads((output / "profile.json").read_bytes())
    receipt_hash = write_fixture_json(
        output / "synthetic-acceptance.json",
        synthetic_reference_receipt(
            bundle.snapshot_sha256, root=output / "reference-fixture"
        ),
    )
    profile["acceptance"] = {
        "path": "synthetic-acceptance.json",
        "sha256": receipt_hash,
    }
    admitted_path = output / "enrich-profile.json"
    profile_hash = write_fixture_json(admitted_path, profile)
    classification = config.target_classification.model_copy(
        update={
            "mode": "enrich",
            "snapshot_manifest": str(admitted_path),
            "snapshot_manifest_sha256": profile_hash,
        }
    )
    return config.model_copy(update={"target_classification": classification})


@pytest.mark.asyncio
async def test_enrich_uses_v31_schema_and_identical_direct_staged_hash(
    shadow_config, tmp_path
):
    from bioetl.domain.normalization.profiles.chembl_target_classification import (
        target_v31_normalization_profile,
    )
    from bioetl.composition.factories.storage._layer_writers import (
        load_contract_rollout_policy,
    )
    from bioetl.composition.bootstrap.assembly.target_classification_identity import (
        target_classification_normalization_identity,
    )

    config = _admitted_synthetic_config(shadow_config)
    direct = _transformer(config, tmp_path / "direct")
    staged = _transformer(config, tmp_path / "staged")
    context = _context()
    data = {
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
    result = await direct.transform(context, data, 0)
    payload = await staged.transform_pre_silver(context, data, 0)
    pipeline = SimpleNamespace(transformer=staged)
    includes, excludes = extract_hash_policy(pipeline)
    normalizer = RecordNormalizationProcessor(
        "chembl",
        "target",
        profile=target_v31_normalization_profile(),
        content_hash_policy_authoritative=True,
        content_hash_include_fields=includes,
        content_hash_exclude_fields=excludes,
        content_hash_policy_by_version=extract_hash_policy_by_version(
            pipeline, include_fields=includes, exclude_fields=excludes
        ),
    )
    assert result == normalizer.finalize_pre_silver(payload, context, 0)
    assert result["iuphar_class"] == "Receptor"
    assert (
        result["target_class_profile_sha256"]
        == config.target_classification.snapshot_manifest_sha256
    )
    assert direct._contract_policy.active_version == "3.1.0"
    assert direct._contract_policy.rollout.write_versions == ["3.1.0"]
    writer_policy = load_contract_rollout_policy(config)
    assert writer_policy.active_version == "3.1.0"
    assert writer_policy.mode == "single"
    assert (
        target_classification_normalization_identity(config)[2]
        == target_v31_normalization_profile().identity.profile_hash
    )


@pytest.mark.asyncio
async def test_shadow_preserves_old_output_and_staged_direct_parity(
    shadow_config, tmp_path
):
    off = _legacy_config()
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
    assert evidence["input_row_ids"] == ["chembl.target:CHEMBL1"]
    assert evidence["mode"] == "shadow"
    assert evidence["artifact_sha256"]
    assert evidence["input_row_ids"] == ["chembl.target:CHEMBL1"]


@pytest.mark.asyncio
@pytest.mark.parametrize("failure", ["structural_policy", "silver_filter", "direct"])
async def test_rejected_target_rows_release_pending_classification(
    shadow_config, tmp_path, monkeypatch, failure
):
    transformer = _transformer(shadow_config, tmp_path / "evidence")
    assert isinstance(transformer, TargetTransformer)
    session = transformer._target_classification_session
    assert session is not None
    context = _context()
    raw = {
        "target_chembl_id": "CHEMBL1",
        "target_type": "SINGLE PROTEIN",
        "pref_name": "known enzyme",
        "tax_id": 9606,
        "organism": "Homo sapiens",
        "species_group_flag": False,
    }

    def reject(*args, **kwargs):
        assert session._pending
        raise ValueError("test row rejection")

    def drop(*args, **kwargs):
        assert session._pending
        return None

    if failure == "direct":
        monkeypatch.setattr(transformer, "_apply_structural_policy", reject)
        with pytest.raises(ValueError, match="test row rejection"):
            await transformer.transform(context, raw, 0)
    else:
        payload = await transformer.transform_pre_silver(context, raw, 0)
        assert payload is not None
        normalizer = RecordNormalizationProcessor("chembl", "target")
        if failure == "structural_policy":
            payload = replace(payload, apply_structural_policy=drop)
            assert normalizer.finalize_pre_silver(payload, context, 0) is None
        else:
            payload = replace(payload, apply_silver_filter=reject)
            with pytest.raises(ValueError, match="test row rejection"):
                normalizer.finalize_pre_silver(payload, context, 0)

    assert not session._pending
    assert not session._published


@pytest.mark.asyncio
@pytest.mark.parametrize("disposition", ["quarantine", "skip", "fail"])
async def test_shadow_evidence_excludes_targets_rejected_by_runtime_dq(
    shadow_config, tmp_path, disposition
):
    transformer = _transformer(shadow_config, tmp_path / "evidence")
    assert isinstance(transformer, TargetTransformer)
    context = _context()
    normalizer = RecordNormalizationProcessor("chembl", "target")
    dq_config = DQConfig(
        invalid_record_policy=disposition,
        field_validations=(
            FieldValidation(
                field="pref_name", validation_type="enum", allowed=("accepted",)
            ),
        ),
    )
    target = {
        "target_type": "SINGLE PROTEIN",
        "tax_id": 9606,
        "organism": "Homo sapiens",
        "species_group_flag": False,
    }

    async def attempt(target_id, name, index):
        return await build_transform_success_outcome(
            context=context,
            transform=transformer.transform_pre_silver,
            raw_record={**target, "target_chembl_id": target_id, "pref_name": name},
            index=index,
            normalization_processor=normalizer,
            gold_filter=lambda _context, _record: False,
            gold_transform=lambda _context, record: record,
            dq_config=dq_config,
            debug_export_service=None,
        )

    with pytest.raises(ValidationError, match=f"disposition={disposition}"):
        await attempt("CHEMBL1", "rejected", 0)
    accepted = await attempt("CHEMBL2", "accepted", 1)
    assert accepted.silver_record is not None
    assert accepted.silver_record["target_id"] == "CHEMBL2"

    session = transformer._target_classification_session
    assert session is not None
    assert not session._pending
    transformer.finalize_target_classification(context)
    [manifest_path] = (tmp_path / "evidence").rglob("manifest.json")
    evidence = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert evidence["status"] == "complete"
    assert evidence["input_row_ids"] == ["chembl.target:CHEMBL2"]


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["shadow", "enrich"])
@pytest.mark.parametrize("disposition", ["quarantine", "skip", "fail"])
async def test_runtime_dq_rejection_excludes_target_from_final_evidence(
    shadow_config, tmp_path, mode, disposition
):
    from bioetl.application.core.batch_transformer_attempt_success import (
        build_transform_success_outcome,
    )
    from bioetl.domain.config import DQConfig
    from bioetl.domain.config.validation_rules import FieldValidation
    from bioetl.domain.exceptions.validation import ValidationError
    from bioetl.domain.types.dq_contracts import DQDisposition

    config = (
        shadow_config if mode == "shadow" else _admitted_synthetic_config(shadow_config)
    )
    root = tmp_path / "runtime-dq"
    transformer = _transformer(config, root)
    session = transformer._target_classification_session
    normalizer = RecordNormalizationProcessor("chembl", "target")
    context = _context()
    dq = DQConfig(
        field_validations=(
            FieldValidation(
                field="pref_name", validation_type="enum", allowed=("accepted",)
            ),
        ),
        default_disposition_policy=DQDisposition(disposition),
    )

    async def attempt(identifier, name, index):
        return await build_transform_success_outcome(
            context=context,
            transform=transformer.transform_pre_silver,
            raw_record={
                "target_chembl_id": identifier,
                "pref_name": name,
                "target_type": "SINGLE PROTEIN",
                "organism": "Homo sapiens",
                "tax_id": 9606,
                "species_group_flag": False,
                "target_components": [],
            },
            index=index,
            normalization_processor=normalizer,
            gold_filter=lambda *_: False,
            gold_transform=lambda _, record: record,
            dq_config=dq,
            debug_export_service=None,
        )

    with pytest.raises(ValidationError, match=f"disposition={disposition}"):
        await attempt("CHEMBL1", "rejected", 0)
    assert session._pending == {}
    assert session._published == {}
    accepted = await attempt("CHEMBL2", "accepted", 1)
    assert accepted.silver_record["target_id"] == "CHEMBL2"
    assert accepted.gold_record is None
    assert session._pending == {}
    transformer.finalize_target_classification(context)
    manifests = list(root.rglob("manifest.json"))
    assert len(manifests) == 1
    evidence = json.loads(manifests[0].read_text())
    assert evidence["status"] == "complete"
    assert evidence["row_count"] == 1
    assert evidence["input_row_ids"] == ["chembl.target:CHEMBL2"]


@pytest.mark.parametrize("dry_run", [False, True])
def test_historical_target_preflight_uses_actual_writer_paths(
    monkeypatch, tmp_path, dry_run
):
    from bioetl.composition.factories.services.preflight import (
        _validate_target_dependencies,
    )

    silver = SimpleNamespace(
        _resolve_table_path=MagicMock(return_value=str(tmp_path / "configured-silver"))
    )
    gold = SimpleNamespace(
        _resolve_table_path=MagicMock(return_value=str(tmp_path / "configured-gold"))
    )
    pipeline = SimpleNamespace(
        services=SimpleNamespace(storage=SimpleNamespace(silver=silver, gold=gold)),
        runtime=SimpleNamespace(
            run_type=RunType.INCREMENTAL, dry_run=dry_run, exact_replay=True
        ),
        config=SimpleNamespace(
            effective_silver_table="chembl.target", effective_gold_table="chembl.target"
        ),
    )
    guard = MagicMock()
    monkeypatch.setattr(
        "bioetl.composition.factories.services.preflight.assert_target_table_compatibility",
        guard,
    )
    _validate_target_dependencies(pipeline, _legacy_config())
    if dry_run:
        guard.assert_not_called()
        silver._resolve_table_path.assert_not_called()
        gold._resolve_table_path.assert_not_called()
        return
    guard.assert_called_once_with(
        silver_path=tmp_path / "configured-silver",
        gold_path=tmp_path / "configured-gold",
        mode="off",
        destructive=False,
        table_contract="3.0.0",
    )
    silver._resolve_table_path.assert_called_once_with("chembl.target")
    gold._resolve_table_path.assert_called_once_with("chembl.target")


def test_target_exact_replay_prefers_parent_to_current_workflow_binding(
    shadow_config, tmp_path
):
    parent = SimpleNamespace(
        pipeline_name="chembl_target", resolved_config=shadow_config.model_dump()
    )
    ctx = SimpleNamespace(
        pipeline_name="chembl_target",
        exact_replay=True,
        replay_of_manifest_id="parent-manifest",
    )
    current_config = load_pipeline_config("chembl_target")
    token = bind_target_classification_dependency(
        {"target_config": current_config.model_dump()}
    )
    try:
        restored = load_target_aware_pipeline_config(
            "chembl_target",
            lambda _: current_config,
            lambda _: None,
            ctx=ctx,
            settings=SimpleNamespace(),
            resolve_parent=lambda **kwargs: parent,
        )
        assert restored.target_classification == shadow_config.target_classification
        assert (
            resolve_target_runtime_config(restored).target_classification
            == current_config.target_classification
        )
        assert (
            resolve_target_runtime_config(
                restored, exact_replay=True
            ).target_classification
            == shadow_config.target_classification
        )
        validate_target_runtime_dependency(restored, exact_replay=True)

        (tmp_path / "targets.json").write_text("[]")
        with pytest.raises(ValueError, match="hash|SHA|digest"):
            validate_target_runtime_dependency(restored, exact_replay=True)
    finally:
        reset_target_classification_dependency(token)


def test_workflow_resume_restores_and_forbids_replacing_pinned_dependency(
    shadow_config, monkeypatch
):
    from bioetl.application.services.workflow.control_plane.execution_service import (
        _restore_workflow_target_dependency,
    )

    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda _: shadow_config,
    )
    config = WorkflowConfig(
        name="chembl_baseline", steps=(WorkflowStepConfig("target", "chembl_target"),)
    )
    binding = preflight_workflow_target_dependencies(config, {})[
        TARGET_CLASSIFICATION_DEPENDENCY_KEY
    ]
    manifest = SimpleNamespace(
        to_dict=lambda: {
            "launch_context": {TARGET_CLASSIFICATION_DEPENDENCY_KEY: binding}
        }
    )
    state = SimpleNamespace(manifest_id="saved-manifest")
    service = SimpleNamespace(
        dependency_preflight=preflight_workflow_target_dependencies,
        workflow_state_port=SimpleNamespace(get_by_manifest_id=lambda _: state),
        manifest_service=SimpleNamespace(
            manifest_port=SimpleNamespace(get=lambda _: manifest)
        ),
    )
    launch = {"resume_manifest_id": "saved-manifest"}
    _restore_workflow_target_dependency(
        service=service, config=config, launch_context=launch, resume_requested=True
    )
    assert launch[TARGET_CLASSIFICATION_DEPENDENCY_KEY] == binding
    launch[TARGET_CLASSIFICATION_DEPENDENCY_KEY] = {"profile_sha256": "replacement"}
    with pytest.raises(ValueError, match="cannot replace"):
        _restore_workflow_target_dependency(
            service=service, config=config, launch_context=launch, resume_requested=True
        )


def test_enrich_metadata_binds_actual_schema_and_normalization_hash(shadow_config):
    from bioetl.composition.factories.pipeline.run_context_factory import (
        RunContextFactory,
    )
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.contracts.gold.chembl_target_classification import (
        target_v31_schema_hash,
    )
    from bioetl.domain.normalization.profiles.chembl_target_classification import (
        target_v31_normalization_profile,
    )
    from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE

    config = _admitted_synthetic_config(shadow_config)
    factory = RunContextFactory("chembl_target", "chembl", lambda _: "target")
    context = factory.create(
        run_id=_context().run_id,
        runtime=RuntimeConfig(run_type=RunType.INCREMENTAL),
        started_at=FIXED_TEST_TIME,
        yaml_config=config,
    )
    assert context.contract_version == "3.1.0"
    assert context.contract_schema_hash == target_v31_schema_hash()
    assert (
        context.normalization_profile_hash
        == target_v31_normalization_profile().identity.profile_hash
    )
    assert (
        context.normalization_profile_hash
        != CHEMBL_TARGET_PROFILE.identity.profile_hash
    )


def test_workflow_dependency_pins_profile_and_rechecks_bytes(
    shadow_config, monkeypatch, tmp_path
):
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda _: shadow_config,
    )
    workflow = WorkflowConfig(
        "target", steps=(WorkflowStepConfig("target", "chembl_target"),)
    )
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
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda _: shadow_config,
    )
    workflow = WorkflowConfig(
        "target", steps=(WorkflowStepConfig("target", "chembl_target"),)
    )
    launch = preflight_workflow_target_dependencies(workflow, {})
    launch[TARGET_CLASSIFICATION_DEPENDENCY_KEY]["snapshot_manifest_sha256"] = "f" * 64
    with pytest.raises(ValueError, match="identity changed"):
        preflight_workflow_target_dependencies(workflow, launch)


def test_completed_resume_verifies_legacy_pin_without_new_enrich_admission(
    shadow_config, monkeypatch
):
    from bioetl.application.services.workflow.control_plane.mutation_plan import (
        WorkflowMutationSpec,
    )

    config = shadow_config.model_copy(
        update={
            "target_classification": shadow_config.target_classification.model_copy(
                update={"mode": "enrich"}
            )
        }
    )
    workflow = WorkflowConfig(
        "historic", steps=(WorkflowStepConfig("target", "chembl_target"),)
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda _: config,
    )
    plan = WorkflowMutationSpec(frozenset(), resumed=True)
    binding = preflight_workflow_target_dependencies(workflow, {}, plan)
    assert (
        binding[TARGET_CLASSIFICATION_DEPENDENCY_KEY]["profile_sha256"]
        == config.target_classification.snapshot_manifest_sha256
    )
    Path(config.target_classification.snapshot_manifest).write_bytes(b"replaced")
    with pytest.raises(ValueError, match="SHA|hash|digest"):
        preflight_workflow_target_dependencies(workflow, binding, plan)


def test_enrich_refuses_missing_acceptance_before_session(shadow_config, tmp_path):
    from tests.helpers.iuphar_snapshot import synthetic_snapshot_bundle

    output, bundle = synthetic_snapshot_bundle(tmp_path / "unaccepted-v2")
    config = shadow_config.model_copy(
        update={
            "target_classification": shadow_config.target_classification.model_copy(
                update={
                    "mode": "enrich",
                    "snapshot_manifest": str(output / "profile.json"),
                    "snapshot_manifest_sha256": bundle.profile_sha256,
                }
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

    def reject(config, launch, mutation_plan):
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


class _SyntheticChemblSource:
    provider_name = "chembl"

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        await self.aclose()

    async def aclose(self):
        pass

    async def health_check(self):
        from bioetl.domain.types import HealthStatus

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


def _assert_shadow_pipeline_proof(
    *, config, silver, manifest_path, run_report_json_path, tmp_path
):
    from bioetl.infrastructure.adapters.iuphar import load_profile
    from bioetl.infrastructure.adapters.iuphar.canonical_target_rows import (
        render_canonical_target_rows,
    )
    from bioetl.infrastructure.adapters.iuphar.cohort_contract import (
        ARROW_SOURCE_FORMAT,
        NORMALIZED_TARGET_SCHEMA,
        CohortExportRequest,
    )
    from iuphar_target_class.models import RunProvenance
    from iuphar_target_class.pipeline import classify_batch
    from iuphar_target_class.pipeline_io import read_bioetl_target_kernel_csv_v1
    from iuphar_target_class.pipeline_proof import (
        PipelineExecutionBinding,
        execution_semantics,
        verify_stored_pipeline_proof,
    )

    profile = load_profile(
        Path(config.target_classification.snapshot_manifest),
        config.target_classification.snapshot_manifest_sha256,
        require_acceptance=False,
    )
    canonical, _, _ = render_canonical_target_rows(
        silver.to_pylist(),
        request=CohortExportRequest(
            tmp_path / "synthetic-silver.arrow",
            "a" * 64,
            ARROW_SOURCE_FORMAT,
            NORMALIZED_TARGET_SCHEMA,
            "synthetic-runtime-cohort-only",
            "synthetic-test",
        ),
    )
    provenance = RunProvenance(
        profile.snapshot.snapshot.snapshot_id,
        profile.normalization_version,
        profile.rules_version,
        profile.classification_schema_version,
        profile.snapshot.retrieved_at,
        FIXED_TEST_TIME.isoformat(),
        matching_policy_version=profile.matching_policy_version,
    )
    expected = classify_batch(
        read_bioetl_target_kernel_csv_v1(
            canonical, source_path="synthetic-silver", target_kind="protein"
        ),
        snapshot=profile.snapshot.snapshot,
        provenance=provenance,
        run_id="synthetic-canonical-replay",
    )
    assert (
        verify_stored_pipeline_proof(
            manifest_path,
            profile.snapshot.snapshot_manifest_sha256,
            Path(run_report_json_path),
            provenance,
            expected_execution=tuple(
                PipelineExecutionBinding(
                    raw.input_row_id, raw.fields, execution_semantics(row.result)
                )
                for raw, row in zip(
                    read_bioetl_target_kernel_csv_v1(
                        canonical,
                        source_path="synthetic-silver",
                        target_kind="protein",
                    ),
                    expected.rows,
                    strict=True,
                )
            ),
        )
        == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    )


async def _assert_enrich_blocks_destructive(
    *, factory, config, settings, observability, monkeypatch
):
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.ports import PipelineCreateRunnerRequest
    from bioetl.domain.workflow import WorkflowRunOptionsConfig
    from deltalake import DeltaTable

    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda name: config if name == "chembl_target" else load_pipeline_config(name),
    )
    workflow = WorkflowConfig(
        name="chembl_baseline",
        defaults=WorkflowRunOptionsConfig(run_type="backfill", limit=1000),
        steps=(
            WorkflowStepConfig(step_id="assay", pipeline_name="chembl_assay"),
            WorkflowStepConfig(
                step_id="target",
                pipeline_name="chembl_target",
                depends_on=("assay",),
            ),
        ),
    )
    with pytest.raises(ValueError, match="destructive"):
        preflight_workflow_target_dependencies(workflow, {}, settings=settings)
    destructive = factory.create_runner(
        PipelineCreateRunnerRequest(
            run_id=UUID("8b8f8439-77c7-47b0-a48a-6adaf43fc817"),
            started_at=FIXED_TEST_TIME,
            runtime=RuntimeConfig(run_type=RunType.BACKFILL, limit=1000),
            settings=settings,
            config=config,
            observability=observability,
        )
    )
    with pytest.raises(ValueError, match="destructive"):
        await destructive.run()
    assert (
        DeltaTable(settings.silver_path / "chembl/target").to_pyarrow_table().num_rows
        == 1
    )
    assert (
        DeltaTable(settings.gold_path / "chembl/target").to_pyarrow_table().num_rows
        == 1
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["shadow", "enrich"])
async def test_real_runner_persists_both_layers_and_completes_evidence(
    shadow_config, tmp_path, mode, monkeypatch
):
    """Actual Application runner and Delta writers on explicitly synthetic rows."""
    from deltalake import DeltaTable
    from bioetl.composition.factories.pipeline.assembler import create_pipeline_factory
    from bioetl.composition.factories.pipeline.registry import chembl_target_factory
    from bioetl.domain.config import RuntimeConfig
    from bioetl.domain.ports import PipelineCreateRunnerRequest
    from bioetl.infrastructure.config.settings_api import Settings
    from bioetl.infrastructure.storage.run_report_store_adapter import (
        FileRunReportStoreAdapter,
    )
    from bioetl.application.services.execution.pipeline_runner_service import (
        PipelineRunnerService,
        RunOptions,
    )
    from bioetl.application.services.execution.pipeline_run_context_service import (
        PipelineRunContextService,
    )
    from bioetl.application.services.execution.pipeline_run_execution_service import (
        PipelineRunExecutionService,
    )
    from tests.helpers.clock import FixedClock
    from tests.integration.pipelines.observability import (
        build_test_observability_bundle,
    )

    source = _SyntheticChemblSource()
    config = (
        _admitted_synthetic_config(shadow_config) if mode == "enrich" else shadow_config
    )
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
    observability = build_test_observability_bundle()
    runner = factory.create_runner(
        PipelineCreateRunnerRequest(
            run_id=_context().run_id,
            started_at=FIXED_TEST_TIME,
            runtime=RuntimeConfig(run_type=RunType.INCREMENTAL, limit=1),
            settings=settings,
            config=config,
            observability=observability,
        )
    )
    clock = FixedClock(FIXED_TEST_TIME)
    service = PipelineRunnerService(
        runner_factory=SimpleNamespace(
            contains=lambda _: True, create=lambda _: runner
        ),
        metrics_extractor=SimpleNamespace(
            extract_metrics=lambda current: current.execution_metrics
        ),
        logger=observability.logger,
        metrics=observability.metrics,
        audit=observability.audit,
        clock=clock,
        _context_service=PipelineRunContextService(),
        _execution_service=PipelineRunExecutionService(clock=clock),
        report_store=FileRunReportStoreAdapter(),
        report_root=tmp_path / "actual-run-reports",
    )
    result = await service.run(
        "chembl_target", run_id=_context().run_id, options=RunOptions(limit=1)
    )
    assert result.is_success, result.error_message
    assert runner.execution_metrics["records_silver"] == 1
    assert runner.execution_metrics["records_gold"] == 1
    silver = DeltaTable(settings.silver_path / "chembl/target").to_pyarrow_table()
    gold = DeltaTable(settings.gold_path / "chembl/target").to_pyarrow_table()
    assert silver.num_rows == gold.num_rows == 1
    if mode == "enrich":
        assert silver.column("iuphar_class").to_pylist() == ["Receptor"]
        assert gold.column("iuphar_class").to_pylist() == ["Receptor"]
    else:
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
    assert evidence["input_row_ids"] == ["chembl.target:CHEMBL1"]
    report = json.loads(Path(result.run_report_json_path).read_text())
    if mode == "shadow":
        _assert_shadow_pipeline_proof(
            config=config,
            silver=silver,
            manifest_path=manifest_path,
            run_report_json_path=result.run_report_json_path,
            tmp_path=tmp_path,
        )
    observation = report["observations"]["Target Classification"]
    assert observation["verdict"] == "OK"
    assert observation["facts"]["mode"] == mode
    assert (
        observation["facts"]["profile_sha256"]
        == config.target_classification.snapshot_manifest_sha256
    )
    assert (
        observation["facts"]["evidence_manifest_sha256"]
        == hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    )
    if mode == "enrich":
        await _assert_enrich_blocks_destructive(
            factory=factory,
            config=config,
            settings=settings,
            observability=observability,
            monkeypatch=monkeypatch,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("mode", ["shadow", "enrich"])
@pytest.mark.parametrize(
    "rejection", ["structural_drop", "structural_error", "filter_error", "build_error"]
)
async def test_rejected_target_releases_pending_evidence_across_batches(
    shadow_config, tmp_path, mode, rejection
):
    from dataclasses import replace
    from bioetl.application.core.base_transformer.errors import FilteredOutError

    config = (
        shadow_config if mode == "shadow" else _admitted_synthetic_config(shadow_config)
    )
    transformer = _transformer(config, tmp_path / "rejected")
    session = transformer._target_classification_session
    normalizer = RecordNormalizationProcessor("chembl", "target")

    def reject(*args):
        raise ValueError("rejected fixture row")

    for batch in range(3):
        context = replace(_context(), source_batch_id=f"batch-{batch}")
        payload = await transformer.transform_pre_silver(
            context,
            {
                "target_chembl_id": "CHEMBL1",
                "pref_name": "synthetic target",
                "target_type": "SINGLE PROTEIN",
                "organism": "Homo sapiens",
                "tax_id": 9606,
                "species_group_flag": False,
                "target_components": [],
            },
            0,
        )
        if rejection == "structural_drop":
            payload = replace(payload, apply_structural_policy=lambda *args: None)
            assert normalizer.finalize_pre_silver(payload, context, 0) is None
        elif rejection == "structural_error":
            payload = replace(
                payload,
                business_data={
                    k: v for k, v in payload.business_data.items() if k != "pref_name"
                },
            )
            with pytest.raises(FilteredOutError, match="pref_name"):
                normalizer.finalize_pre_silver(payload, context, 0)
        else:
            callback = (
                "apply_silver_filter"
                if rejection == "filter_error"
                else "build_silver_record"
            )
            payload = replace(payload, **{callback: reject})
            with pytest.raises(ValueError, match="rejected fixture row"):
                normalizer.finalize_pre_silver(payload, context, 0)
        assert session._pending == {}
        assert session._published == {}
    assert not list((tmp_path / "rejected").rglob("*.json"))


@pytest.mark.parametrize("parent_mode", ["off", "shadow"])
def test_exact_replay_keeps_parent_with_current_workflow_binding(
    shadow_config, parent_mode
):
    from bioetl.composition.bootstrap.assembly.target_classification_identity import (
        load_target_aware_pipeline_config,
    )

    off = _legacy_config()
    parent_config = shadow_config if parent_mode == "shadow" else off
    current = off if parent_mode == "shadow" else shadow_config
    token = bind_target_classification_dependency(
        {"target_config": current.model_dump(mode="json")}
    )
    try:
        restored = load_target_aware_pipeline_config(
            "chembl_target",
            lambda _: current,
            lambda _: None,
            ctx=SimpleNamespace(
                pipeline_name="chembl_target",
                exact_replay=True,
                replay_of_manifest_id="parent-manifest",
            ),
            settings=SimpleNamespace(),
            resolve_parent=lambda **kwargs: SimpleNamespace(
                pipeline_name="chembl_target",
                resolved_config=parent_config.model_dump(mode="json"),
            ),
        )
        assert restored.target_classification == parent_config.target_classification
    finally:
        reset_target_classification_dependency(token)


@pytest.mark.parametrize("parent_mode", ["off", "shadow", "enrich"])
def test_workflow_preflight_pins_exact_replay_parent(
    shadow_config, monkeypatch, tmp_path, parent_mode
):
    from bioetl.domain.workflow import WorkflowRunOptionsConfig
    from bioetl.infrastructure.config.settings_api import Settings

    off = _legacy_config()
    parent_config = (
        off
        if parent_mode == "off"
        else shadow_config
        if parent_mode == "shadow"
        else _admitted_synthetic_config(shadow_config)
    )
    current = shadow_config if parent_mode == "off" else off
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda _: current,
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.resolve_replay_parent_manifest",
        lambda **kwargs: SimpleNamespace(
            pipeline_name="chembl_target",
            resolved_config=parent_config.model_dump(mode="json"),
        ),
    )
    workflow = WorkflowConfig(
        "replay",
        steps=(
            WorkflowStepConfig(
                "target",
                "chembl_target",
                run_options=WorkflowRunOptionsConfig(
                    exact_replay=True, replay_of_manifest_id="parent-manifest"
                ),
            ),
        ),
    )
    binding = preflight_workflow_target_dependencies(
        workflow,
        {},
        settings=Settings(test_mode=True, data_dir=tmp_path / "data", _env_file=None),
    )[TARGET_CLASSIFICATION_DEPENDENCY_KEY]
    assert binding["target_config"]["target_classification"]["mode"] == parent_mode
    if parent_mode == "off":
        assert "profile_sha256" not in binding
    else:
        assert (
            binding["profile_sha256"]
            == parent_config.target_classification.snapshot_manifest_sha256
        )
    token = bind_target_classification_dependency(binding)
    try:
        validate_target_runtime_dependency(parent_config, exact_replay=True)
    finally:
        reset_target_classification_dependency(token)


def test_workflow_preflight_rejects_conflicting_replay_dependencies(
    shadow_config, monkeypatch, tmp_path
):
    from bioetl.domain.workflow import WorkflowRunOptionsConfig
    from bioetl.infrastructure.config.settings_api import Settings

    current = load_pipeline_config("chembl_target")
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda _: current,
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.resolve_replay_parent_manifest",
        lambda **kwargs: SimpleNamespace(
            pipeline_name="chembl_target",
            resolved_config=shadow_config.model_dump(mode="json"),
        ),
    )
    workflow = WorkflowConfig(
        "conflict",
        steps=(
            WorkflowStepConfig(
                "replay",
                "chembl_target",
                run_options=WorkflowRunOptionsConfig(
                    exact_replay=True, replay_of_run_id="parent-run"
                ),
            ),
            WorkflowStepConfig("current", "chembl_target"),
        ),
    )
    with pytest.raises(ValueError, match="conflicting classification dependencies"):
        preflight_workflow_target_dependencies(
            workflow,
            {},
            settings=Settings(
                test_mode=True, data_dir=tmp_path / "data", _env_file=None
            ),
        )


@pytest.mark.parametrize(
    "parent_pipeline,payload", [("chembl_assay", {}), ("chembl_target", {})]
)
def test_workflow_preflight_rejects_invalid_target_replay_parent(
    shadow_config, monkeypatch, tmp_path, parent_pipeline, payload
):
    from bioetl.domain.workflow import WorkflowRunOptionsConfig
    from bioetl.infrastructure.config.settings_api import Settings

    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda _: shadow_config,
    )
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.resolve_replay_parent_manifest",
        lambda **kwargs: SimpleNamespace(
            pipeline_name=parent_pipeline, resolved_config=payload
        ),
    )
    workflow = WorkflowConfig(
        "invalid-parent",
        steps=(
            WorkflowStepConfig(
                "replay",
                "chembl_target",
                run_options=WorkflowRunOptionsConfig(
                    exact_replay=True, replay_of_manifest_id="invalid-parent"
                ),
            ),
        ),
    )
    with pytest.raises(ValueError, match="no matching pinned configuration"):
        preflight_workflow_target_dependencies(
            workflow,
            {},
            settings=Settings(
                test_mode=True, data_dir=tmp_path / "data", _env_file=None
            ),
        )


@pytest.mark.parametrize(
    "binding", [{}, {"target_config": None}, {"target_config": []}]
)
def test_workflow_preflight_rejects_malformed_pinned_configuration(
    shadow_config, binding
):
    workflow = WorkflowConfig(
        "malformed", steps=(WorkflowStepConfig("target", "chembl_target"),)
    )
    with pytest.raises(ValueError, match="no configuration"):
        preflight_workflow_target_dependencies(
            workflow, {TARGET_CLASSIFICATION_DEPENDENCY_KEY: binding}
        )
