# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for lineage persistence helpers."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, call

import pytest

from bioetl.application.services.lineage import MetadataLineageBundleResult
from bioetl.domain.lineage import LineageGraphFragment
from bioetl.infrastructure.storage.lineage_persistence import (
    emit_composite_source_selection_metrics,
    emit_lineage_refs_missing_metric,
    persist_lineage_fragment_if_present,
    resolve_metadata_and_lineage_fragment,
)
from tests.unit.infrastructure.storage._lineage_fragment_helpers import (
    make_produced_artifact_fragment,
)


class _CoordinatorWithBundle:
    def __init__(self, metadata: object, fragment: LineageGraphFragment) -> None:
        self._metadata = metadata
        self._fragment = fragment

    def create_silver_metadata_bundle(
        self, input_data: object
    ) -> MetadataLineageBundleResult:
        _ = input_data
        return MetadataLineageBundleResult(
            metadata=self._metadata,
            lineage_fragment=self._fragment,
        )

    def create_silver_metadata(self, input_data: object) -> object:
        _ = input_data
        return self._metadata


class _MetadataStub:
    def __init__(self) -> None:
        self.runtime = SimpleNamespace(run_id="run-123", manifest_id=None)
        self.output = SimpleNamespace(lineage_fragment_id=None, artifact_id=None)


@pytest.mark.unit
def test_resolve_metadata_and_lineage_fragment_prefers_bundle_method() -> None:
    metadata = _MetadataStub()
    fragment = make_produced_artifact_fragment(
        fragment_id="silver:fragment-1",
        layer="silver",
        logical_name="test.dataset",
    )
    coordinator = _CoordinatorWithBundle(metadata=metadata, fragment=fragment)

    resolved_metadata, resolved_fragment = resolve_metadata_and_lineage_fragment(
        coordinator=coordinator,
        bundle_factory_name="create_silver_metadata_bundle",
        coordinator_factory_name="create_silver_metadata",
        input_data=object(),
        fallback_factory=MagicMock(return_value=MagicMock()),
    )

    assert resolved_metadata is metadata
    assert resolved_fragment == fragment
    assert metadata.output.lineage_fragment_id == "silver:fragment-1"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_lineage_fragment_if_present_calls_store() -> None:
    fragment = make_produced_artifact_fragment(
        fragment_id="gold:fragment-1",
        layer="gold",
        logical_name="test.dataset",
    )
    store = MagicMock()

    await persist_lineage_fragment_if_present(
        lineage_store=store,
        lineage_fragment=fragment,
    )

    store.save.assert_called_once_with(fragment)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_persist_lineage_fragment_if_present_emits_metric() -> None:
    fragment = make_produced_artifact_fragment(
        fragment_id="silver:fragment-1",
        layer="silver",
        logical_name="test.dataset",
    )
    store = MagicMock()
    metrics = MagicMock()

    await persist_lineage_fragment_if_present(
        lineage_store=store,
        lineage_fragment=fragment,
        metrics=metrics,
        pipeline_name="chembl_activity",
        layer="silver",
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_lineage_fragments_emitted_total",
        1,
        {
            "pipeline": "chembl_activity",
            "layer": "silver",
            "status": "success",
        },
    )


@pytest.mark.unit
def test_emit_lineage_refs_missing_metric_uses_expected_labels() -> None:
    metrics = MagicMock()

    emit_lineage_refs_missing_metric(
        metrics,
        pipeline_name="chembl_activity",
        layer="silver",
        ref_type="bronze_batch",
    )

    metrics.increment_counter.assert_called_once_with(
        "bioetl_lineage_refs_missing_total",
        1,
        {
            "pipeline": "chembl_activity",
            "layer": "silver",
            "ref_type": "bronze_batch",
        },
    )


@pytest.mark.unit
def test_emit_composite_source_selection_metrics_aggregates_sources_and_fields() -> (
    None
):
    metrics = MagicMock()
    records = [
        {
            "_source_providers": ["chembl", "pubchem"],
            "_field_sources": {"title": "chembl", "score": "pubchem"},
        },
        {
            "_source_providers": ["chembl"],
            "_field_sources": {"summary": "chembl"},
        },
    ]

    emit_composite_source_selection_metrics(
        metrics,
        pipeline_name="composite_publication",
        layer="silver",
        sources_used=["openalex"],
        records=records,
    )

    metrics.increment_counter.assert_has_calls(
        [
            call(
                "bioetl_composite_source_selection_total",
                1,
                {
                    "pipeline": "composite_publication",
                    "decision_type": "silver_source_included",
                    "selected_source": "chembl",
                },
            ),
            call(
                "bioetl_composite_source_selection_total",
                1,
                {
                    "pipeline": "composite_publication",
                    "decision_type": "silver_source_included",
                    "selected_source": "openalex",
                },
            ),
            call(
                "bioetl_composite_source_selection_total",
                1,
                {
                    "pipeline": "composite_publication",
                    "decision_type": "silver_source_included",
                    "selected_source": "pubchem",
                },
            ),
            call(
                "bioetl_composite_source_selection_total",
                2,
                {
                    "pipeline": "composite_publication",
                    "decision_type": "silver_field_selected",
                    "selected_source": "chembl",
                },
            ),
            call(
                "bioetl_composite_source_selection_total",
                1,
                {
                    "pipeline": "composite_publication",
                    "decision_type": "silver_field_selected",
                    "selected_source": "pubchem",
                },
            ),
        ],
        any_order=False,
    )
