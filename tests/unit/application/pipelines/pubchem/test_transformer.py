"""Same-path owner tests for PubChem pipeline transformer module."""

from __future__ import annotations

import pytest

from bioetl.application.core.base_transformer import BaseTransformer
from bioetl.application.pipelines.pubchem.transformer import (
    PubChemCompoundTransformer,
    __all__,
)


pytestmark = pytest.mark.unit

def test_pubchem_transformer_is_canonical_base_transformer_subclass() -> None:
    assert issubclass(PubChemCompoundTransformer, BaseTransformer)


def test_pubchem_transformer_module_exports_single_transformer_entrypoint() -> None:
    assert __all__ == ["PubChemCompoundTransformer"]
