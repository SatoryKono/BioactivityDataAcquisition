"""Typed records for one target row and its evidence.

Derived classification fields stay null on ``invalid_input``. Local fields are
allowed only as empty values when ``local_status`` is ``not_supported``.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Diagnostic:
    """One component diagnostic. Errors stay here instead of an empty result."""

    code: str
    level: str
    message: str
    evidence_id: str | None = None


@dataclass(frozen=True, slots=True)
class EcNumber:
    """A parsed EC token. Partial numbers are not expanded or dropped."""

    raw: str
    valid: bool
    depth: int | None
    confirmed_levels: tuple[str, ...]
    category_name: str | None
    diagnostic: str | None


@dataclass(frozen=True, slots=True)
class RunProvenance:
    """Technical origin of one run. Unapproved versions stay null."""

    snapshot_id: str
    normalization_version: str | None
    rules_version: str | None
    schema_version: str | None
    retrieved_at: str
    run_started_at: str


@dataclass(frozen=True, slots=True)
class RawTargetRow:
    """One input row before normalization. Values are the original text."""

    input_row_id: str
    fields: dict[str, str | None]
    target_kind: str | None = None


@dataclass(frozen=True, slots=True)
class GlueFixture:
    """A proven glued identifier. The value is not repaired."""

    field: str
    original: str
    signs: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ValidatedInput:
    """Normalization output. Original text stays beside the normalized value."""

    input_row_id: str
    raw_fields: dict[str, str | None]
    normalized_fields: dict[str, str | None]
    target_id: str | None
    uniprot_accessions: tuple[str, ...]
    gene_symbol: str | None
    gene_id: str | None
    organism: str | None
    isoform_suffix: str | None
    isoform_id: str | None
    name: str | None
    synonyms: tuple[str, ...]
    keywords: tuple[str, ...]
    predicted_l1: str | None
    predicted_l2: str | None
    ec_raw: str | None
    ec_numbers: tuple[EcNumber, ...]
    target_kind: str | None
    taxon: str | None
    catalog_status: str | None
    input_validation_status: str
    input_errors: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...]
    row_sha256: str
    provenance: RunProvenance


@dataclass(frozen=True, slots=True)
class Evidence:
    """One child-table evidence record."""

    evidence_id: str
    input_row_id: str
    evidence_type: str
    source_id: str
    content: str
    run_id: str = ""


@dataclass(frozen=True, slots=True)
class MatchResult:
    """Matching output. ``matched`` requires a target id."""

    match_status: str | None
    matched_target_id: str | None
    candidate_target_ids: tuple[str, ...]
    match_method: tuple[str, ...]
    match_evidence_ids: tuple[str, ...]
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class ProviderAnnotation:
    """Raw provider payload plus the fields the direct layer may read."""

    target_id: str | None
    type_raw: str | None
    family_ids: tuple[str, ...]
    payload_sha256: str | None
    taxon: str | None
    raw_payload: str | None


@dataclass(frozen=True, slots=True)
class LocalInference:
    """Local layer. ``not_supported`` keeps the class empty."""

    local_status: str | None
    local_class: str | None
    local_subclasses: tuple[str, ...]
    local_rule_ids: tuple[str, ...]
    local_evidence_ids: tuple[str, ...]
    ec_categories: tuple[str, ...] = ()
    multiple_ec_categories: bool = False
    local_candidates: tuple[str, ...] = ()
    diagnostics: tuple[Diagnostic, ...] = ()


@dataclass(frozen=True, slots=True)
class ClassificationResult:
    """Final row. List fields are tuples; null means a scalar was not computed."""

    input_row_id: str
    snapshot_id: str
    input_validation_status: str
    input_errors: tuple[str, ...]
    match_status: str | None
    matched_target_id: str | None
    candidate_target_ids: tuple[str, ...]
    iuphar_annotation_status: str | None
    iuphar_class: str | None
    iuphar_subclass: str | None
    iuphar_class_candidates: tuple[str, ...]
    iuphar_type_raw: str | None
    iuphar_mapping_rule_id: str | None
    iuphar_mapping_version: str | None
    local_status: str | None
    local_class: str | None
    local_subclasses: tuple[str, ...]
    local_rule_ids: tuple[str, ...]
    effective_class: str | None
    effective_subclasses: tuple[str, ...]
    effective_source: str | None
    decision_status: str | None
    conflict_codes: tuple[str, ...]
    match_evidence_ids: tuple[str, ...]
    local_evidence_ids: tuple[str, ...]
    row_sha256: str
    provenance: RunProvenance
    diagnostics: tuple[Diagnostic, ...] = ()
