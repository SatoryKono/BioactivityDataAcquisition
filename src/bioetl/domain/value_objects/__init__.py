"""Value Objects for BioETL domain.

Value Objects are immutable domain primitives that encapsulate validation
and business rules. They provide type safety and self-validation.

Categories:
- Identifiers: ChemblId, UniProtId, DOI, PubMedId, PubChemCid, CompoundId, AssayId
- Chemical: InChIKey, SMILES
- Metadata: PublicationYear
- Activity Values: Concentration, ActivityType, PChemblValue, ActivityValue
- Activity: ConfidenceScore, RelationOperator

Usage:
    >>> from bioetl.domain.value_objects import ChemblId, DOI
    >>> molecule_id = ChemblId("CHEMBL25")
    >>> molecule_id.numeric_id
    25
    >>> doi = DOI("10.1038/nature12373")
    >>> doi.url
    'https://doi.org/10.1038/nature12373'

    >>> from bioetl.domain.value_objects import CompoundId, ConfidenceScore
    >>> cid = CompoundId.from_chembl("CHEMBL25")
    >>> cid.source
    <CompoundSource.CHEMBL: 'chembl'>
    >>> score = ConfidenceScore(9)
    >>> score.is_high_confidence
    True

    >>> from bioetl.domain.value_objects import InChIKey, SMILES, PublicationYear
    >>> key = InChIKey("BSYNRYMUTXBXSQ-UHFFFAOYSA-N")
    >>> key.connectivity_layer
    'BSYNRYMUTXBXSQ'
    >>> smiles = SMILES.canonical("CC(=O)OC1=CC=CC=C1C(=O)O")
    >>> smiles.is_canonical
    True
    >>> year = PublicationYear(2020)
    >>> year.decade
    2020

See also:
- DDD patterns: https://martinfowler.com/bliki/ValueObject.html
- RULES.md §2.8: Entity ID - stable identifiers
"""

from bioetl.domain.value_objects.activity import (
    ActivityValue,
    ConfidenceScore,
    RelationOperator,
)
from bioetl.domain.value_objects.activity_values import (
    ActivityType,
    Concentration,
    ConcentrationUnit,
    PChemblValue,
)
from bioetl.domain.value_objects.base import ValueObject
from bioetl.domain.value_objects.chemical import (
    SMILES,
    InChIKey,
    PublicationYear,
)
from bioetl.domain.value_objects.compound_ids import (
    AssayId,
    CompoundId,
    CompoundIdUnion,
    CompoundSource,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus, DQResult
from bioetl.domain.value_objects.identifiers import (
    ChemblId,
    PubChemCid,
    UniProtId,
)
from bioetl.domain.value_objects.publications import (
    DOI,
    PubMedId,
)

__all__ = [
    "DOI",
    "SMILES",
    "ActivityType",
    "ActivityValue",
    "AssayId",
    "ChemblId",
    "CompoundId",
    "CompoundIdUnion",
    "CompoundSource",
    "Concentration",
    "ConcentrationUnit",
    "ConfidenceScore",
    "DQEvaluationStatus",
    "DQResult",
    "InChIKey",
    "PChemblValue",
    "PubChemCid",
    "PubMedId",
    "PublicationYear",
    "RelationOperator",
    "UniProtId",
    "ValueObject",
]
