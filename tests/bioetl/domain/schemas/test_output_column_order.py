"""Проверки порядка колонок для схем ChEMBL."""

import pytest

from bioetl.domain.schemas.chembl.activity import ActivityTableSchema
from bioetl.domain.schemas.chembl.assay import AssayTableSchema
from bioetl.domain.schemas.chembl.base import GENERATED_COLUMN_ORDER
from bioetl.domain.schemas.chembl.molecule import MoleculeTableSchema
from bioetl.domain.schemas.chembl.output_views import (
    ACTIVITY_OUTPUT_COLUMNS,
    ASSAY_OUTPUT_COLUMNS,
    MOLECULE_OUTPUT_COLUMNS,
    PUBLICATION_OUTPUT_COLUMNS,
    TARGET_OUTPUT_COLUMNS,
)
from bioetl.domain.schemas.chembl.publication import PublicationTableSchema
from bioetl.domain.schemas.chembl.target import TargetTableSchema


@pytest.mark.parametrize(
    ("output_columns", "schema_cls"),
    [
        (ACTIVITY_OUTPUT_COLUMNS, ActivityTableSchema),
        (ASSAY_OUTPUT_COLUMNS, AssayTableSchema),
        (PUBLICATION_OUTPUT_COLUMNS, PublicationTableSchema),
        (MOLECULE_OUTPUT_COLUMNS, MoleculeTableSchema),
        (TARGET_OUTPUT_COLUMNS, TargetTableSchema),
    ],
)
def test_output_column_order_matches_schema(output_columns, schema_cls) -> None:
    """Порядок колонок совпадает с колонками схемы без дубликатов."""

    schema_columns = set(schema_cls.to_schema().columns.keys())
    business_columns = [
        col for col in output_columns if col not in GENERATED_COLUMN_ORDER
    ]

    assert output_columns, "Список с колонками не должен быть пустым"
    assert len(output_columns) == len(set(output_columns)), "Повторы недопустимы"
    assert set(output_columns).issubset(schema_columns)
    assert set(business_columns).issubset(schema_columns - set(GENERATED_COLUMN_ORDER))


@pytest.mark.parametrize(
    "output_columns",
    [
        ACTIVITY_OUTPUT_COLUMNS,
        ASSAY_OUTPUT_COLUMNS,
        PUBLICATION_OUTPUT_COLUMNS,
        MOLECULE_OUTPUT_COLUMNS,
        TARGET_OUTPUT_COLUMNS,
    ],
)
def test_metadata_columns_last(output_columns) -> None:
    """Служебные колонки идут последними в фиксированном порядке."""

    metadata_suffix = output_columns[-len(GENERATED_COLUMN_ORDER) :]
    business_prefix = output_columns[: -len(GENERATED_COLUMN_ORDER)]

    assert metadata_suffix == GENERATED_COLUMN_ORDER
    assert not set(GENERATED_COLUMN_ORDER) & set(business_prefix)
