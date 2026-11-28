"""Pending workflow admission against real physical target tables."""

from __future__ import annotations

import hashlib
import asyncio
from dataclasses import replace
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pyarrow as pa
import pytest
from deltalake import DeltaTable, write_deltalake

from bioetl.application.services.workflow.control_plane.execution_service import (
    WorkflowExecutionService,
)
from bioetl.application.services.workflow.control_plane.mutation_plan import (
    WorkflowMutationSpec,
    build_workflow_mutation_plan,
)
from bioetl.composition.runtime_builders.config_access import load_pipeline_config
from bioetl.composition.bootstrap.assembly.storage import (
    preflight_workflow_target_dependencies,
)
from bioetl.composition.bootstrap.cli.lock import (
    validate_workflow_target_mutations,
)
from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.control_plane import WorkflowExecutionState, WorkflowStepState
from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
    WorkflowTransformSpec,
)
from bioetl.domain.workflow.config import WorkflowReferenceCohort
from bioetl.domain.workflow.foreign_key_reconciliation_models import (
    ForeignKeyReconciliationRequest,
)
from bioetl.infrastructure.config.settings_api import Settings
from bioetl.infrastructure.storage.workflow_foreign_key_reconciliation import (
    StorageForeignKeyReconciliationAdapter,
)
from tests.helpers.clock import FIXED_TEST_TIME

pytestmark = pytest.mark.unit


@pytest.fixture
def physical_target(tmp_path):
    """Schema detection fixture only; no reference/scientific admission receipt."""
    settings = Settings(test_mode=True, data_dir=tmp_path / "data", _env_file=None)
    schema = pa.schema(
        [
            pa.field("target_id", pa.string()),
            *[pa.field(name, pa.string()) for name in TARGET_CLASSIFICATION_FIELDS],
        ]
    )
    rows = [
        {
            "target_id": value,
            **dict.fromkeys(TARGET_CLASSIFICATION_FIELDS, "physical-fixture"),
        }
        for value in ("CHEMBL1", "CHEMBL2")
    ]
    for root in (settings.silver_path, settings.gold_path):
        write_deltalake(
            str(root / "chembl/target"), pa.Table.from_pylist(rows, schema=schema)
        )
    write_deltalake(
        str(settings.gold_path / "chembl/assay"),
        pa.table({"assay_id": ["A1", "A2"], "target_id": ["CHEMBL1", "CHEMBL2"]}),
    )
    return settings


def _physical_hashes(settings):
    return {
        path.relative_to(settings.data_dir).as_posix(): hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
        for path in settings.data_dir.rglob("*")
        if path.is_file()
    }


def _target_config(mode="off"):
    config = load_pipeline_config("chembl_target")
    return config.model_copy(
        update={
            "target_classification": config.target_classification.model_copy(
                update={
                    "mode": mode,
                    "table_contract": None,
                    "snapshot_manifest": "not-admitted.json"
                    if mode == "enrich"
                    else None,
                    "snapshot_manifest_sha256": "a" * 64 if mode == "enrich" else None,
                }
            )
        }
    )


def _fk(
    *,
    source="chembl.target",
    reference="chembl.assay",
    mode="complete-reference",
    closed=True,
    depends_on=(),
):
    return TransformStepConfig(
        step_id="reconcile",
        transform_name="reconcile_foreign_keys",
        depends_on=depends_on,
        config={
            "source_table": source,
            "reference_table": reference,
            "source_layer": "gold",
            "reference_layer": "gold",
            "mutation_layer": "gold",
            "action": "delete_orphans",
            "primary_keys": ["target_id"],
            "source_key": "target_id",
            "reference_key": "target_id",
            "require_closed_cohort": closed,
            "reconciliation_mode": mode,
            "source_scope": "current_run"
            if mode == "selected-snapshot"
            else "all_current",
        },
    )


def _workflow():
    return WorkflowConfig(
        "baseline",
        steps=(
            WorkflowStepConfig(
                "assay",
                "chembl_assay",
                run_options=WorkflowRunOptionsConfig(run_type="backfill", limit=1000),
            ),
            WorkflowStepConfig(
                "target",
                "chembl_target",
                depends_on=("assay",),
                run_options=WorkflowRunOptionsConfig(run_type="incremental"),
                reference_cohort=WorkflowReferenceCohort(
                    "assay", "chembl.assay", "target_id", "target_id"
                ),
            ),
        ),
    )


def _state(config, *, successful=(), completed_transforms=None):
    return WorkflowExecutionState(
        workflow_run_id=UUID("f8b62cb0-0846-4418-89db-a980138d2d55"),
        manifest_id="manifest",
        workflow_name=config.name,
        execution_fingerprint="fingerprint",
        status="failed",
        started_at=FIXED_TEST_TIME,
        updated_at=FIXED_TEST_TIME,
        completed_at=None,
        selected_step_ids=config.step_ids,
        steps=tuple(
            WorkflowStepState(
                step.step_id,
                "pipeline" if isinstance(step, WorkflowStepConfig) else "transform",
                "success" if step.step_id in successful else "pending",
            )
            for step in config.steps
        ),
        completed_transform_fingerprints=completed_transforms or {},
    )


def test_pending_plan_matches_resume_selectors_and_transform_fingerprints():
    transform = _fk(depends_on=("target",))
    config = replace(_workflow(), steps=(*_workflow().steps, transform))
    state = _state(
        config,
        successful=("assay", "target"),
        completed_transforms={
            "reconcile": WorkflowTransformSpec.from_step(transform).fingerprint
        },
    )
    assert not build_workflow_mutation_plan(config, state).pending_step_ids
    assert build_workflow_mutation_plan(
        config, state, force_steps=("target",)
    ).pending_step_ids == {"target"}
    assert build_workflow_mutation_plan(
        config, state, repair_steps=("reconcile",)
    ).pending_step_ids == {"reconcile"}


def test_bounded_upstream_refused_without_touching_actual_delta(physical_target):
    before = _physical_hashes(physical_target)
    config = _workflow()
    with pytest.raises(ValueError, match="bounded destructive upstream"):
        validate_workflow_target_mutations(
            config,
            _target_config("enrich"),
            physical_target,
            build_workflow_mutation_plan(config),
            load_pipeline_config,
        )
    assert _physical_hashes(physical_target) == before
    assert (
        DeltaTable(str(physical_target.gold_path / "chembl/assay"))
        .to_pyarrow_table()
        .num_rows
        == 2
    )


@pytest.mark.asyncio
async def test_bounded_upstream_fails_before_assay_or_manifest_write(
    physical_target, monkeypatch
):
    target = _target_config("enrich")
    original_loader = load_pipeline_config
    monkeypatch.setattr(
        "bioetl.composition.bootstrap.assembly.storage.load_pipeline_config",
        lambda name: target if name == "chembl_target" else original_loader(name),
    )
    runner = SimpleNamespace(run_workflow=AsyncMock())
    manifests = MagicMock()
    service = WorkflowExecutionService(
        workflow_runner=runner,
        manifest_service=manifests,
        workflow_ledger_port=MagicMock(),
        workflow_ledger_factory=MagicMock(),
        workflow_state_port=MagicMock(),
        workflow_lock_port=SimpleNamespace(
            acquire=AsyncMock(return_value="lock"), release=AsyncMock()
        ),
        now_factory=lambda: FIXED_TEST_TIME,
        run_id_factory=lambda: UUID("ab42b91c-7b99-456e-9ede-199944724c1d"),
        dependency_preflight=lambda config, context, plan: (
            preflight_workflow_target_dependencies(
                config, context, plan, settings=physical_target
            )
        ),
    )
    before = _physical_hashes(physical_target)
    with pytest.raises(ValueError, match="bounded destructive upstream"):
        await service.run_workflow(_workflow())
    runner.run_workflow.assert_not_awaited()
    assert not manifests.mock_calls
    assert _physical_hashes(physical_target) == before


def test_completed_destructive_steps_do_not_block_readonly_resume(physical_target):
    config = replace(
        _workflow(),
        steps=(
            *_workflow().steps,
            TransformStepConfig(
                "summary", "summarize_upstream_outputs", depends_on=("target",)
            ),
        ),
    )
    state = _state(config, successful=("assay", "target"))
    admission = validate_workflow_target_mutations(
        config,
        _target_config("enrich"),
        physical_target,
        build_workflow_mutation_plan(config, state),
        load_pipeline_config,
    )
    assert admission.required and not admission.pending_writes
    with pytest.raises(ValueError, match="bounded destructive upstream"):
        validate_workflow_target_mutations(
            config,
            _target_config("enrich"),
            physical_target,
            build_workflow_mutation_plan(config, state, force_steps=("assay",)),
            load_pipeline_config,
        )


def test_fk_reference_read_and_closed_cohort_verification_are_legal(physical_target):
    before = _physical_hashes(physical_target)
    reference_only = WorkflowConfig(
        "read", steps=(_fk(source="chembl.assay", reference="chembl.target"),)
    )
    admission = validate_workflow_target_mutations(
        reference_only,
        _target_config(),
        physical_target,
        build_workflow_mutation_plan(reference_only),
        load_pipeline_config,
    )
    assert not admission.required
    verify = WorkflowConfig("verify", steps=(_fk(),))
    admission = validate_workflow_target_mutations(
        verify,
        _target_config(),
        physical_target,
        build_workflow_mutation_plan(verify),
        load_pipeline_config,
    )
    assert admission.required and not admission.pending_writes
    assert _physical_hashes(physical_target) == before


def test_transform_only_writer_cannot_bypass_profile_compatibility(physical_target):
    config = WorkflowConfig("mutate", steps=(_fk(closed=False),))
    before = _physical_hashes(physical_target)
    with pytest.raises(ValueError, match="rollback"):
        validate_workflow_target_mutations(
            config,
            _target_config(),
            physical_target,
            build_workflow_mutation_plan(config),
            load_pipeline_config,
        )
    assert _physical_hashes(physical_target) == before


def test_scoped_selected_snapshot_requires_both_declared_producers(physical_target):
    config = WorkflowConfig(
        "scoped",
        steps=(
            WorkflowStepConfig("assay", "chembl_assay"),
            WorkflowStepConfig("target", "chembl_target"),
            _fk(mode="selected-snapshot", closed=False, depends_on=("assay", "target")),
        ),
    )
    plan = WorkflowMutationSpec(frozenset({"reconcile"}), resumed=True)
    assert validate_workflow_target_mutations(
        config, _target_config("enrich"), physical_target, plan, load_pipeline_config
    ).pending_writes
    unbound = WorkflowConfig(
        "unbound", steps=(_fk(mode="selected-snapshot", closed=False),)
    )
    with pytest.raises(ValueError, match="both bound workflow producers"):
        validate_workflow_target_mutations(
            unbound,
            _target_config("enrich"),
            physical_target,
            build_workflow_mutation_plan(unbound),
            load_pipeline_config,
        )


def test_dry_run_and_nonmutating_transform_do_not_request_write_admission(
    physical_target,
):
    config = replace(_workflow(), defaults=WorkflowRunOptionsConfig(dry_run=True))
    assert not validate_workflow_target_mutations(
        config,
        _target_config(),
        physical_target,
        build_workflow_mutation_plan(config),
        load_pipeline_config,
    ).pending_writes


def test_unrelated_bounded_ancestor_does_not_block_target_incremental(physical_target):
    workflow = _workflow()
    target = replace(workflow.steps[1], reference_cohort=None)
    config = replace(workflow, steps=(workflow.steps[0], target))
    assert validate_workflow_target_mutations(
        config,
        _target_config("enrich"),
        physical_target,
        build_workflow_mutation_plan(config),
        load_pipeline_config,
    ).pending_writes


def test_future_pipeline_alias_cannot_write_existing_v31_destinations(physical_target):
    config = WorkflowConfig(
        "alias", steps=(WorkflowStepConfig("future", "future_target_writer"),)
    )
    target = _target_config("enrich")
    with pytest.raises(ValueError, match="unclassified writer"):
        validate_workflow_target_mutations(
            config,
            target,
            physical_target,
            build_workflow_mutation_plan(config),
            lambda _: target,
        )


def test_undeclared_target_transform_mutation_is_refused(physical_target):
    transform = replace(_fk(), transform_name="future_custom_mutation")
    config = WorkflowConfig("unknown", steps=(transform,))
    with pytest.raises(ValueError, match="declared supported workflow transform"):
        validate_workflow_target_mutations(
            config,
            _target_config("enrich"),
            physical_target,
            build_workflow_mutation_plan(config),
            load_pipeline_config,
        )


@pytest.mark.parametrize(
    "options",
    [
        WorkflowRunOptionsConfig(use_cached_bronze=True),
        WorkflowRunOptionsConfig(input_csv="subset.csv"),
        WorkflowRunOptionsConfig(start_offset=1000),
    ],
)
def test_bounded_upstream_routes_do_not_depend_on_limit(physical_target, options):
    config = _workflow()
    config = replace(
        config,
        steps=(
            replace(config.steps[0], run_options=replace(options, run_type="backfill")),
            config.steps[1],
        ),
    )
    with pytest.raises(ValueError, match="bounded destructive upstream"):
        validate_workflow_target_mutations(
            config,
            _target_config("enrich"),
            physical_target,
            build_workflow_mutation_plan(config),
            load_pipeline_config,
        )


@pytest.mark.parametrize("ignore_yaml", [False, True])
def test_yaml_subset_is_bounded_unless_explicitly_ignored(physical_target, ignore_yaml):
    config = _workflow()
    config = replace(
        config,
        steps=(
            replace(
                config.steps[0],
                run_options=WorkflowRunOptionsConfig(
                    run_type="backfill", ignore_yaml_filter=ignore_yaml
                ),
            ),
            config.steps[1],
        ),
    )
    assay = load_pipeline_config("chembl_assay")
    assay = assay.model_copy(
        update={"input_filter": assay.input_filter.model_copy(update={"enabled": True})}
    )

    def loader(name):
        return assay if name == "chembl_assay" else load_pipeline_config(name)

    if ignore_yaml:
        assert validate_workflow_target_mutations(
            config,
            _target_config("enrich"),
            physical_target,
            build_workflow_mutation_plan(config),
            loader,
        ).pending_writes
    else:
        with pytest.raises(ValueError, match="bounded destructive upstream"):
            validate_workflow_target_mutations(
                config,
                _target_config("enrich"),
                physical_target,
                build_workflow_mutation_plan(config),
                loader,
            )


class _ReconciliationWriter:
    def __init__(self, root):
        self.root = root

    def _resolve_table_path(self, name):
        return str(self.root / name.replace(".", "/"))

    async def _run_in_executor(self, fn, *args):
        return await asyncio.to_thread(fn, *args)

    async def read_gold(self, name, columns=None, current_only=True):
        rows = DeltaTable(self._resolve_table_path(name)).to_pyarrow_table().to_pylist()
        return [row for row in rows if not current_only or row["_is_current"]]


@pytest.mark.asyncio
async def test_admitted_scoped_fk_preserves_unrelated_and_historical_target_rows(
    physical_target,
):
    """Exercise the owning FK adapter after the same physical workflow admission."""

    def row(target, run, current=True):
        return {
            "target_id": target,
            "_run_id": run,
            "_is_current": current,
            "_valid_to": "",
            **dict.fromkeys(TARGET_CLASSIFICATION_FIELDS, "fixture"),
        }

    rows = [
        row("CHEMBL1", "producer"),
        row("CHEMBL2", "history"),
        row("CHEMBL1", "history", False),
    ]
    gold = _ReconciliationWriter(physical_target.gold_path)
    write_deltalake(
        str(physical_target.silver_path / "chembl/target"),
        pa.Table.from_pylist(rows),
        mode="overwrite",
        schema_mode="overwrite",
    )
    write_deltalake(
        gold._resolve_table_path("chembl.target"),
        pa.Table.from_pylist(rows),
        mode="overwrite",
        schema_mode="overwrite",
    )
    write_deltalake(
        gold._resolve_table_path("chembl.assay"),
        pa.table(
            {
                "assay_id": ["unrelated"],
                "target_id": ["CHEMBL2"],
                "_run_id": ["producer"],
            }
        ),
        mode="overwrite",
        schema_mode="overwrite",
    )
    storage = StorageForeignKeyReconciliationAdapter(
        silver_writer=_ReconciliationWriter(physical_target.silver_path),
        gold_writer=gold,
        logger=MagicMock(),
        clock=SimpleNamespace(now=lambda: FIXED_TEST_TIME),
        quarantine=SimpleNamespace(write_many=AsyncMock()),
    )
    snapshots = await storage.capture_pipeline_snapshots("chembl_target", "producer")
    snapshots.update(
        await storage.capture_pipeline_snapshots("chembl_assay", "producer")
    )
    config = WorkflowConfig(
        "scoped",
        steps=(
            WorkflowStepConfig("target", "chembl_target"),
            WorkflowStepConfig("assay", "chembl_assay"),
            _fk(mode="selected-snapshot", closed=False, depends_on=("target", "assay")),
        ),
    )
    plan = WorkflowMutationSpec(frozenset({"reconcile"}), resumed=True)
    assert validate_workflow_target_mutations(
        config, _target_config("enrich"), physical_target, plan, load_pipeline_config
    ).pending_writes
    result = await storage.reconcile_foreign_keys(
        ForeignKeyReconciliationRequest(
            source_table="chembl.target",
            reference_table="chembl.assay",
            source_key="target_id",
            reference_key="target_id",
            primary_keys=("target_id",),
            source_layer="gold",
            reference_layer="gold",
            source_scope="current_run",
            source_run_ids=("producer",),
            workflow_run_id="ab42b91c-7b99-456e-9ede-199944724c1d",
            reconciliation_mode="selected-snapshot",
            selected_snapshots=snapshots,
        )
    )
    assert result.scanned_rows == result.orphan_rows_deleted == 1
    actual = (
        DeltaTable(gold._resolve_table_path("chembl.target"))
        .to_pyarrow_table()
        .to_pylist()
    )
    assert sorted(
        [item for item in actual if item["_run_id"] == "history"],
        key=lambda item: item["target_id"],
    ) == sorted(rows[1:], key=lambda item: item["target_id"])
    assert len(actual) == 3
    assert not next(item for item in actual if item["_run_id"] == "producer")[
        "_is_current"
    ]
