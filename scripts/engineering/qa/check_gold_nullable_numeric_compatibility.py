#!/usr/bin/env python3
"""Validate documented nullable numeric compatibility in Gold contracts."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DOC_PATH = "docs/04-reference/contracts/gold-schemas.md"

# Source marker identities for Pandera nullable-numeric evidence (python:S1192).
MARKER_PUBLICATION_YEAR_SERIES = "publication_year: Series[float]"
MARKER_CITATIONS_RECEIVED_SERIES = "citations_received: Series[float]"
MARKER_CITATIONS_MADE_SERIES = "citations_made: Series[float]"
MARKER_COERCE_TRUE = "coerce=True"
SOURCE_PUBLICATION_COMMON_SCHEMA = (
    "src/bioetl/domain/contracts/gold/_publication_common_schema.py"
)


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    """Source markers proving the Pandera compatibility convention is explicit."""

    path: str
    markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class NullableNumericSpec:
    """Expected nullable numeric compatibility for one Gold JSON contract."""

    category: str
    contract_path: str
    fields: tuple[str, ...]
    source_evidence: tuple[SourceEvidence, ...]


@dataclass(frozen=True, slots=True)
class NullableNumericFinding:
    """One nullable numeric compatibility validation finding."""

    kind: str
    category: str
    path: str
    field: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable finding payload."""
        return {
            "kind": self.kind,
            "category": self.category,
            "path": self.path,
            "field": self.field,
            "message": self.message,
        }


NULLABLE_NUMERIC_SPECS: tuple[NullableNumericSpec, ...] = (
    NullableNumericSpec(
        category="publication_year_and_citations",
        contract_path="docs/04-reference/contracts/gold/chembl_publication_v1.0.json",
        fields=("publication_year", "citations_received", "citations_made"),
        source_evidence=(
            SourceEvidence(
                "src/bioetl/domain/contracts/gold/_chembl_reference_publication_schemas.py",
                (
                    MARKER_PUBLICATION_YEAR_SERIES,
                    MARKER_CITATIONS_RECEIVED_SERIES,
                    MARKER_CITATIONS_MADE_SERIES,
                    MARKER_COERCE_TRUE,
                ),
            ),
        ),
    ),
    NullableNumericSpec(
        category="publication_year_and_citations",
        contract_path="docs/04-reference/contracts/gold/crossref_publication_v1.0.json",
        fields=("publication_year", "citations_received", "citations_made"),
        source_evidence=(
            SourceEvidence(
                SOURCE_PUBLICATION_COMMON_SCHEMA,
                (MARKER_PUBLICATION_YEAR_SERIES, MARKER_CITATIONS_MADE_SERIES),
            ),
            SourceEvidence(
                "src/bioetl/domain/contracts/gold/publications_crossref.py",
                (MARKER_CITATIONS_RECEIVED_SERIES, MARKER_COERCE_TRUE),
            ),
        ),
    ),
    NullableNumericSpec(
        category="publication_year_and_citations",
        contract_path="docs/04-reference/contracts/gold/openalex_publication_v1.0.json",
        fields=("publication_year", "citations_received", "citations_made"),
        source_evidence=(
            SourceEvidence(
                SOURCE_PUBLICATION_COMMON_SCHEMA,
                (MARKER_PUBLICATION_YEAR_SERIES, MARKER_CITATIONS_MADE_SERIES),
            ),
            SourceEvidence(
                "src/bioetl/domain/contracts/gold/publications_openalex.py",
                (MARKER_CITATIONS_RECEIVED_SERIES, MARKER_COERCE_TRUE),
            ),
        ),
    ),
    NullableNumericSpec(
        category="publication_year_and_citations",
        contract_path="docs/04-reference/contracts/gold/pubmed_publication_v1.0.json",
        fields=("publication_year", "citations_made"),
        source_evidence=(
            SourceEvidence(
                SOURCE_PUBLICATION_COMMON_SCHEMA,
                (MARKER_PUBLICATION_YEAR_SERIES, MARKER_CITATIONS_MADE_SERIES),
            ),
        ),
    ),
    NullableNumericSpec(
        category="publication_year_and_citations",
        contract_path=(
            "docs/04-reference/contracts/gold/semanticscholar_publication_v1.0.json"
        ),
        fields=("publication_year", "citations_received", "citations_made"),
        source_evidence=(
            SourceEvidence(
                SOURCE_PUBLICATION_COMMON_SCHEMA,
                (MARKER_PUBLICATION_YEAR_SERIES, MARKER_CITATIONS_MADE_SERIES),
            ),
            SourceEvidence(
                "src/bioetl/domain/contracts/gold/publications_semanticscholar.py",
                (MARKER_CITATIONS_RECEIVED_SERIES, MARKER_COERCE_TRUE),
            ),
        ),
    ),
    NullableNumericSpec(
        category="molecule_descriptors",
        contract_path="docs/04-reference/contracts/gold/chembl_molecule_v1.0.json",
        fields=(
            "logp",
            "molecular_weight",
            "polar_surface_area",
            "hba_count",
            "hbd_count",
        ),
        source_evidence=(
            SourceEvidence(
                "src/bioetl/domain/contracts/gold/_chembl_molecule_protein_schemas.py",
                (
                    "logp: Series[float]",
                    "molecular_weight: Series[float]",
                    "polar_surface_area: Series[float]",
                    "hba_count: Series[float]",
                    "hbd_count: Series[float]",
                    MARKER_COERCE_TRUE,
                ),
            ),
        ),
    ),
    NullableNumericSpec(
        category="molecule_descriptors",
        contract_path="docs/04-reference/contracts/gold/pubchem_compound_v1.0.json",
        fields=("molecular_weight", "xlogp", "tpsa"),
        source_evidence=(
            SourceEvidence(
                "src/bioetl/domain/contracts/gold/pubchem.py",
                (
                    "molecular_weight: Series[float]",
                    "logp: Series[float]",
                    'alias="xlogp"',
                    "polar_surface_area: Series[float]",
                    'alias="tpsa"',
                    MARKER_COERCE_TRUE,
                ),
            ),
        ),
    ),
    NullableNumericSpec(
        category="activity_measurements",
        contract_path="docs/04-reference/contracts/gold/chembl_activity_v1.0.json",
        fields=(
            "value",
            "upper_value",
            "standard_value",
            "standard_upper_value",
            "pchembl_value",
            "ligand_efficiency_bei",
            "ligand_efficiency_le",
            "ligand_efficiency_lle",
            "ligand_efficiency_sei",
            "publication_year",
        ),
        source_evidence=(
            SourceEvidence(
                "src/bioetl/domain/contracts/gold/_chembl_activity_assay_schemas.py",
                (
                    "value: Series[float]",
                    "upper_value: Series[float]",
                    "standard_value: Series[float]",
                    "standard_upper_value: Series[float]",
                    "pchembl_value: Series[float]",
                    "ligand_efficiency_bei: Series[float]",
                    "ligand_efficiency_le: Series[float]",
                    "ligand_efficiency_lle: Series[float]",
                    "ligand_efficiency_sei: Series[float]",
                    MARKER_PUBLICATION_YEAR_SERIES,
                    MARKER_COERCE_TRUE,
                ),
            ),
        ),
    ),
)

REQUIRED_DOC_MARKERS = (
    "Nullable Numeric Compatibility",
    "Publication Nullable Integer Compatibility",
    "Molecule Descriptor Numeric Compatibility",
    "Activity Measurement Numeric Compatibility",
    "check_gold_nullable_numeric_compatibility.py --check",
)


def _load_json(path: Path) -> dict[str, object]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected JSON object in {path}")


def _finding(
    *,
    spec: NullableNumericSpec,
    kind: str,
    path: str,
    field: str,
    message: str,
) -> NullableNumericFinding:
    return NullableNumericFinding(
        kind=kind,
        category=spec.category,
        path=path,
        field=field,
        message=message,
    )


def _validate_contract_fields(
    repo_root: Path,
    spec: NullableNumericSpec,
) -> list[NullableNumericFinding]:
    findings: list[NullableNumericFinding] = []
    payload = _load_json(repo_root / spec.contract_path)
    properties = payload.get("properties", {})
    if not isinstance(properties, dict):
        return [
            _finding(
                spec=spec,
                kind="missing_properties",
                path=spec.contract_path,
                field="<properties>",
                message=f"{spec.contract_path} has no JSON properties object",
            )
        ]

    for field in spec.fields:
        field_schema = properties.get(field)
        if not isinstance(field_schema, dict):
            findings.append(
                _finding(
                    spec=spec,
                    kind="missing_field",
                    path=spec.contract_path,
                    field=field,
                    message=f"{spec.contract_path} does not define {field!r}",
                )
            )
            continue
        field_type = field_schema.get("type")
        nullable = field_schema.get("nullable")
        if field_type != ["number", "null"] or nullable is not True:
            findings.append(
                _finding(
                    spec=spec,
                    kind="numeric_type_mismatch",
                    path=spec.contract_path,
                    field=field,
                    message=(
                        f"{spec.contract_path}:{field} expected "
                        "type=['number', 'null'] and nullable=true, got "
                        f"type={field_type!r}, nullable={nullable!r}"
                    ),
                )
            )
    return findings


def _validate_source_evidence(
    repo_root: Path,
    spec: NullableNumericSpec,
) -> list[NullableNumericFinding]:
    findings: list[NullableNumericFinding] = []
    for evidence in spec.source_evidence:
        source = (repo_root / evidence.path).read_text(encoding="utf-8")
        for marker in evidence.markers:
            if marker in source:
                continue
            findings.append(
                _finding(
                    spec=spec,
                    kind="missing_source_marker",
                    path=evidence.path,
                    field=marker,
                    message=f"{evidence.path} is missing compatibility marker {marker!r}",
                )
            )
    return findings


def _validate_doc_markers(repo_root: Path) -> list[NullableNumericFinding]:
    doc_source = (repo_root / DOC_PATH).read_text(encoding="utf-8")
    findings: list[NullableNumericFinding] = []
    sentinel = NULLABLE_NUMERIC_SPECS[0]
    for marker in REQUIRED_DOC_MARKERS:
        if marker in doc_source:
            continue
        findings.append(
            _finding(
                spec=sentinel,
                kind="missing_doc_marker",
                path=DOC_PATH,
                field=marker,
                message=f"{DOC_PATH} is missing nullable numeric marker {marker!r}",
            )
        )
    return findings


def validate_nullable_numeric_compatibility(
    repo_root: Path = REPO_ROOT,
    specs: tuple[NullableNumericSpec, ...] = NULLABLE_NUMERIC_SPECS,
) -> tuple[NullableNumericFinding, ...]:
    """Return nullable numeric compatibility findings for Gold contracts."""
    findings: list[NullableNumericFinding] = []
    for spec in specs:
        findings.extend(_validate_contract_fields(repo_root, spec))
        findings.extend(_validate_source_evidence(repo_root, spec))
    findings.extend(_validate_doc_markers(repo_root))
    return tuple(findings)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate nullable numeric compatibility in Gold contracts.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail with a non-zero exit code when findings are present",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable validation output",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root containing docs and source contracts",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    findings = validate_nullable_numeric_compatibility(args.repo_root)
    if args.json:
        payload = {
            "ok": not findings,
            "finding_count": len(findings),
            "findings": [finding.as_dict() for finding in findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif findings:
        print("[gold-nullable-numeric-compatibility] validation failed")
        for finding in findings:
            print(f"- {finding.message} ({finding.path})")
    else:
        print("[gold-nullable-numeric-compatibility] ok")

    return 1 if args.check and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
