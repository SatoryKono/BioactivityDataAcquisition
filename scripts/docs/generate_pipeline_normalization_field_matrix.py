#!/usr/bin/env python3
"""Generate deterministic normalization field-matrix artifacts for all pipelines."""

from __future__ import annotations

import argparse
import csv
import io
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if __package__ in {None, ""}:
    repo_root = Path(__file__).resolve().parents[2]
    sys.path.insert(0, str(repo_root))
    sys.path.insert(0, str(repo_root / "src"))

from bioetl.application.composite.join_key_normalization import (
    JOIN_KEY_NORMALIZATION_POLICIES,
)
from bioetl.application.core.normalization_fallbacks import (
    is_date_field,
    is_doi_field,
    is_pmid_field,
    is_smiles_field,
)
from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
from bioetl.domain.normalization.profiles import resolve_normalization_profile
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_CELL_LINE_SCHEMA,
    CHEMBL_COMPOUND_RECORD_SCHEMA,
    CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    CHEMBL_DOCUMENT_TERM_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_PROTEIN_CLASS_SCHEMA,
    CHEMBL_PUBLICATION_SCHEMA,
    CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    CHEMBL_TARGET_COMPONENT_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
    CHEMBL_TISSUE_SCHEMA,
    CROSSREF_PUBLICATION_SCHEMA,
    OPENALEX_PUBLICATION_SCHEMA,
    PUBCHEM_COMPOUND_SCHEMA,
    PUBMED_PUBLICATION_SCHEMA,
    SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    UNIPROT_ID_MAPPING_SCHEMA,
    UNIPROT_PROTEIN_SCHEMA,
)

if TYPE_CHECKING:
    import pyarrow as pa

DEFAULT_OUT_DIR = Path("docs/reports/generated/pipeline_normalization_field_matrix")
CSV_NAME = "pipeline_normalization_field_matrix.csv"
MD_NAME = "pipeline_normalization_field_matrix.md"

CSV_COLUMNS = (
    "pipeline_name",
    "pipeline_kind",
    "field_name",
    "field_type",
    "normalization_source",
    "normalizer",
    "normalization_summary",
    "include_in_content_hash",
    "set_like",
    "notes",
)

FALLBACK_BUSINESS = "fallback_business"
FALLBACK_TECHNICAL_PASSTHROUGH = "fallback_technical_passthrough"

ENTITY_SILVER_SCHEMA_REGISTRY: dict[str, Any] = {
    "chembl_activity": CHEMBL_ACTIVITY_SCHEMA,
    "chembl_assay": CHEMBL_ASSAY_SCHEMA,
    "chembl_assay_parameters": CHEMBL_ASSAY_PARAMETERS_SCHEMA,
    "chembl_cell_line": CHEMBL_CELL_LINE_SCHEMA,
    "chembl_compound_record": CHEMBL_COMPOUND_RECORD_SCHEMA,
    "chembl_molecule": CHEMBL_MOLECULE_SCHEMA,
    "chembl_protein_class": CHEMBL_PROTEIN_CLASS_SCHEMA,
    "chembl_publication": CHEMBL_PUBLICATION_SCHEMA,
    "chembl_publication_similarity": CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
    "chembl_publication_term": CHEMBL_DOCUMENT_TERM_SCHEMA,
    "chembl_subcellular_fraction": CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
    "chembl_target": CHEMBL_TARGET_SCHEMA,
    "chembl_target_component": CHEMBL_TARGET_COMPONENT_SCHEMA,
    "chembl_tissue": CHEMBL_TISSUE_SCHEMA,
    "crossref_publication": CROSSREF_PUBLICATION_SCHEMA,
    "openalex_publication": OPENALEX_PUBLICATION_SCHEMA,
    "pubchem_compound": PUBCHEM_COMPOUND_SCHEMA,
    "pubmed_publication": PUBMED_PUBLICATION_SCHEMA,
    "semanticscholar_publication": SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
    "uniprot_idmapping": UNIPROT_ID_MAPPING_SCHEMA,
    "uniprot_protein": UNIPROT_PROTEIN_SCHEMA,
}

COMPOSITE_GOLD_SCHEMA_TYPE_REGISTRY: dict[str, str] = {
    "composite_activity": "unknown",
    "composite_assay": "unknown",
    "composite_molecule": "unknown",
    "composite_publication": "unknown",
    "composite_target": "unknown",
}


def _normalizer_name(normalizer: Any) -> str:
    return getattr(normalizer, "__name__", type(normalizer).__name__)


def _entity_config_paths() -> list[Path]:
    return sorted(Path("configs/entities").glob("*/*.yaml"))


def _composite_config_paths() -> list[Path]:
    return sorted(Path("configs/composites").glob("*.yaml"))


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    return payload if isinstance(payload, dict) else {}


def _render_bool(value: bool | None) -> str:
    if value is None:
        return ""
    return "true" if value else "false"


def _looks_like_string_type(type_name: str) -> bool:
    lowered = type_name.lower()
    return "string" in lowered or "large_string" in lowered


def _normalize_summary_from_policy(*, trim: bool, lowercase: bool) -> str:
    if trim and lowercase:
        return "Trim surrounding whitespace and lowercase join-key text."
    if trim:
        return "Trim surrounding whitespace for join-key text."
    if lowercase:
        return "Lowercase join-key text."
    return "Composite join key is preserved as-is by explicit no-op policy."


def _fallback_contract(
    rule_set: NormalizationRulesPolicy,
    *,
    field_name: str,
    field_type: str,
) -> tuple[str, str, str]:
    if field_name in rule_set.passthrough_fields:
        return (
            FALLBACK_TECHNICAL_PASSTHROUGH,
            "passthrough",
            "Field is passed through unchanged by the canonical fallback normalization seam.",
        )
    if field_name.startswith("_"):
        return (
            FALLBACK_TECHNICAL_PASSTHROUGH,
            "passthrough",
            "Technical field appears in the normalization inventory only; "
            "persisted-row publication is governed separately by the "
            "Silver/Gold storage contract.",
        )
    if field_name in rule_set.title_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_title",
            "Normalize title text through HTML/entity cleanup and whitespace normalization.",
        )
    if field_name in rule_set.abstract_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_abstract",
            "Normalize abstract text through HTML/entity cleanup and whitespace normalization.",
        )
    if field_name in rule_set.oa_status_fields:
        return (
            FALLBACK_BUSINESS,
            "normalize_oa_status",
            "Trim textual OA status and lowercase the resulting value.",
        )
    if is_doi_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_profile_doi",
            "Normalize DOI through the canonical fallback identifier helper.",
        )
    if is_pmid_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_profile_pmid",
            "Normalize PMID through the canonical fallback identifier helper.",
        )
    if is_date_field(field_name, rule_set=rule_set):
        return (
            FALLBACK_BUSINESS,
            "normalize_partial_date",
            "Canonicalize supported date text to the stable partial-date representation.",
        )
    if is_smiles_field(field_name):
        return (
            FALLBACK_BUSINESS,
            "SMILES.from_raw(mode=soft)",
            "Validate and trim SMILES text; invalid values collapse to None.",
        )
    if _looks_like_string_type(field_type):
        return (
            FALLBACK_BUSINESS,
            "normalize_string + canonicalize_json_string(json-like)",
            "Trim string values, collapse blanks to None, and canonicalize JSON-looking string payloads.",
        )
    return (
        FALLBACK_BUSINESS,
        "preserve_non_string",
        "No field-specific fallback normalizer is applied; non-string values are preserved as-is.",
    )


def _build_entity_rows_for_pipeline(
    *,
    pipeline_name: str,
    provider: str,
    entity: str,
    schema: pa.Schema,
) -> list[dict[str, str]]:
    profile = resolve_normalization_profile(provider, entity)
    rule_set = NormalizationRulesPolicy()
    rows: list[dict[str, str]] = []
    for field_name in schema.names:
        field = schema.field(field_name)
        field_type = str(field.type)
        profile_rule = None if profile is None else profile.rule_for(field_name)
        if profile_rule is not None:
            rows.append(
                {
                    "pipeline_name": pipeline_name,
                    "pipeline_kind": "entity",
                    "field_name": field_name,
                    "field_type": field_type,
                    "normalization_source": "profile",
                    "normalizer": _normalizer_name(profile_rule.normalizer),
                    "normalization_summary": profile_rule.notes or "",
                    "include_in_content_hash": _render_bool(profile_rule.include_in_hash),
                    "set_like": _render_bool(profile_rule.set_like),
                    "notes": profile_rule.notes or "",
                }
            )
            continue

        source, normalizer, summary = _fallback_contract(
            rule_set,
            field_name=field_name,
            field_type=field_type,
        )
        rows.append(
            {
                "pipeline_name": pipeline_name,
                "pipeline_kind": "entity",
                "field_name": field_name,
                "field_type": field_type,
                "normalization_source": source,
                "normalizer": normalizer,
                "normalization_summary": summary,
                "include_in_content_hash": "",
                "set_like": "false",
                "notes": "",
            }
        )
    return rows


def _iter_composite_fields(payload: dict[str, object]) -> list[str]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return []
    merge = composite.get("merge")
    if not isinstance(merge, dict):
        return []
    column_groups = merge.get("column_groups")
    if not isinstance(column_groups, list):
        return []

    ordered: list[str] = []
    seen: set[str] = set()
    for group in column_groups:
        if not isinstance(group, dict):
            continue
        fields = group.get("fields")
        if not isinstance(fields, list):
            continue
        for field_name in fields:
            if not isinstance(field_name, str) or field_name in seen:
                continue
            seen.add(field_name)
            ordered.append(field_name)
    return ordered


def _iter_composite_join_keys(payload: dict[str, object]) -> set[str]:
    composite = payload.get("composite")
    if not isinstance(composite, dict):
        return set()

    keys: set[str] = set()
    dependencies = composite.get("dependencies")
    if isinstance(dependencies, list):
        for dependency in dependencies:
            if not isinstance(dependency, dict):
                continue
            join_keys = dependency.get("join_keys")
            if isinstance(join_keys, list):
                keys.update(str(key) for key in join_keys if isinstance(key, str))

    enrichers = composite.get("enrichers")
    if isinstance(enrichers, list):
        for enricher in enrichers:
            if not isinstance(enricher, dict):
                continue
            join_keys = enricher.get("join_keys")
            if isinstance(join_keys, list):
                keys.update(str(key) for key in join_keys if isinstance(key, str))
    return keys


def _build_composite_rows_for_pipeline(
    *,
    pipeline_name: str,
    payload: dict[str, object],
) -> list[dict[str, str]]:
    join_keys = _iter_composite_join_keys(payload)
    rows: list[dict[str, str]] = []
    for field_name in _iter_composite_fields(payload):
        policy = JOIN_KEY_NORMALIZATION_POLICIES.get(field_name)
        if field_name in join_keys and policy is not None:
            source = "composite_join_key_policy"
            normalizer = "join_key_policy"
            summary = _normalize_summary_from_policy(
                trim=policy.trim,
                lowercase=policy.lowercase,
            )
            notes = "Applied only while resolving and comparing composite join keys."
        else:
            source = "upstream_inherited"
            normalizer = "none"
            summary = (
                "No composite-specific field normalizer is defined; field is inherited "
                "from already-normalized upstream records."
            )
            notes = (
                "Composite normalization is key-oriented; non-key fields preserve upstream semantics."
            )
        rows.append(
            {
                "pipeline_name": pipeline_name,
                "pipeline_kind": "composite",
                "field_name": field_name,
                "field_type": COMPOSITE_GOLD_SCHEMA_TYPE_REGISTRY.get(
                    pipeline_name, "unknown"
                ),
                "normalization_source": source,
                "normalizer": normalizer,
                "normalization_summary": summary,
                "include_in_content_hash": "",
                "set_like": "false",
                "notes": notes,
            }
        )
    return rows


def build_field_matrix_rows() -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []

    for config_path in _entity_config_paths():
        payload = _load_yaml(config_path)
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        pipeline_name = str(pipeline.get("pipeline_name", "")).strip()
        if not pipeline_name:
            continue
        provider = str(payload.get("provider", "")).strip()
        entity = str(payload.get("entity", "")).strip()
        schema = ENTITY_SILVER_SCHEMA_REGISTRY.get(pipeline_name)
        if schema is None:
            raise ValueError(f"Missing Silver schema registry entry for {pipeline_name}")
        rows.extend(
            _build_entity_rows_for_pipeline(
                pipeline_name=pipeline_name,
                provider=provider,
                entity=entity,
                schema=schema,
            )
        )

    for config_path in _composite_config_paths():
        payload = _load_yaml(config_path)
        composite = payload.get("composite")
        if not isinstance(composite, dict):
            continue
        pipeline_name = str(composite.get("name", "")).strip()
        if not pipeline_name:
            continue
        rows.extend(
            _build_composite_rows_for_pipeline(
                pipeline_name=pipeline_name,
                payload=payload,
            )
        )

    return rows


def render_csv(rows: list[dict[str, str]]) -> str:
    output = io.StringIO()
    writer = csv.DictWriter(
        output,
        fieldnames=list(CSV_COLUMNS),
        lineterminator="\n",
    )
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue()


def render_markdown(rows: list[dict[str, str]]) -> str:
    headers = list(CSV_COLUMNS)
    lines = [
        "# Pipeline Normalization Field Matrix",
        "",
        "Generated from active pipeline configs, Silver schemas, and current normalization code paths.",
        "",
        "This matrix is a normalization inventory, not a persisted-row publication contract.",
        "Occurrence-scoped provenance fields may appear here because normalization or config policy still references them,",
        "but canonical Silver/Gold row contracts are defined by provider references and Gold contract exports.",
        "",
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join("---" for _ in headers) + " |",
    ]
    for row in rows:
        lines.append("| " + " | ".join(row[header] for header in headers) + " |")
    lines.append("")
    return "\n".join(lines)


def build_artifacts() -> dict[str, str]:
    rows = build_field_matrix_rows()
    return {
        CSV_NAME: render_csv(rows),
        MD_NAME: render_markdown(rows),
    }


def write_artifacts(out_dir: Path) -> dict[str, object]:
    out_dir.mkdir(parents=True, exist_ok=True)
    artifacts = build_artifacts()
    for name, payload in artifacts.items():
        (out_dir / name).write_text(payload, encoding="utf-8")
    return {
        "out_dir": str(out_dir),
        "rows": len(build_field_matrix_rows()),
    }


def check_artifacts(out_dir: Path) -> int:
    artifacts = build_artifacts()
    for name, payload in artifacts.items():
        path = out_dir / name
        if not path.exists():
            return 1
        if path.read_text(encoding="utf-8") != payload:
            return 1
    return 0


def _arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate deterministic normalization field-matrix artifacts for all pipelines."
    )
    parser.add_argument(
        "--out-dir",
        type=Path,
        default=DEFAULT_OUT_DIR,
        help="Output directory for generated artifacts.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Exit with status 1 when artifacts on disk differ from generated output.",
    )
    return parser


def main() -> int:
    args = _arg_parser().parse_args()
    out_dir = args.out_dir.resolve()
    if args.check:
        return check_artifacts(out_dir)
    result = write_artifacts(out_dir)
    print(yaml.safe_dump(result, sort_keys=False), end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
