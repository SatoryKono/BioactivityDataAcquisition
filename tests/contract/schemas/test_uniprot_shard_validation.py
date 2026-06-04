"""Contract validation for UniProt schema shards."""

from __future__ import annotations

import pandas as pd
import pandera as pa
import pytest

from bioetl.domain.schemas.uniprot._core import UniprotCoreSchema
from bioetl.domain.schemas.uniprot._features import UniprotFeatureSchema
from bioetl.domain.schemas.uniprot.idmapping import IDMappingSchema
from bioetl.domain.schemas.uniprot.protein import UniprotTargetSchema
from tests.contract.schemas._schema_row_helpers import (
    dataframe_from_row,
    id_mapping_row,
    minimal_schema_dataframe,
)

pytestmark = [pytest.mark.contracts, pytest.mark.no_api]


def test_uniprot_core_shard_accepts_minimal_valid_row() -> None:
    UniprotCoreSchema.validate(minimal_schema_dataframe(UniprotCoreSchema))


@pytest.mark.parametrize("accession", ["BAD", "123", ""])
def test_uniprot_core_shard_rejects_invalid_accession(accession: str) -> None:
    frame = minimal_schema_dataframe(UniprotCoreSchema)
    frame.loc[0, "accession"] = accession
    with pytest.raises(pa.errors.SchemaError):
        UniprotCoreSchema.validate(frame)


def test_uniprot_core_shard_rejects_invalid_entry_name() -> None:
    frame = minimal_schema_dataframe(UniprotCoreSchema)
    frame.loc[0, "entry_name"] = "invalid"
    with pytest.raises(pa.errors.SchemaError):
        UniprotCoreSchema.validate(frame)


def test_uniprot_feature_shard_rejects_negative_feature_count() -> None:
    df = pd.DataFrame([{"feature_count": -1}])
    with pytest.raises(pa.errors.SchemaError):
        UniprotFeatureSchema.validate(df)


def test_id_mapping_shard_accepts_found_mapping() -> None:
    IDMappingSchema.validate(dataframe_from_row(id_mapping_row()))


def test_id_mapping_shard_rejects_invalid_target_id() -> None:
    with pytest.raises(pa.errors.SchemaError):
        IDMappingSchema.validate(
            dataframe_from_row(id_mapping_row(target_id="TARGET1"))
        )


def test_id_mapping_shard_rejects_invalid_mapping_status() -> None:
    with pytest.raises(pa.errors.SchemaError):
        IDMappingSchema.validate(
            dataframe_from_row(id_mapping_row(mapping_status="unknown"))
        )


def test_uniprot_target_schema_accepts_composed_minimal_row() -> None:
    UniprotTargetSchema.validate(minimal_schema_dataframe(UniprotTargetSchema))


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("entry_type", "bad"),
        ("flag", "bad"),
        ("taxonomy_id", 0),
        ("sequence", "ACD*"),
        ("sequence_length", 0),
        ("sequence_mass", 0),
        ("entry_version", 0),
        ("protein_existence", "bad"),
        ("annotation_score", 6),
    ],
)
def test_uniprot_core_shard_rejects_additional_invalid_values(
    field: str,
    value: object,
) -> None:
    frame = minimal_schema_dataframe(UniprotCoreSchema)
    frame.loc[0, field] = value
    with pytest.raises(pa.errors.SchemaError):
        UniprotCoreSchema.validate(frame)


@pytest.mark.parametrize(
    "field",
    [
        "cross_reference_count",
        "keyword_count",
        "publication_count",
        "isoform_count",
    ],
)
def test_uniprot_feature_shard_rejects_additional_negative_counts(field: str) -> None:
    df = pd.DataFrame([{field: -1}])
    with pytest.raises(pa.errors.SchemaError):
        UniprotFeatureSchema.validate(df)


def test_id_mapping_shard_accepts_not_found_without_accession() -> None:
    IDMappingSchema.validate(
        dataframe_from_row(
            id_mapping_row(
                uniprot_accession=None,
                mapping_status="not_found",
            )
        )
    )


def test_id_mapping_shard_rejects_invalid_uniprot_accession() -> None:
    with pytest.raises(pa.errors.SchemaError):
        IDMappingSchema.validate(
            dataframe_from_row(id_mapping_row(uniprot_accession="bad"))
        )
