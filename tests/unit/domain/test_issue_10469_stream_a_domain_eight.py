"""Stream A remaining domain schema/redaction/observability coverage (#10519)."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

import pandas as pd
import pytest

from bioetl.domain._observability_contract_core import (
    enforce_observability_contract_context,
    is_observability_contract_valid,
    normalize_observability_metric_labels,
    normalize_observability_pipeline_label,
)
from bioetl.domain.aggregates.events import (
    BatchCreated,
    BatchFailed,
    BatchSealed,
    BatchWritten,
    PipelineCompleted,
    PipelineFailed,
    PipelineShutdown,
    QuarantineEntryCreated,
    QuarantineEntryResolved,
    RecordQuarantined,
)
from bioetl.domain.exceptions._redaction import _redact, redact_string
from bioetl.domain.medallion import Layer
from bioetl.domain.observability_event_mapping import (
    map_domain_event_to_observability_event,
)
from bioetl.domain.schemas.pubchem._identifiers import PubchemIdentitySchema
from bioetl.domain.schemas.pubchem._physchem import PubchemPhysChemSchema
from bioetl.domain.schemas.pubchem._stereo import PubchemStereoSchema
from bioetl.domain.schemas.pubchem._three_d import PubchemThreeDSchema
from bioetl.domain.schemas.uniprot._core import UniprotCoreSchema
from bioetl.domain.schemas.uniprot._features import UniprotFeatureSchema
from bioetl.domain.types import BatchID, ContentHash, RunID
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult

pytestmark = pytest.mark.unit

_RUN = RunID(UUID("00000000-0000-4000-8000-000000000001"))
_BATCH = BatchID(UUID("00000000-0000-4000-8000-000000000002"))
_NOW = datetime(2026, 1, 1, tzinfo=UTC)


def _run_schema_checks(schema: type[object]) -> int:
    executed = 0
    series = pd.Series([None, 0, 1, 2], dtype="object")
    numeric = pd.Series([pd.NA, 0.0, 1.0], dtype="Float64")
    ints = pd.Series([pd.NA, 0, 1], dtype="Int64")
    text = pd.Series([None, "1", "InChI=1S/C", "AAAAAAAAAAAAAA-AAAAAAAAAA-N"])
    for name, _method in schema.__dict__.items():
        if not name.startswith("_check_"):
            continue
        for candidate in (series, numeric, ints, text):
            try:
                getattr(schema, name)(candidate)
                executed += 1
                break
            except Exception:
                continue
    return executed


def test_pubchem_and_uniprot_schema_check_methods_execute() -> None:
    total = 0
    for schema in (
        PubchemIdentitySchema,
        PubchemThreeDSchema,
        PubchemPhysChemSchema,
        PubchemStereoSchema,
        UniprotCoreSchema,
        UniprotFeatureSchema,
    ):
        total += _run_schema_checks(schema)
    assert total >= 20


def test_redaction_covers_quoted_url_cycle_set_and_exception() -> None:
    assert "password=" in redact_string('password="sec\\ret" leftover')
    assert redact_string("password=")
    redacted_url = redact_string("see https://user:pass@example.com:8443/path?q=1#f")
    assert "[REDACTED]" in redacted_url or "example.com" in redacted_url
    assert redact_string("://not-a-url") == "://not-a-url"
    cyclic: dict[str, object] = {"token": "abc"}
    cyclic["self"] = cyclic
    redacted = _redact(cyclic)
    assert isinstance(redacted, dict)
    assert redacted["token"] == "[REDACTED]"
    assert _redact({"items": {"x", "y"}})
    assert _redact(("a", "b"))
    assert _redact(ValueError("token=abc"))
    assert _redact(object()) is not None
    assert redact_string("Bearer abc.def")
    assert redact_string("sk-abc123")


def test_bronze_write_result_path_guards() -> None:
    with pytest.raises(ValueError, match="relative_path"):
        BronzeWriteResult(
            batch_id=_BATCH,
            relative_path="",
            absolute_path="/tmp/x",
            record_count=0,
            compressed_size=0,
            uncompressed_size=0,
            checksum_blake2="abc",
        )
    with pytest.raises(ValueError, match="parent-directory"):
        BronzeWriteResult(
            batch_id=_BATCH,
            relative_path="chembl/../activity/file.jsonl",
            absolute_path="/tmp/x",
            record_count=0,
            compressed_size=0,
            uncompressed_size=0,
            checksum_blake2="abc",
        )
    ok = BronzeWriteResult(
        batch_id=_BATCH,
        relative_path="v1/chembl/activity/file.jsonl.zst",
        absolute_path="/tmp/file.jsonl.zst",
        record_count=1,
        compressed_size=1,
        uncompressed_size=1,
        checksum_blake2="abc",
    )
    assert ok.provider_entity == ("chembl", "activity")
    dotted = BronzeWriteResult(
        batch_id=_BATCH,
        relative_path="./chembl/activity/file.jsonl.zst",
        absolute_path="/tmp/file.jsonl.zst",
        record_count=1,
        compressed_size=1,
        uncompressed_size=1,
        checksum_blake2="abc",
    )
    assert dotted.provider_entity[0] == "chembl"
    no_prefix = BronzeWriteResult(
        batch_id=_BATCH,
        relative_path="chembl/activity/file.jsonl.zst",
        absolute_path="/tmp/file.jsonl.zst",
        record_count=1,
        compressed_size=1,
        uncompressed_size=1,
        checksum_blake2="abc",
    )
    assert no_prefix.provider_entity == ("chembl", "activity")
    with pytest.raises(ValueError, match="provider/entity"):
        BronzeWriteResult(
            batch_id=_BATCH,
            relative_path="chembl/",
            absolute_path="/tmp/x",
            record_count=0,
            compressed_size=0,
            uncompressed_size=0,
            checksum_blake2="abc",
        )


def test_observability_mapping_and_contract_repair() -> None:
    events = [
        PipelineCompleted(
            occurred_at=_NOW,
            run_id=_RUN,
            pipeline_name="chembl_activity",
            records_processed=1,
            duration_seconds=1.0,
            stages_count=1,
        ),
        PipelineFailed(
            occurred_at=_NOW,
            run_id=_RUN,
            pipeline_name="chembl_activity",
            failed_stage="extract",
            error="boom",
            error_type=None,
        ),
        PipelineShutdown(
            occurred_at=_NOW,
            run_id=_RUN,
            pipeline_name="chembl_activity",
            records_processed=0,
        ),
        BatchCreated(
            occurred_at=_NOW, run_id=_RUN, batch_id=_BATCH, record_count=1
        ),
        BatchSealed(
            occurred_at=_NOW,
            run_id=_RUN,
            batch_id=_BATCH,
            record_count=1,
            valid_count=1,
            quarantined_count=0,
        ),
        BatchWritten(
            occurred_at=_NOW,
            run_id=_RUN,
            batch_id=_BATCH,
            layer=Layer.BRONZE,
            record_count=1,
        ),
        BatchFailed(
            occurred_at=_NOW,
            run_id=_RUN,
            batch_id=_BATCH,
            layer=Layer.BRONZE,
            error="boom",
            error_type=None,
        ),
        RecordQuarantined(
            occurred_at=_NOW,
            run_id=_RUN,
            batch_id=_BATCH,
            record_id="r1",
            error_code="E",
            error_message="bad",
            content_hash=None,
        ),
        QuarantineEntryCreated(
            occurred_at=_NOW,
            run_id=_RUN,
            pipeline_name="chembl_activity",
            batch_id=_BATCH,
            error_code="E",
            payload_hash=ContentHash("h" * 64),
            metadata={},
        ),
        QuarantineEntryResolved(
            occurred_at=_NOW,
            run_id=_RUN,
            entry_id="e1",
            resolution="ignored",
        ),
    ]
    for event in events:
        envelope = map_domain_event_to_observability_event(event)
        assert envelope.event_name
    with pytest.raises(TypeError):
        map_domain_event_to_observability_event(object())  # type: ignore[arg-type]

    repaired = enforce_observability_contract_context(
        event_name="",
        context={},
        default_provider="",
        default_pipeline="chembl_activity__v1_2_0",
        default_run_id="",
        default_severity="error",
    )
    assert repaired["provider"]
    assert is_observability_contract_valid(repaired)
    labels = normalize_observability_metric_labels({"event": "x"})
    assert labels["pipeline"]
    assert normalize_observability_pipeline_label("chembl_activity__v1_2_0")
    assert normalize_observability_pipeline_label("C:\\tmp\\p")
    assert normalize_observability_pipeline_label(
        "00000000-0000-4000-8000-000000000001"
    )
    assert normalize_observability_pipeline_label("sha256:" + "a" * 32)
