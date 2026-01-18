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
from bioetl.domain.value_objects.bronze_result import BronzeWriteResult
from bioetl.domain.value_objects.chemical import (
    SMILES,
    InChIKey,
    MolecularWeight,
    PublicationYear,
)
from bioetl.domain.value_objects.compound_ids import (
    AssayId,
    CompoundId,
    CompoundIdUnion,
    CompoundSource,
)
from bioetl.domain.value_objects.dq_metrics import (
    BatchDQMetrics,
    ColumnStats,
    SchemaDriftInfo,
)
from bioetl.domain.value_objects.dq_report import (
    AnomalyDetectionResult,
    AnomalyMetric,
    BronzeDQCheckType,
    BronzeDQReport,
    BusinessRuleResult,
    BusinessRulesResult,
    CategoricalDistribution,
    CompletenessResult,
    ContentHashIntegrityResult,
    DataFreshnessResult,
    DeduplicationStatsResult,
    DQCheckResult,
    DQCheckStatus,
    DQReportFormat,
    DQReportStatus,
    DQReportSummary,
    DQThresholds,
    DriftLevel,
    EncodingValidationResult,
    FieldPresenceResult,
    FileIntegrityResult,
    ForeignKeyResult,
    GoldDQCheckType,
    GoldDQReport,
    MedallionLayer,
    NullRateResult,
    NumericDistribution,
    RecordCountResult,
    ReferentialIntegrityResult,
    SCDIntegrityResult,
    SchemaDriftResult,
    SchemaSnapshotResult,
    SilverDQCheckType,
    SilverDQReport,
    StatisticalMetric,
    StatisticalProfileResult,
    TypeConformanceResult,
    UniquenessResult,
    ValueDistributionResult,
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
from bioetl.domain.value_objects.run_context import RunContext
from bioetl.domain.value_objects.silver_result import SilverWriteResult
from bioetl.domain.value_objects.taxonomy_id import (
    TaxonomyId,
    validate_taxonomy_id,
    validate_taxonomy_id_str,
)

__all__ = [
    "DOI",
    "ISSN",
    "ORCID",
    "SMILES",
    "ActivityType",
    "ActivityValue",
    "AnomalyDetectionResult",
    "AnomalyMetric",
    "AssayId",
    "BatchDQMetrics",
    "BronzeDQCheckType",
    "BronzeDQReport",
    "BronzeWriteResult",
    "BusinessRuleResult",
    "BusinessRulesResult",
    "CategoricalDistribution",
    "ChemblId",
    "ColumnStats",
    "CompletenessResult",
    "CompoundId",
    "CompoundIdUnion",
    "CompoundSource",
    "Concentration",
    "ConcentrationUnit",
    "ConfidenceScore",
    "ContentHashIntegrityResult",
    "DQCheckResult",
    "DQCheckStatus",
    "DQEvaluationStatus",
    "DQReportFormat",
    "DQReportStatus",
    "DQReportSummary",
    "DQResult",
    "DQThresholds",
    "DataFreshnessResult",
    "DeduplicationStatsResult",
    "DriftLevel",
    "EncodingValidationResult",
    "FieldPresenceResult",
    "FileIntegrityResult",
    "ForeignKeyResult",
    "GoldDQCheckType",
    "GoldDQReport",
    "InChIKey",
    "MedallionLayer",
    "MolecularWeight",
    "NullRateResult",
    "NumericDistribution",
    "OpenAlexId",
    "PChemblValue",
    "PubChemCid",
    "PubMedId",
    "PublicationYear",
    "RecordCountResult",
    "ReferentialIntegrityResult",
    "RelationOperator",
    "RunContext",
    "SCDIntegrityResult",
    "SchemaDriftInfo",
    "SchemaDriftResult",
    "SchemaSnapshotResult",
    "SemanticScholarId",
    "SilverDQCheckType",
    "SilverDQReport",
    "SilverWriteResult",
    "StatisticalMetric",
    "StatisticalProfileResult",
    "TaxonomyId",
    "TypeConformanceResult",
    "UniProtId",
    "UniquenessResult",
    "ValueDistributionResult",
    "ValueObject",
    "validate_taxonomy_id",
    "validate_taxonomy_id_str",
]
