# pyright: reportIncompatibleVariableOverride=false
# Pandera/ETL nested Config override pattern (PD2-7).
"""Pandera schema for PubChem Molecule entity.

Aligned with RULES.md v5.24 and PubChem PUG REST API.
Source: https://pubchem.ncbi.nlm.nih.gov/rest/pug/
"""

from __future__ import annotations

from bioetl.domain.schemas.pubchem._identifiers import PubchemIdentitySchema
from bioetl.domain.schemas.pubchem._physchem import PubchemPhysChemSchema
from bioetl.domain.schemas.pubchem._stereo import PubchemStereoSchema
from bioetl.domain.schemas.pubchem._three_d import PubchemThreeDSchema
from bioetl.domain.validation import (
    INCHI_KEY_REGEX_PATTERN as _INCHI_KEY_REGEX_PATTERN,
)

INCHI_KEY_REGEX_PATTERN = _INCHI_KEY_REGEX_PATTERN


class PubchemMoleculeSchema(
    PubchemIdentitySchema,
    PubchemPhysChemSchema,
    PubchemStereoSchema,
    PubchemThreeDSchema,
):
    """PubChem Molecule validation schema for Silver layer.

    Represents a unique chemical structure identified by CID.
    """

    class Config:
        """Pandera configuration."""

        strict = False
        ordered = False
        coerce = True
        name = "PubchemMoleculeSchema"
        description = "PubChem Molecule Silver layer validation"


__all__ = [
    "INCHI_KEY_REGEX_PATTERN",
    "PubchemMoleculeSchema",
]
