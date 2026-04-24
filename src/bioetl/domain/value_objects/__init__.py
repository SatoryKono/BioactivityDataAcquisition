"""Value Objects for BioETL domain.

Value Objects are immutable domain primitives that encapsulate validation
and business rules. They provide type safety and self-validation.

Categories:
- Identifiers: ChemblId, UniProtId, DOI, PubMedId, PubChemCid, CompoundId, AssayId
- Publication: OpenAlexId, SemanticScholarId, ISSN, ORCID
- Chemical: InChI, InChIKey, SMILES, MolecularWeight
- Molecular Descriptors: HydrogenBondCount, RotatableBondCount, HeavyAtomCount, LogP, PolarSurfaceArea
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

from __future__ import annotations

from importlib import import_module as _import_module
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.domain.value_objects.academic_ids import ISSN, ORCID, OpenAlexId, SemanticScholarId
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
    from bioetl.domain.value_objects.chemical import MolecularWeight, PublicationYear
    from bioetl.domain.value_objects.compound_ids import AssayId, CompoundId, CompoundSource
    from bioetl.domain.value_objects.dq_anomaly import (
        DQAnomaly,
        DQAnomalySeverity,
        DQAnomalyType,
    )
    from bioetl.domain.value_objects.dq_result import DQEvaluationStatus
    from bioetl.domain.value_objects.identifiers import ChemblId, PubChemCid, UniProtId
    from bioetl.domain.value_objects.inchi import InChI
    from bioetl.domain.value_objects.molecular_descriptors import (
        HeavyAtomCount,
        HydrogenBondCount,
        LogP,
        PolarSurfaceArea,
        RotatableBondCount,
    )
    from bioetl.domain.value_objects.publications import DOI, PubMedId
    from bioetl.domain.value_objects.taxonomy_id import TaxonomyId, validate_taxonomy_id
    from bioetl.domain.value_objects._chemical_identifiers import InChIKey, SMILES

_MODULE_ACADEMIC_IDS = "bioetl.domain.value_objects.academic_ids"
_MODULE_ACTIVITY = "bioetl.domain.value_objects.activity"
_MODULE_ACTIVITY_VALUES = "bioetl.domain.value_objects.activity_values"
_MODULE_CHEMICAL = "bioetl.domain.value_objects.chemical"
_MODULE_COMPOUND_IDS = "bioetl.domain.value_objects.compound_ids"
_MODULE_DQ_ANOMALY = "bioetl.domain.value_objects.dq_anomaly"
_MODULE_DQ_RESULT = "bioetl.domain.value_objects.dq_result"
_MODULE_IDENTIFIERS = "bioetl.domain.value_objects.identifiers"
_MODULE_MOLECULAR_DESCRIPTORS = "bioetl.domain.value_objects.molecular_descriptors"
_MODULE_PUBLICATIONS = "bioetl.domain.value_objects.publications"
_MODULE_TAXONOMY_ID = "bioetl.domain.value_objects.taxonomy_id"

_LAZY_ATTRIBUTE_EXPORTS: dict[str, tuple[str, str]] = {
    "DOI": (_MODULE_PUBLICATIONS, "DOI"),
    "ISSN": (_MODULE_ACADEMIC_IDS, "ISSN"),
    "ORCID": (_MODULE_ACADEMIC_IDS, "ORCID"),
    "SMILES": (_MODULE_CHEMICAL, "SMILES"),
    "ActivityType": (_MODULE_ACTIVITY_VALUES, "ActivityType"),
    "ActivityValue": (_MODULE_ACTIVITY, "ActivityValue"),
    "AssayId": (_MODULE_COMPOUND_IDS, "AssayId"),
    "ChemblId": (_MODULE_IDENTIFIERS, "ChemblId"),
    "CompoundId": (_MODULE_COMPOUND_IDS, "CompoundId"),
    "CompoundSource": (
        _MODULE_COMPOUND_IDS,
        "CompoundSource",
    ),
    "Concentration": (
        _MODULE_ACTIVITY_VALUES,
        "Concentration",
    ),
    "ConcentrationUnit": (
        _MODULE_ACTIVITY_VALUES,
        "ConcentrationUnit",
    ),
    "ConfidenceScore": (_MODULE_ACTIVITY, "ConfidenceScore"),
    "DQAnomaly": (_MODULE_DQ_ANOMALY, "DQAnomaly"),
    "DQAnomalySeverity": (
        _MODULE_DQ_ANOMALY,
        "DQAnomalySeverity",
    ),
    "DQAnomalyType": (_MODULE_DQ_ANOMALY, "DQAnomalyType"),
    "DQEvaluationStatus": (
        _MODULE_DQ_RESULT,
        "DQEvaluationStatus",
    ),
    "HeavyAtomCount": (
        _MODULE_MOLECULAR_DESCRIPTORS,
        "HeavyAtomCount",
    ),
    "HydrogenBondCount": (
        _MODULE_MOLECULAR_DESCRIPTORS,
        "HydrogenBondCount",
    ),
    "InChI": ("bioetl.domain.value_objects.inchi", "InChI"),
    "InChIKey": (_MODULE_CHEMICAL, "InChIKey"),
    "LogP": (_MODULE_MOLECULAR_DESCRIPTORS, "LogP"),
    "MolecularWeight": (
        _MODULE_CHEMICAL,
        "MolecularWeight",
    ),
    "OpenAlexId": (_MODULE_ACADEMIC_IDS, "OpenAlexId"),
    "PChemblValue": (_MODULE_ACTIVITY_VALUES, "PChemblValue"),
    "PolarSurfaceArea": (
        _MODULE_MOLECULAR_DESCRIPTORS,
        "PolarSurfaceArea",
    ),
    "PubChemCid": (_MODULE_IDENTIFIERS, "PubChemCid"),
    "PubMedId": (_MODULE_PUBLICATIONS, "PubMedId"),
    "PublicationYear": (
        _MODULE_CHEMICAL,
        "PublicationYear",
    ),
    "RelationOperator": (
        _MODULE_ACTIVITY,
        "RelationOperator",
    ),
    "RotatableBondCount": (
        _MODULE_MOLECULAR_DESCRIPTORS,
        "RotatableBondCount",
    ),
    "SemanticScholarId": (
        _MODULE_ACADEMIC_IDS,
        "SemanticScholarId",
    ),
    "TaxonomyId": (_MODULE_TAXONOMY_ID, "TaxonomyId"),
    "UniProtId": (_MODULE_IDENTIFIERS, "UniProtId"),
    "ValueObject": ("bioetl.domain.value_objects.base", "ValueObject"),
    "validate_taxonomy_id": (
        _MODULE_TAXONOMY_ID,
        "validate_taxonomy_id",
    ),
}

__all__ = [
    "DOI",
    "ISSN",
    "ORCID",
    "SMILES",
    "ActivityType",
    "ActivityValue",
    "AssayId",
    "ChemblId",
    "CompoundId",
    "CompoundSource",
    "Concentration",
    "ConcentrationUnit",
    "ConfidenceScore",
    "DQAnomaly",
    "DQAnomalySeverity",
    "DQAnomalyType",
    "DQEvaluationStatus",
    "HeavyAtomCount",
    "HydrogenBondCount",
    "InChI",
    "InChIKey",
    "LogP",
    "MolecularWeight",
    "OpenAlexId",
    "PChemblValue",
    "PolarSurfaceArea",
    "PubChemCid",
    "PubMedId",
    "PublicationYear",
    "RelationOperator",
    "RotatableBondCount",
    "SemanticScholarId",
    "TaxonomyId",
    "UniProtId",
    "ValueObject",
    "validate_taxonomy_id",
]


def __getattr__(name: str) -> object:
    """Resolve public value-object facade exports lazily."""
    try:
        module_name, attribute_name = _LAZY_ATTRIBUTE_EXPORTS[name]
    except KeyError as exc:  # pragma: no cover - standard attribute path
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from exc

    value = getattr(_import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable facade exports for introspection."""
    return sorted(set(globals()) | set(__all__))
