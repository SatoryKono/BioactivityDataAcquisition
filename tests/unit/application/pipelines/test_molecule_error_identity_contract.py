"""Only missing molecule identifiers receive the catalog's missing-id reason."""

from __future__ import annotations

from unittest.mock import Mock

import pytest

from bioetl.application.core.base_transformer.errors import TransformationError
from bioetl.application.pipelines.chembl.base_chembl_transformer import (
    BaseChemblTransformer,
)
from bioetl.application.pipelines.chembl.molecule_transformer import MoleculeTransformer

pytestmark = pytest.mark.unit


def test_unrelated_transformation_error_is_not_relabelled_as_missing_compound(
    monkeypatch,
):
    error = TransformationError("invalid molecular weight", field="molecular_weight")
    monkeypatch.setattr(
        BaseChemblTransformer, "_resolve_primary_id", Mock(side_effect=error)
    )
    transformer = MoleculeTransformer.__new__(MoleculeTransformer)
    with pytest.raises(TransformationError) as caught:
        transformer._resolve_primary_id({"molecule_chembl_id": "CHEMBL1"})
    assert caught.value is error
