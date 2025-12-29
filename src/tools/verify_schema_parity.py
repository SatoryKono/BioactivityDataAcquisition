"""Script to programmatically verify schema parity."""

import dataclasses

from bioetl.domain.entities.chembl_activity import Activity, Assay
from bioetl.domain.entities.chembl_structures import Molecule, Target
from bioetl.infrastructure.schemas.gold import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLTargetGoldSchema,
)
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
)


def get_dataclass_fields(cls):
    """Return set of field names from a dataclass, excluding system fields."""
    return {f.name for f in dataclasses.fields(cls)}


def get_pyarrow_fields(schema):
    """Return set of field names from PyArrow schema."""
    return {f.name for f in schema}


def get_pandera_fields(model):
    """Return set of field names from Pandera model."""
    return model.to_schema().columns.keys()


def check_parity(name, domain_cls, silver_schema, gold_model):
    print(f"Checking {name}...")
    domain_fields = get_dataclass_fields(domain_cls)
    silver_fields = get_pyarrow_fields(silver_schema)
    gold_fields = get_pandera_fields(gold_model)

    # System fields to ignore in domain comparison (added by BaseEntity/Infrastructure)
    system_fields = {
        "_run_id",
        "_run_type",
        "_source_batch_id",
        "_ingestion_ts",
        "entity_id",
        "content_hash",
        "ingestion_ts",
        "run_id",
        "run_type",
        "source_batch_id",
    }

    missing_in_silver = {
        f for f in domain_fields if f not in silver_fields and f not in system_fields
    }

    if missing_in_silver:
        print(f"  [ERROR] Fields in Domain but missing in Silver: {missing_in_silver}")
    else:
        print("  [OK] All Domain fields present in Silver.")

    # Check 2: Silver vs Gold
    # Gold Schema keys() usually returns the aliased name if defined, or the field name.
    # In our Gold schema, we use alias="_run_id", so to_schema().columns keys should be "_run_id".

    missing_in_gold = silver_fields - set(gold_fields)
    missing_in_silver_from_gold = set(gold_fields) - silver_fields

    if missing_in_gold:
        print(f"  [ERROR] Fields in Silver but missing in Gold: {missing_in_gold}")
    elif missing_in_silver_from_gold:
        print(
            f"  [ERROR] Fields in Gold but missing in Silver: {missing_in_silver_from_gold}"
        )
    else:
        print("  [OK] Silver and Gold schemas match exactly.")


if __name__ == "__main__":
    check_parity("Molecule", Molecule, CHEMBL_MOLECULE_SCHEMA, ChEMBLMoleculeGoldSchema)
    check_parity("Target", Target, CHEMBL_TARGET_SCHEMA, ChEMBLTargetGoldSchema)
    check_parity("Activity", Activity, CHEMBL_ACTIVITY_SCHEMA, ChEMBLActivityGoldSchema)
    check_parity("Assay", Assay, CHEMBL_ASSAY_SCHEMA, ChEMBLAssayGoldSchema)
