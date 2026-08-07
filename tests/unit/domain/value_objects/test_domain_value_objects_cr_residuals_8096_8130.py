# pyright: reportArgumentType=false
"""Residual closeout coverage for domain/value_objects CR-FULL #8096-#8130."""

from __future__ import annotations

from uuid import UUID

import pytest

pytestmark = pytest.mark.unit

from bioetl.domain.types import BatchID
from bioetl.domain.value_objects.activity_concentration import (
    Concentration,
    ConcentrationUnit,
)
from bioetl.domain.value_objects.activity_confidence import ConfidenceScore
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.column_qualifier import ColumnQualifier
from bioetl.domain.value_objects.dq_metrics_calculations import is_valid_numeric
from bioetl.domain.value_objects.inchi import InChI


def test_confidence_score_rejects_bool() -> None:
    with pytest.raises(TypeError):
        ConfidenceScore(True)  # type: ignore[arg-type]


def test_inchi_rejects_bare_prefix() -> None:
    with pytest.raises(ValueError, match="version and layer"):
        InChI("InChI=")
    assert InChI("InChI=1S/C2H6/c1-2/h1-2H3").value.startswith("InChI=")


def test_concentration_rejects_nan_and_converts() -> None:
    with pytest.raises(ValueError, match="finite"):
        Concentration(value=float("nan"), unit=ConcentrationUnit.NANOMOLAR)
    c = Concentration(value=1000.0, unit=ConcentrationUnit.NANOMOLAR)
    assert c.to_unit(ConcentrationUnit.MICROMOLAR).value == 1.0


def test_column_qualifier_preserves_dots_in_field() -> None:
    q = ColumnQualifier.parse("chembl.activity.foo.bar")
    assert q.provider == "chembl"
    assert q.entity == "activity"
    assert q.field == "foo.bar"
    assert ColumnQualifier.is_qualified("chembl.activity.foo.bar")


def test_is_valid_numeric_overflow() -> None:
    huge = 10**10000
    assert is_valid_numeric(huge) is False


def test_bronze_result_rejects_bad_relative_path_and_zero_compress() -> None:
    with pytest.raises(ValueError, match="provider/entity"):
        BronzeWriteResult(
            batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000201")),
            relative_path="onlyfile.jsonl.zst",
            absolute_path="/tmp/onlyfile.jsonl.zst",
            record_count=1,
            compressed_size=10,
            uncompressed_size=20,
            checksum_blake2="abc",
        )
    result = BronzeWriteResult(
        batch_id=BatchID(UUID("00000000-0000-0000-0000-000000000201")),
        relative_path="chembl/activity/batch.jsonl.zst",
        absolute_path="/data/chembl/activity/batch.jsonl.zst",
        record_count=1,
        compressed_size=0,
        uncompressed_size=100,
        checksum_blake2="abc",
    )
    assert result.compression_ratio == 1.0
