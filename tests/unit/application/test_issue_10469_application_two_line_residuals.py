"""Focused branch coverage for small application-layer residuals in #10469."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from bioetl.application.composite.coalesce_policy import CoalescePolicyService
from bioetl.application.composite.column_priority_orderer import (
    resolve_by_column_scan,
    resolve_priority_column,
)
from bioetl.application.composite.conflict_resolver import ConflictResolverService
from bioetl.application.composite.dependency_key_resolvers import (
    SeedKeyResolver,
    _create_key_resolver,
)
from bioetl.application.core.base_transformer.optionality import (
    _collect_dq_fields,
    _collect_nonnullable_key_fields,
)
from bioetl.application.core.batch_metrics import BatchMetricsRecorderService
from bioetl.application.core.batch_tracing import BatchTracingManagerService
from bioetl.application.core.lifecycle.checkpoint_saved_at import (
    set_checkpoint_saved_at,
)
from bioetl.application.core.lifecycle.lock_runtime import validate_lock_ownership
from bioetl.application.core.subcellular_fraction_support import (
    update_fraction_record,
)
from bioetl.application.services.control_plane.manifest.inspection_cross_surface import (
    effective_config_artifact_anchor,
)
from bioetl.application.services.control_plane.workflow.manifest_service import (
    _missing_manifest_id_factory,
)
from bioetl.domain.types import RunID


pytestmark = pytest.mark.unit


def test_column_priority_helpers_cover_absent_and_seed_provider_paths() -> None:
    assert (
        resolve_by_column_scan(
            provider="chembl", field="id", columns_set={"other.entity.id"}
        )
        is None
    )
    assert (
        resolve_priority_column(
            source="CHEMBL",
            field="id",
            columns_set=set(),
            seed_provider="chembl",
            seed_entity="activity",
        )
        == "chembl.activity.id"
    )


def test_coalesce_alias_and_single_column_timestamp_path() -> None:
    service = CoalescePolicyService(logger=MagicMock())
    frame = pl.DataFrame({"chembl.activity.id": ["A"]})

    assert service.coalesce_first_non_null(frame, ()) is frame
    assert service.coalesce_prefer_latest_timestamp(frame, ()) is frame


def test_conflict_resolver_unknown_policy_has_no_handler() -> None:
    service = ConflictResolverService(
        merge_config=SimpleNamespace(conflict_resolution="unknown"),
        logger=MagicMock(),
        coalesce_policy=MagicMock(),
    )

    assert (
        service._resolve_policy_handler(
            df=pl.DataFrame({"id": [1]}), enrichers=(), seed_pipeline=None
        )
        is None
    )


def test_generic_key_resolver_factory_builds_requested_type() -> None:
    resolver = _create_key_resolver(SeedKeyResolver, MagicMock(), normalization_policies={})

    assert isinstance(resolver, SeedKeyResolver)


def test_optionality_collectors_ignore_blank_and_nullable_rules() -> None:
    domain_config = SimpleNamespace(
        dq=SimpleNamespace(
            field_validations=(
                SimpleNamespace(field="", validation_type="required"),
                SimpleNamespace(field="title", validation_type="required"),
            ),
            key_nullability_rules=(
                SimpleNamespace(field="optional_id", nullable=True),
                SimpleNamespace(field="entity_id", nullable=False),
            ),
        )
    )

    assert _collect_dq_fields(domain_config, validation_type="required") == {
        "title"
    }
    assert _collect_nonnullable_key_fields(domain_config) == {"entity_id"}


def test_checkpoint_metric_ignores_non_numeric_timestamp() -> None:
    metrics = MagicMock()

    set_checkpoint_saved_at(
        metrics,
        pipeline_name="chembl_activity",
        checkpoint_saved_at_epoch_seconds="not-a-number",
    )

    metrics.set_gauge.assert_not_called()


@pytest.mark.asyncio
async def test_lock_validation_without_fencing_token_uses_owner() -> None:
    lock_port = MagicMock()
    lock_port.validate_owner = AsyncMock(return_value=True)

    assert await validate_lock_ownership(
        lock_port=lock_port,
        config=SimpleNamespace(lock_key="pipeline:test"),
        run_id=RunID("run-1"),
        fencing_token=None,
    )


def test_fraction_update_populates_first_example_assay() -> None:
    record = {"assay_count": 1, "example_assay_id": None}

    update_fraction_record(record, {"assay_chembl_id": " CHEMBL1 "})

    assert record == {"assay_count": 2, "example_assay_id": "CHEMBL1"}


def test_batch_tracing_none_result_spans_are_noops() -> None:
    service = BatchTracingManagerService(
        tracer=MagicMock(),
        context=MagicMock(),
        config=MagicMock(),
        initial_batch_size=100,
        adaptive_sizing_enabled=False,
    )

    assert (
        service.set_batch_result(
            None,
            bronze_count=0,
            silver_count=0,
            gold_count=0,
            quarantined_count=0,
        )
        is None
    )
    assert (
        service.set_transform_result(
            None,
            silver_count=0,
            gold_count=0,
            quarantined_count=0,
        )
        is None
    )


def test_fetched_metrics_update_bound_stage_accounting(monkeypatch: pytest.MonkeyPatch) -> None:
    accounting = MagicMock()
    monkeypatch.setattr(
        "bioetl.application.core.batch_metrics.get_stage_accounting",
        lambda: accounting,
    )
    recorder = BatchMetricsRecorderService(
        metrics=None,
        pipeline_label="chembl_activity",
        run_type_label="incremental",
    )

    recorder.track_records_fetched(3)

    accounting.record_in.assert_called_once_with("extract", 3)
    accounting.mark_instrumented.assert_called_once_with("extract")


def test_effective_config_anchor_accepts_flat_artifact_payload() -> None:
    assert effective_config_artifact_anchor(
        {"artifact_id": "artifact-1", "effective_config_hash": "sha256:config"}
    ) == {
        "artifact_id": "artifact-1",
        "effective_config_hash": "sha256:config",
    }


def test_missing_workflow_manifest_id_factory_fails_closed() -> None:
    with pytest.raises(RuntimeError, match="must be supplied"):
        _missing_manifest_id_factory()
