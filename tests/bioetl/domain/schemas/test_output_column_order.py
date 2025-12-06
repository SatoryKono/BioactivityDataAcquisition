"""Проверки порядка колонок для схем ChEMBL."""

import pytest

from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.document import DocumentSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.output_views import (
    ACTIVITY_OUTPUT_COLUMNS,
    ASSAY_OUTPUT_COLUMNS,
    DOCUMENT_OUTPUT_COLUMNS,
    MOLECULE_OUTPUT_COLUMNS,
    TARGET_OUTPUT_COLUMNS,
    TESTITEM_OUTPUT_COLUMNS,
)
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.testitem import TestitemSchema


METADATA_COLUMNS = [
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
]


@pytest.mark.parametrize(
    ("output_columns", "schema_cls"),
    [
        (ACTIVITY_OUTPUT_COLUMNS, ActivitySchema),
        (ASSAY_OUTPUT_COLUMNS, AssaySchema),
        (DOCUMENT_OUTPUT_COLUMNS, DocumentSchema),
        (MOLECULE_OUTPUT_COLUMNS, MoleculeSchema),
        (TARGET_OUTPUT_COLUMNS, TargetSchema),
        (TESTITEM_OUTPUT_COLUMNS, TestitemSchema),
    ],
)
def test_output_column_order_matches_schema(output_columns, schema_cls) -> None:
    """Порядок колонок совпадает с колонками схемы без дубликатов."""

    schema_columns = set(schema_cls.to_schema().columns.keys())
    business_columns = [col for col in output_columns if col not in METADATA_COLUMNS]

    assert output_columns, "Список с колонками не должен быть пустым"
    assert len(output_columns) == len(set(output_columns)), "Повторы недопустимы"
    assert set(output_columns).issubset(schema_columns)
    assert set(business_columns).issubset(schema_columns - set(METADATA_COLUMNS))


@pytest.mark.parametrize(
    "output_columns",
    [
        ACTIVITY_OUTPUT_COLUMNS,
        ASSAY_OUTPUT_COLUMNS,
        DOCUMENT_OUTPUT_COLUMNS,
        MOLECULE_OUTPUT_COLUMNS,
        TARGET_OUTPUT_COLUMNS,
        TESTITEM_OUTPUT_COLUMNS,
    ],
)
def test_metadata_columns_last(output_columns) -> None:
    """Служебные колонки идут последними в фиксированном порядке."""

    metadata_suffix = output_columns[-len(METADATA_COLUMNS) :]
    business_prefix = output_columns[: -len(METADATA_COLUMNS)]

    assert metadata_suffix == METADATA_COLUMNS
    assert not set(METADATA_COLUMNS) & set(business_prefix)

