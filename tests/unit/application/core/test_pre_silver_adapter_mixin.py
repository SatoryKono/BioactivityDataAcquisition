"""Unit tests for shared staged PreSilver adapter helpers."""

from __future__ import annotations

from unittest.mock import MagicMock
from tests.helpers.deterministic_ids import deterministic_uuid_from_callsite

import pytest

from bioetl.application.core.pre_silver_adapter_mixin import PreSilverAdapterMixin
from bioetl.application.core.pre_silver_record import PreSilverRecord
from bioetl.domain.context import PipelineContext
from bioetl.domain.types import RunType


class _DummyTransformer(PreSilverAdapterMixin):
    provider = "crossref"
    entity_type = "publication"

    def __init__(self) -> None:
        self.hash_inputs: list[dict[str, object]] = []
        self.filtered_records: list[dict[str, object]] = []

    def compute_content_hash(
        self,
        business_data: dict[str, object],
        *,
        exclude_none: bool = True,
    ) -> str:
        del exclude_none
        self.hash_inputs.append(dict(business_data))
        return "hash-123"

    def _build_pre_silver_record(
        self,
        context: PipelineContext,
        entity_id: str,
        content_hash: str,
        index: int,
        business_data: dict[str, object],
    ) -> dict[str, object]:
        return {
            "entity_id": entity_id,
            "content_hash": content_hash,
            "_run_id": str(context.run_id),
            "_index": index,
            **business_data,
        }

    def _apply_structural_policy(
        self,
        context: PipelineContext,
        record: dict[str, object],
        index: int,
    ) -> dict[str, object] | None:
        del context, index
        return {**record, "structural_policy": "applied"}

    def _apply_silver_filter(
        self,
        context: PipelineContext,
        record: dict[str, object],
        index: int,
    ) -> None:
        del context, index
        self.filtered_records.append(dict(record))


@pytest.fixture
def pipeline_context() -> PipelineContext:
    logger = MagicMock()
    logger.bind = MagicMock(return_value=logger)
    return PipelineContext(
        run_id=deterministic_uuid_from_callsite("test_pre_silver_adapter_mixin"),
        run_type=RunType.INCREMENTAL,
        logger=logger,
    )


@pytest.mark.unit
def test_build_pre_silver_payload_returns_protocol_ready_record() -> None:
    transformer = _DummyTransformer()

    payload = transformer._build_pre_silver_payload(
        entity_id="crossref:1",
        business_data={"publication_doi": "10.1000/test"},
    )

    assert isinstance(payload, PreSilverRecord)
    assert payload.entity_id == "crossref:1"
    assert payload.business_data["publication_doi"] == "10.1000/test"
    assert payload.build_silver_record == transformer._build_pre_silver_json_record
    assert payload.apply_structural_policy == (
        transformer._apply_pre_silver_structural_policy
    )
    assert payload.apply_silver_filter == transformer._apply_pre_silver_filter


@pytest.mark.unit
def test_finalize_staged_business_data_normalizes_hashes_and_projects_findings(
    pipeline_context: PipelineContext,
) -> None:
    transformer = _DummyTransformer()

    result = transformer._finalize_staged_business_data(
        context=pipeline_context,
        entity_id="crossref:1",
        index=7,
        business_data={
            "publication_doi": " HTTPS://doi.org/10.1000/ABC ",
            "title": "  Example <b>Title</b>  ",
        },
    )

    assert transformer.hash_inputs == [
        {
            "publication_doi": "10.1000/abc",
            "title": "Example Title",
        }
    ]
    assert result["entity_id"] == "crossref:1"
    assert result["content_hash"] == "hash-123"
    assert result["publication_doi"] == "10.1000/abc"
    assert result["title"] == "Example Title"
    assert result["_index"] == 7
    assert result["_run_id"] == str(pipeline_context.run_id)
