"""Unit tests for delete_orphans workflow scoping (#10469 T0 / #10515)."""

from __future__ import annotations

import pytest

from bioetl.domain.workflow import (
    TransformStepConfig,
    WorkflowConfig,
    WorkflowRunOptionsConfig,
    WorkflowStepConfig,
)
from bioetl.domain.workflow._delete_orphans_scope import (
    _delete_orphans_transform,
    _limited_upstream_pipeline_ids,
    _record_limited_upstream_dep,
    _require_workflow_config,
    _scope_delete_orphans_step,
    mark_delete_orphans_current_run_scope,
    reject_delete_orphans_after_limited_extracts,
)

pytestmark = pytest.mark.unit


def _pipeline(
    step_id: str, *, limit: int | None = None, depends_on: tuple[str, ...] = ()
) -> WorkflowStepConfig:
    return WorkflowStepConfig(
        step_id=step_id,
        pipeline_name=f"pipe_{step_id}",
        depends_on=depends_on,
        run_options=WorkflowRunOptionsConfig(limit=limit),
    )


def _delete_orphans(
    step_id: str = "reconcile",
    *,
    depends_on: tuple[str, ...] = (),
    action: str = "delete_orphans",
    extra: dict[str, object] | None = None,
) -> TransformStepConfig:
    config: dict[str, object] = {"action": action}
    if extra:
        config.update(extra)
    return TransformStepConfig(
        step_id=step_id,
        transform_name="reconcile_foreign_keys",
        depends_on=depends_on,
        config=config,
    )


def test_require_workflow_config_rejects_non_config() -> None:
    with pytest.raises(TypeError, match="did not preserve WorkflowConfig"):
        _require_workflow_config(object())


def test_delete_orphans_transform_ignores_pipeline_and_other_actions() -> None:
    pipeline = _pipeline("extract")
    assert _delete_orphans_transform(pipeline) is None
    other = TransformStepConfig(
        step_id="rows",
        transform_name="reconcile_rows",
        config={"action": "delete_orphans"},
    )
    assert _delete_orphans_transform(other) is None
    missing_action = TransformStepConfig(
        step_id="fk",
        transform_name="reconcile_foreign_keys",
        config=None,
    )
    assert _delete_orphans_transform(missing_action) is None
    noop = _delete_orphans(action="keep")
    assert _delete_orphans_transform(noop) is None
    matched = _delete_orphans()
    assert _delete_orphans_transform(matched) is matched


def test_record_limited_upstream_skips_seen_and_missing_deps() -> None:
    config = WorkflowConfig(name="wf", steps=(_pipeline("extract"),))
    steps_by_id = {item.step_id: item for item in config.steps}
    seen: set[str] = {"extract"}
    limited: list[str] = []
    stack: list[str] = []
    _record_limited_upstream_dep(
        "extract",
        config=config,
        steps_by_id=steps_by_id,
        seen=seen,
        stack=stack,
        limited=limited,
    )
    assert limited == []
    _record_limited_upstream_dep(
        "missing",
        config=config,
        steps_by_id=steps_by_id,
        seen=seen,
        stack=stack,
        limited=limited,
    )
    assert "missing" in seen
    assert limited == []


def test_limited_upstream_walks_dag_and_ignores_transform_deps() -> None:
    extract = _pipeline("extract", limit=10)
    mid = TransformStepConfig(
        step_id="mid",
        transform_name="reconcile_rows",
        depends_on=("extract",),
    )
    fk = _delete_orphans("fk", depends_on=("mid",))
    config = WorkflowConfig(name="wf", steps=(extract, mid, fk))
    steps_by_id = {item.step_id: item for item in config.steps}
    assert _limited_upstream_pipeline_ids("fk", config, steps_by_id) == ["extract"]


def test_scope_step_is_noop_without_limited_extract() -> None:
    extract = _pipeline("extract")
    fk = _delete_orphans(depends_on=("extract",))
    config = WorkflowConfig(name="wf", steps=(extract, fk))
    steps_by_id = {item.step_id: item for item in config.steps}
    scoped, changed = _scope_delete_orphans_step(fk, config, steps_by_id)
    assert changed is False
    assert scoped is fk


def test_mark_scopes_current_run_when_extract_is_limited() -> None:
    extract = _pipeline("extract", limit=5)
    fk = _delete_orphans(depends_on=("extract",), extra={"source_table": "gold.x"})
    other = TransformStepConfig(
        step_id="rows",
        transform_name="reconcile_rows",
        config={"layer": "gold"},
    )
    config = WorkflowConfig(name="wf", steps=(extract, fk, other))

    marked = mark_delete_orphans_current_run_scope(config)

    assert marked is not config
    scoped = marked.steps[1]
    assert isinstance(scoped, TransformStepConfig)
    assert scoped.config is not None
    assert scoped.config["source_scope"] == "current_run"
    assert scoped.config["source_table"] == "gold.x"
    assert marked.steps[2] is other


def test_mark_returns_same_config_when_nothing_to_scope() -> None:
    extract = _pipeline("extract")
    fk = _delete_orphans(depends_on=("extract",))
    config = WorkflowConfig(name="wf", steps=(extract, fk))
    assert mark_delete_orphans_current_run_scope(config) is config


def test_reject_passes_without_delete_orphans_or_limits() -> None:
    extract = _pipeline("extract")
    rows = TransformStepConfig(
        step_id="rows",
        transform_name="reconcile_rows",
        depends_on=("extract",),
    )
    config = WorkflowConfig(name="wf", steps=(extract, rows))
    reject_delete_orphans_after_limited_extracts(config)

    unlimited_fk = WorkflowConfig(
        name="wf",
        steps=(_pipeline("extract"), _delete_orphans(depends_on=("extract",))),
    )
    reject_delete_orphans_after_limited_extracts(unlimited_fk)


def test_reject_raises_when_limited_extract_feeds_delete_orphans() -> None:
    config = WorkflowConfig(
        name="wf",
        steps=(
            _pipeline("extract", limit=3),
            _delete_orphans(depends_on=("extract",)),
        ),
    )
    with pytest.raises(ValueError, match="run_options.limit"):
        reject_delete_orphans_after_limited_extracts(config)
