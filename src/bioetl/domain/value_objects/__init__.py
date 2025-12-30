"""Value Objects for BioETL domain.

Value Objects are immutable domain primitives that encapsulate validation
and business rules. They provide type safety and self-validation.

Categories:
- Identifiers: ChemblId, UniProtId, DOI, PubMedId, PubChemCid, CompoundId, AssayId
- Measurements: Concentration, ActivityType, PChemblValue, ActivityValue
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

See also:
- DDD patterns: https://martinfowler.com/bliki/ValueObject.html
- RULES.md §2.8: Entity ID - stable identifiers
"""

from bioetl.domain.value_objects.activity import (
    ActivityValue,
    ConfidenceScore,
    RelationOperator,
)
from bioetl.domain.value_objects.base import ValueObject
from bioetl.domain.value_objects.compound_ids import (
    AssayId,
    CompoundId,
    CompoundIdUnion,
    CompoundSource,
)
from bioetl.domain.value_objects.identifiers import (
    DOI,
    ChemblId,
    PubChemCid,
    PubMedId,
    UniProtId,
)
from bioetl.domain.value_objects.measurements import (
    ActivityType,
    Concentration,
    ConcentrationUnit,
    PChemblValue,
)

__all__ = [
    "DOI",
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
    "PChemblValue",
    "PubChemCid",
    "PubMedId",
    "RelationOperator",
    "UniProtId",
    "ValueObject",
]
