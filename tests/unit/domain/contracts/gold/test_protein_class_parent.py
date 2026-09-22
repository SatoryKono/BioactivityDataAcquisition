"""ChEMBL's root sentinel is a valid parent, but negative IDs are invalid."""

import pandas as pd
import pandera.pandas as pa
import pytest

from bioetl.domain.contracts.gold._chembl_molecule_protein_schemas import (
    ChEMBLProteinClassGoldSchema,
)


@pytest.mark.unit
@pytest.mark.parametrize("parent_id", [None, 0, 1, -1])
def test_protein_class_parent_contract(parent_id):
    schema = pa.DataFrameSchema(
        {"parent_id": ChEMBLProteinClassGoldSchema.to_schema().columns["parent_id"]}
    )
    frame = pd.DataFrame({"parent_id": [parent_id]})
    if parent_id == -1:
        with pytest.raises(pa.errors.SchemaError):
            schema.validate(frame)
    else:
        assert len(schema.validate(frame)) == 1
