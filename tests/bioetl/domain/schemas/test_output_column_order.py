"""Проверки OUTPUT_COLUMN_ORDER для схем ChEMBL."""

import pytest

from bioetl.domain.schemas.chembl import activity, assay, document, molecule, target, testitem
from bioetl.domain.schemas.chembl.activity import ActivitySchema
from bioetl.domain.schemas.chembl.assay import AssaySchema
from bioetl.domain.schemas.chembl.document import DocumentSchema
from bioetl.domain.schemas.chembl.molecule import MoleculeSchema
from bioetl.domain.schemas.chembl.target import TargetSchema
from bioetl.domain.schemas.chembl.testitem import TestitemSchema as SchemaTestitem


TECHNICAL_COLUMNS = {
    "hash_row",
    "hash_business_key",
    "index",
    "database_version",
    "extracted_at",
}


@pytest.mark.parametrize(
    ("module", "schema_cls"),
    [
        (activity, ActivitySchema),
        (assay, AssaySchema),
        (document, DocumentSchema),
        (molecule, MoleculeSchema),
        (target, TargetSchema),
        (testitem, SchemaTestitem),
    ],
)
def test_output_column_order_subset_of_schema(module, schema_cls) -> None:
    """OUTPUT_COLUMN_ORDER содержит только допустимые бизнес-колонки."""

    output_columns = module.OUTPUT_COLUMN_ORDER
    schema_columns = set(schema_cls.to_schema().columns.keys())

    assert output_columns, "Список OUTPUT_COLUMN_ORDER не должен быть пустым"
    assert len(output_columns) == len(set(output_columns)), "Повторы недопустимы"
    assert set(output_columns).issubset(schema_columns)
    assert set(output_columns).isdisjoint(TECHNICAL_COLUMNS)

