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

from importlib import import_module

_LAZY_ATTRIBUTE_EXPORTS: dict[str, tuple[str, str]] = {
    "DOI": ("bioetl.domain.value_objects.publications", "DOI"),
    "ISSN": ("bioetl.domain.value_objects.academic_ids", "ISSN"),
    "ORCID": ("bioetl.domain.value_objects.academic_ids", "ORCID"),
    "SMILES": ("bioetl.domain.value_objects.chemical", "SMILES"),
    "ActivityType": ("bioetl.domain.value_objects.activity_values", "ActivityType"),
    "ActivityValue": ("bioetl.domain.value_objects.activity", "ActivityValue"),
    "AssayId": ("bioetl.domain.value_objects.compound_ids", "AssayId"),
    "ChemblId": ("bioetl.domain.value_objects.identifiers", "ChemblId"),
    "CompoundId": ("bioetl.domain.value_objects.compound_ids", "CompoundId"),
    "CompoundSource": (
        "bioetl.domain.value_objects.compound_ids",
        "CompoundSource",
    ),
    "Concentration": (
        "bioetl.domain.value_objects.activity_values",
        "Concentration",
    ),
    "ConcentrationUnit": (
        "bioetl.domain.value_objects.activity_values",
        "ConcentrationUnit",
    ),
    "ConfidenceScore": ("bioetl.domain.value_objects.activity", "ConfidenceScore"),
    "DQEvaluationStatus": (
        "bioetl.domain.value_objects.dq_result",
        "DQEvaluationStatus",
    ),
    "HeavyAtomCount": (
        "bioetl.domain.value_objects.molecular_descriptors",
        "HeavyAtomCount",
    ),
    "HydrogenBondCount": (
        "bioetl.domain.value_objects.molecular_descriptors",
        "HydrogenBondCount",
    ),
    "InChI": ("bioetl.domain.value_objects.inchi", "InChI"),
    "InChIKey": ("bioetl.domain.value_objects.chemical", "InChIKey"),
    "LogP": ("bioetl.domain.value_objects.molecular_descriptors", "LogP"),
    "MolecularWeight": (
        "bioetl.domain.value_objects.chemical",
        "MolecularWeight",
    ),
    "OpenAlexId": ("bioetl.domain.value_objects.academic_ids", "OpenAlexId"),
    "PChemblValue": ("bioetl.domain.value_objects.activity_values", "PChemblValue"),
    "PolarSurfaceArea": (
        "bioetl.domain.value_objects.molecular_descriptors",
        "PolarSurfaceArea",
    ),
    "PubChemCid": ("bioetl.domain.value_objects.identifiers", "PubChemCid"),
    "PubMedId": ("bioetl.domain.value_objects.publications", "PubMedId"),
    "PublicationYear": (
        "bioetl.domain.value_objects.chemical",
        "PublicationYear",
    ),
    "RelationOperator": (
        "bioetl.domain.value_objects.activity",
        "RelationOperator",
    ),
    "RotatableBondCount": (
        "bioetl.domain.value_objects.molecular_descriptors",
        "RotatableBondCount",
    ),
    "SemanticScholarId": (
        "bioetl.domain.value_objects.academic_ids",
        "SemanticScholarId",
    ),
    "TaxonomyId": ("bioetl.domain.value_objects.taxonomy_id", "TaxonomyId"),
    "UniProtId": ("bioetl.domain.value_objects.identifiers", "UniProtId"),
    "ValueObject": ("bioetl.domain.value_objects.base", "ValueObject"),
    "validate_taxonomy_id": (
        "bioetl.domain.value_objects.taxonomy_id",
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

    value = getattr(import_module(module_name), attribute_name)
    globals()[name] = value
    return value


def __dir__() -> list[str]:
    """Return stable facade exports for introspection."""
    return sorted(set(globals()) | set(__all__))
