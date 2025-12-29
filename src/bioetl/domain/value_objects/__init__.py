"""Value Objects for BioETL domain.

Value Objects are immutable domain primitives that encapsulate validation
and business rules. They provide type safety and self-validation.

Categories:
- Identifiers: ChemblId, UniProtId, DOI, PubMedId, PubChemCid
- Measurements: Concentration, ActivityType, PChemblValue

Usage:
    >>> from bioetl.domain.value_objects import ChemblId, DOI
    >>> molecule_id = ChemblId("CHEMBL25")
    >>> molecule_id.numeric_id
    25
    >>> doi = DOI("10.1038/nature12373")
    >>> doi.url
    'https://doi.org/10.1038/nature12373'

See also:
- DDD patterns: https://martinfowler.com/bliki/ValueObject.html
- RULES.md §2.8: Entity ID - stable identifiers
"""

from bioetl.domain.value_objects.base import ValueObject
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
    "ChemblId",
    "Concentration",
    "ConcentrationUnit",
    "PChemblValue",
    "PubChemCid",
    "PubMedId",
    "UniProtId",
    "ValueObject",
]
