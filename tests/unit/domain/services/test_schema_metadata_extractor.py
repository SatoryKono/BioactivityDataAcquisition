"""Tests for shared schema metadata extraction (RF-03)."""

from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest

from bioetl.composition.services.metadata_coordinator import MetadataCoordinator
from bioetl.domain.medallion import GoldWriteMode
from bioetl.domain.ports import GoldMetadataInput
from bioetl.domain.services.schema_metadata_extractor import extract_schema_metadata
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.domain.types import RunID, RunType
from bioetl.infrastructure.storage.metadata_builder import GoldMetadataBuilder


class _FakeColumn:
    def __init__(self, dtype: object, nullable: bool) -> None:
        self.dtype = dtype
        self.nullable = nullable


class _FakeSchemaInstance:
    columns = {
        "entity_id": _FakeColumn(dtype="pandera.dtypes.String", nullable=False),
        "score": _FakeColumn(dtype="pandera.dtypes.Float64", nullable=True),
    }


class _FakeSchemaWithColumns:
    class Config:
        version = 2
        strict = False

    @classmethod
    def to_schema(cls) -> _FakeSchemaInstance:
        return _FakeSchemaInstance()


class _FakeSchemaExtractionError:
    class Config:
        version = "3.1.0"
        strict = True

    @classmethod
    def to_schema(cls) -> _FakeSchemaInstance:
        raise ValueError("broken schema")


def _build_schema_info_via_builder(gold_schema: object | None):
    builder = GoldMetadataBuilder()
    metadata = builder.build_fallback_metadata(
        table_name="chembl.activity",
        records=[{"id": 1}],
        mode=GoldWriteMode.OVERWRITE,
        gold_schema=gold_schema,
    )
    return metadata.schema_info


def _build_schema_info_via_coordinator(gold_schema: object | None):
    context = RunContext.create(
        run_id=RunID(uuid4()),
        run_type=RunType.INCREMENTAL,
        started_at=datetime.now(UTC),
        provider="chembl",
        entity="activity",
    )
    coordinator = MetadataCoordinator(context)
    metadata = coordinator.create_gold_metadata(
        GoldMetadataInput(
            table_path="/data/gold/chembl/activity",
            table_name="chembl.activity",
            records=[{"id": 1}],
            mode=GoldWriteMode.OVERWRITE,
            gold_schema=gold_schema,
        )
    )
    return metadata.schema_info


@pytest.mark.parametrize(
    ("gold_schema", "case"),
    [
        (None, "none"),
        (_FakeSchemaWithColumns, "columns"),
        (_FakeSchemaExtractionError, "schema_error"),
    ],
)
def test_shared_schema_extraction_vectors_match_all_call_sites(
    gold_schema: object | None, case: str
) -> None:
    """Builder and coordinator must produce identical schema metadata."""
    expected = extract_schema_metadata(gold_schema)
    from_builder = _build_schema_info_via_builder(gold_schema)
    from_coordinator = _build_schema_info_via_coordinator(gold_schema)

    assert from_builder == expected, f"builder mismatch on vector '{case}'"
    assert from_coordinator == expected, f"coordinator mismatch on vector '{case}'"


def test_shared_schema_extraction_contract_path_vector(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Contract path extraction must stay consistent across all call sites."""
    import bioetl.domain.services.schema_metadata_extractor as extractor_module

    fake_module = SimpleNamespace(
        __file__="/tmp/work/src/bioetl/domain/contracts/gold/fake_schema.py"
    )

    monkeypatch.setattr(extractor_module.inspect, "getmodule", lambda _: fake_module)

    expected = extract_schema_metadata(_FakeSchemaWithColumns)
    from_builder = _build_schema_info_via_builder(_FakeSchemaWithColumns)
    from_coordinator = _build_schema_info_via_coordinator(_FakeSchemaWithColumns)

    assert expected.contract_path == "src/bioetl/domain/contracts/gold/fake_schema.py"
    assert from_builder == expected
    assert from_coordinator == expected
