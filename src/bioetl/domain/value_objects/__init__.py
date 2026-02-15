"""Value Objects for BioETL domain.

Value Objects are immutable domain primitives that encapsulate validation
and business rules. They provide type safety and self-validation.

Categories:
- Identifiers: ChemblId, UniProtId, DOI, PubMedId, PubChemCid, CompoundId, AssayId
- Publication: OpenAlexId, SemanticScholarId, ISSN, ORCID
- Chemical: InChIKey, SMILES, MolecularWeight
- Biological: TaxonomyId (NCBI Taxonomy)
- Metadata: PublicationYear
- Activity Values: Concentration, ActivityType, PChemblValue, ActivityValue
- Activity: ConfidenceScore, RelationOperator

DQ report types, column order, and other internal types should be imported
directly from their submodules:
- ``bioetl.domain.value_objects.dq_report``
- ``bioetl.domain.value_objects.dq_metrics``
- ``bioetl.domain.value_objects.dq_result``
- ``bioetl.domain.value_objects.column_order``
- ``bioetl.domain.value_objects.column_qualifier``
- ``bioetl.domain.value_objects.publication_field_groups``
- ``bioetl.domain.value_objects.bronze_result``
- ``bioetl.domain.value_objects.silver_result``
- ``bioetl.domain.value_objects.run_context``

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

from bioetl.domain.value_objects.academic_ids import (
    ISSN,
    ORCID,
    OpenAlexId,
    SemanticScholarId,
)
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
    MolecularWeight,
    PublicationYear,
)
from bioetl.domain.value_objects.compound_ids import (
    AssayId,
    CompoundId,
    CompoundSource,
)
from bioetl.domain.value_objects.dq_result import DQEvaluationStatus
from bioetl.domain.value_objects.identifiers import (
    ChemblId,
    PubChemCid,
    UniProtId,
)
from bioetl.domain.value_objects.publications import (
    DOI,
    PubMedId,
)
from bioetl.domain.value_objects.taxonomy_id import (
    TaxonomyId,
    validate_taxonomy_id,
)

__all__ = [
    # Academic IDs
    "ISSN",
    "ORCID",
    "OpenAlexId",
    "SemanticScholarId",
    # Activity
    "ActivityValue",
    "ConfidenceScore",
    "RelationOperator",
    # Activity Values
    "ActivityType",
    "Concentration",
    "ConcentrationUnit",
    "PChemblValue",
    # Base
    "ValueObject",
    # Chemical
    "SMILES",
    "InChIKey",
    "MolecularWeight",
    "PublicationYear",
    # Compound IDs
    "AssayId",
    "CompoundId",
    "CompoundSource",
    # DQ Result
    "DQEvaluationStatus",
    # Identifiers
    "ChemblId",
    "PubChemCid",
    "UniProtId",
    # Publications
    "DOI",
    "PubMedId",
    # Taxonomy
    "TaxonomyId",
    "validate_taxonomy_id",
]
