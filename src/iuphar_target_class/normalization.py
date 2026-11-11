"""Input normalization. Missing markers become None; original text stays."""

from __future__ import annotations

import re

from .models import (
    ClassificationResult,
    Diagnostic,
    EcNumber,
    GlueFixture,
    RawTargetRow,
    RunProvenance,
    ValidatedInput,
)
from .policy import BASE_MISSING_MARKERS, EC_CATEGORIES
from .stage0.io import canonical_json_bytes, sha256_bytes

_NAMED_MARKERS = frozenset(marker for marker in BASE_MISSING_MARKERS if marker)
_EC_NAMES = dict(EC_CATEGORIES)
_MULTI_FIELDS = frozenset({"uniprot", "synonyms", "ec", "keywords"})
_SCALAR_FIELDS = (
    "target_id",
    "gene_symbol",
    "gene_id",
    "organism",
    "isoform_suffix",
    "isoform_id",
    "name",
    "predicted_l1",
    "predicted_l2",
)
_KIND = frozenset({"protein", "complex"})


def normalize_missing(value: str | None) -> str | None:
    """Map the plan's base markers to None. Any other text is unchanged."""
    if value is None:
        return None
    if value.strip() == "" or value.strip() in _NAMED_MARKERS:
        return None
    return value


def normalize_identifiers(
    value: str | None,
    *,
    field: str,
    glue_fixtures: tuple[GlueFixture, ...],
) -> tuple[str | None, str | None]:
    """Return the normalized id and an error when a glue fixture matches.

    A glued value is not rewritten. ``920840`` stays ``920840``.
    """
    for fixture in glue_fixtures:
        if fixture.field == field and fixture.original == value and fixture.signs:
            return value, f"glued identifier in {field}"
    return normalize_missing(value), None


def parse_ec_numbers(raw: str | None) -> tuple[EcNumber, ...]:
    """Parse one EC field. Invalid tokens stay, with a diagnostic message."""
    normalized = normalize_missing(raw)
    if normalized is None:
        return ()
    return tuple(_parse_ec_token(token) for token in _split_multi(normalized))


def validate_input(
    row: RawTargetRow,
    *,
    provenance: RunProvenance,
    glue_fixtures: tuple[GlueFixture, ...] = (),
    catalog: frozenset[str] = frozenset(),
    snapshot_taxon: str | None = None,
) -> ValidatedInput:
    """Validate one row. An invalid row does not compute derived fields."""
    errors: list[str] = []
    if not row.input_row_id:
        errors.append("input_row_id is empty")
    if row.target_kind not in _KIND:
        errors.append("target_kind must be protein or complex")
    normalized: dict[str, str | None] = {}
    for field_name in (*_SCALAR_FIELDS, *_MULTI_FIELDS):
        original = row.fields.get(field_name)
        value, glue_error = normalize_identifiers(
            original,
            field=field_name,
            glue_fixtures=glue_fixtures,
        )
        normalized[field_name] = value
        if glue_error is not None:
            errors.append(glue_error)
    row_hash = sha256_bytes(canonical_json_bytes(row.fields))
    if errors:
        return _invalid(
            row,
            provenance,
            tuple(errors),
            row_hash,
        )
    diagnostics: list[Diagnostic] = []
    ec_numbers = parse_ec_numbers(row.fields.get("ec"))
    for number in ec_numbers:
        if not number.valid and number.diagnostic is not None:
            diagnostics.append(
                Diagnostic("invalid_ec", "warning", number.diagnostic),
            )
    taxon, taxon_diagnostic = _taxon(
        normalized.get("organism"),
        snapshot_taxon,
    )
    if taxon_diagnostic is not None:
        diagnostics.append(taxon_diagnostic)
    supplied = _supplied_ids(normalized)
    if not supplied:
        catalog_status: str | None = "not_applicable"
    elif any(identifier in catalog for identifier in supplied):
        catalog_status = "found"
    else:
        catalog_status = "not_found"
    return ValidatedInput(
        input_row_id=row.input_row_id,
        raw_fields=dict(row.fields),
        normalized_fields=normalized,
        target_id=normalized.get("target_id"),
        uniprot_accessions=_split_stored(normalized.get("uniprot")),
        gene_symbol=normalized.get("gene_symbol"),
        gene_id=normalized.get("gene_id"),
        organism=normalized.get("organism"),
        isoform_suffix=normalized.get("isoform_suffix"),
        isoform_id=normalized.get("isoform_id"),
        name=normalized.get("name"),
        synonyms=_split_stored(normalized.get("synonyms")),
        keywords=_split_stored(normalized.get("keywords")),
        predicted_l1=normalized.get("predicted_l1"),
        predicted_l2=normalized.get("predicted_l2"),
        ec_raw=row.fields.get("ec"),
        ec_numbers=ec_numbers,
        target_kind=row.target_kind,
        taxon=taxon,
        catalog_status=catalog_status,
        input_validation_status="valid",
        input_errors=(),
        diagnostics=tuple(diagnostics),
        row_sha256=row_hash,
        provenance=provenance,
    )


def validate_batch(
    rows: tuple[RawTargetRow, ...],
    *,
    provenance: RunProvenance,
    glue_fixtures: tuple[GlueFixture, ...] = (),
    catalog: frozenset[str] = frozenset(),
    snapshot_taxon: str | None = None,
) -> tuple[ValidatedInput, ...]:
    """Validate every row. One invalid row does not stop the batch."""
    return tuple(
        validate_input(
            row,
            provenance=provenance,
            glue_fixtures=glue_fixtures,
            catalog=catalog,
            snapshot_taxon=snapshot_taxon,
        )
        for row in rows
    )


def isolated_invalid_result(row: ValidatedInput) -> ClassificationResult:
    """Build the invalid_input contract: identity and provenance only."""
    if row.input_validation_status != "invalid_input":
        message = "isolated result requires invalid_input"
        raise ValueError(message)
    return ClassificationResult(
        input_row_id=row.input_row_id,
        snapshot_id=row.provenance.snapshot_id,
        input_validation_status="invalid_input",
        input_errors=row.input_errors,
        match_status=None,
        matched_target_id=None,
        candidate_target_ids=(),
        iuphar_annotation_status=None,
        iuphar_class=None,
        iuphar_subclass=None,
        iuphar_class_candidates=(),
        iuphar_type_raw=None,
        iuphar_mapping_rule_id=None,
        iuphar_mapping_version=None,
        local_status=None,
        local_class=None,
        local_subclasses=(),
        local_rule_ids=(),
        effective_class=None,
        effective_subclasses=(),
        effective_source=None,
        decision_status=None,
        conflict_codes=(),
        match_evidence_ids=(),
        local_evidence_ids=(),
        row_sha256=row.row_sha256,
        provenance=row.provenance,
        diagnostics=(),
    )


def require_approved_normalization(provenance: RunProvenance) -> None:
    """Refuse an accepted run while the marker version is unapproved."""
    if not (provenance.normalization_version or "").strip():
        message = "missing_markers version не утверждена"
        raise ValueError(message)


def _invalid(
    row: RawTargetRow,
    provenance: RunProvenance,
    errors: tuple[str, ...],
    row_hash: str,
) -> ValidatedInput:
    return ValidatedInput(
        input_row_id=row.input_row_id,
        raw_fields=dict(row.fields),
        normalized_fields={},
        target_id=None,
        uniprot_accessions=(),
        gene_symbol=None,
        gene_id=None,
        organism=None,
        isoform_suffix=None,
        isoform_id=None,
        name=None,
        synonyms=(),
        keywords=(),
        predicted_l1=None,
        predicted_l2=None,
        ec_raw=row.fields.get("ec"),
        ec_numbers=(),
        target_kind=row.target_kind,
        taxon=None,
        catalog_status=None,
        input_validation_status="invalid_input",
        input_errors=errors,
        diagnostics=(),
        row_sha256=row_hash,
        provenance=provenance,
    )


def _parse_ec_token(token: str) -> EcNumber:
    parts = token.split(".")
    if not 1 <= len(parts) <= 4 or not _ascii_digits(parts[0]):
        return _bad_ec(token)
    try:
        top = int(parts[0])
    except ValueError:
        return _bad_ec(token)
    if top not in _EC_NAMES:
        return _bad_ec(token)
    seen_dash = False
    depth = 0
    levels: list[str] = []
    prefix: list[str] = []
    for part in parts:
        if part == "-":
            seen_dash = True
            continue
        if seen_dash or not _ascii_digits(part):
            return _bad_ec(token)
        depth += 1
        prefix.append(part)
        levels.append(".".join(prefix))
    return EcNumber(
        raw=token,
        valid=True,
        depth=depth,
        confirmed_levels=tuple(levels),
        category_name=_EC_NAMES[top],
        diagnostic=None,
    )


def _ascii_digits(value: str) -> bool:
    return value.isascii() and value.isdigit()


def _bad_ec(token: str) -> EcNumber:
    return EcNumber(
        raw=token,
        valid=False,
        depth=None,
        confirmed_levels=(),
        category_name=None,
        diagnostic=f"invalid EC token: {token}",
    )


def _split_multi(value: str) -> tuple[str, ...]:
    return tuple(
        part.strip()
        for part in re.split(r"[;|]", value)
        if normalize_missing(part) is not None
    )


def _split_stored(value: str | None) -> tuple[str, ...]:
    if value is None:
        return ()
    return _split_multi(value)


def _supplied_ids(normalized: dict[str, str | None]) -> tuple[str, ...]:
    values: list[str] = []
    target_id = normalized.get("target_id")
    if target_id is not None:
        values.append(target_id)
    values.extend(_split_stored(normalized.get("uniprot")))
    gene_id = normalized.get("gene_id")
    if gene_id is not None:
        values.append(gene_id)
    return tuple(values)


def _taxon(
    organism: str | None,
    snapshot_taxon: str | None,
) -> tuple[str | None, Diagnostic | None]:
    if snapshot_taxon and organism and snapshot_taxon != organism:
        return snapshot_taxon, Diagnostic(
            "taxon_source_conflict",
            "warning",
            "organism differs from the snapshot taxon; GtoPdb taxon is used",
        )
    if snapshot_taxon:
        return snapshot_taxon, None
    return organism, None
