"""CodeRabbit residuals for domain validation (#11224)."""

from __future__ import annotations

import pytest

from bioetl.domain._observability_contract_primitives import normalize_severity
from bioetl.domain.behavior.aggregation_validation_helpers import build_group_key
from bioetl.domain.behavior.merged_metadata_explainability import (
    MergedMetadataExplainer,
)
from bioetl.domain.behavior.validation_helpers import aggregation_group_key
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from tests.helpers.deterministic_ids import deterministic_batch_uuid_from_callsite

pytestmark = pytest.mark.unit


def test_aggregation_group_key_matches_build_group_key() -> None:
    record = {"group": {"b": 1, "a": 2}, "missing": None}
    fields = ["group", "absent", "missing"]
    assert aggregation_group_key(record, fields) == build_group_key(record, fields)


def test_merged_explainability_summary_delegates_to_composite_cv() -> None:
    explainer = MergedMetadataExplainer()
    summary = explainer.generate_explainability_summary([])
    assert summary["record_count"] == 0
    assert summary["conflict_summary"]["records_with_conflicts"] == 0


def test_bronze_result_short_path_requires_table_identity() -> None:
    batch_id = deterministic_batch_uuid_from_callsite("test_issue_11224_bronze")
    with pytest.raises(ValueError, match="provider/entity"):
        BronzeWriteResult(
            batch_id=batch_id,
            relative_path="batch.jsonl.zst",
            absolute_path="/data/bronze/batch.jsonl.zst",
            record_count=1,
            compressed_size=1,
            uncompressed_size=1,
            checksum_blake2="abc",
        )


def test_normalize_severity_exception_alias_maps_to_error() -> None:
    assert normalize_severity("exception", fallback="info") == "error"
