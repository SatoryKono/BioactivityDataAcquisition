# pyright: reportArgumentType=false
"""Focused tests for CR-FULL 20260816 VO/schema residuals (#8905)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import pytest

from bioetl.domain.schemas.chembl.publication import _is_iso_calendar_date
from bioetl.domain.schemas.column_order import canonical_column_order
from bioetl.domain.schemas.uniprot._core import UniprotCoreSchema
from bioetl.domain.schemas.validators import rows_are_valid_json, str_matches_pattern
from bioetl.domain.value_objects._molecular_weight import MolecularWeight
from bioetl.domain.value_objects._publication_year import PublicationYear
from bioetl.domain.value_objects import (
    ActivityType,
    Concentration,
    ConcentrationUnit,
    PChemblValue,
)
from bioetl.domain.value_objects.column_order import ColumnOrderConfig
from bioetl.domain.value_objects.column_qualifier import ColumnQualifier
from bioetl.domain.value_objects.dq_metrics import BatchDQMetrics
from bioetl.domain.value_objects.dq_metrics_calculations import calculate_null_rate
from bioetl.domain.value_objects.dq_report_builder import _require_aware_timestamp
from bioetl.domain.value_objects.dq_report_enums import DQCheckStatus
from bioetl.domain.value_objects.dq_report_results_core import SchemaSnapshotResult
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult
from bioetl.domain.value_objects.export_identity import format_utc
from bioetl.domain.value_objects.identifiers import PubChemCid
from bioetl.domain.value_objects.inchi import InChI
from bioetl.domain.value_objects.molecular_descriptors import _coerce_int

pytestmark = pytest.mark.unit


def test_concentration_rejects_non_enum_unit_and_trailing_text() -> None:
    with pytest.raises(TypeError, match="ConcentrationUnit"):
        Concentration(1.0, "nM")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="Cannot parse"):
        Concentration.from_string("100 nM extra")
    parsed = Concentration.from_string("100 nM")
    assert parsed.unit is ConcentrationUnit.NANOMOLAR


def test_molecular_weight_rejects_bool() -> None:
    with pytest.raises(ValueError, match="Invalid molecular weight"):
        MolecularWeight(True)


def test_publication_year_century_and_invalid_date() -> None:
    assert PublicationYear(2000).century == 20
    assert PublicationYear("2024-01-15").value == 2024
    with pytest.raises(ValueError):
        PublicationYear("2024-99-99")


def test_pchembl_and_int_coercion_and_utc_format() -> None:
    with pytest.raises(ValueError, match="finite"):
        PChemblValue(float("nan"))
    with pytest.raises(ValueError):
        _coerce_int(1.9)
    with pytest.raises(ValueError, match="timezone-aware"):
        format_utc(datetime(2026, 1, 1, 12, 0, 0))


def test_pubchem_inchi_activity_and_extract_field() -> None:
    assert PubChemCid.from_raw(True) is None
    with pytest.raises(ValueError, match="version and layer"):
        InChI("InChI=1/")
    with pytest.raises(ValueError, match="Unknown activity type"):
        ActivityType.from_string(None)  # type: ignore[arg-type]
    assert ColumnQualifier.extract_field("chembl.publication.foo.bar") == "foo.bar"


def test_dq_invariants_and_frozen_schema() -> None:
    with pytest.raises(ValueError, match="UTC offset"):
        _require_aware_timestamp(datetime(2026, 1, 1, tzinfo=timezone(timedelta(hours=2))))
    with pytest.raises(ValueError, match="error_rate"):
        DQResult(status=DQEvaluationStatus.PASSED, error_rate=1.5)
    with pytest.raises(ValueError, match="error_records"):
        BatchDQMetrics(total_records=1, error_records=5)
    assert calculate_null_rate([], 0) == 0.0
    snap = SchemaSnapshotResult(fields_detected=1, schema={"a": "int"}, status=DQCheckStatus.PASS)
    with pytest.raises(TypeError):
        snap.schema["a"] = "str"  # type: ignore[index]
    cfg = ColumnOrderConfig()
    with pytest.raises(TypeError):
        cfg.field_groups["title"] = cfg.field_groups["title"]  # type: ignore[index]


def test_schema_date_timestamp_dups_json_accession() -> None:
    assert _is_iso_calendar_date("2024-02-29") is True
    assert _is_iso_calendar_date("2024-02-30") is False
    with pytest.raises(ValueError, match="duplicate"):
        canonical_column_order(["entity_id", "name", "name"])
    series = pd.Series([[1, 2], None, "[]"], dtype=object)
    result = rows_are_valid_json(series)
    assert bool(result.iloc[1]) is True
    extra = pd.Series(["P12345EXTRA"])
    assert bool(UniprotCoreSchema._check_accession(extra).iloc[0]) is False
    assert str_matches_pattern(pd.Series(["CHEMBL1X"]), pattern=r"CHEMBL\\d+").tolist() == [False]
