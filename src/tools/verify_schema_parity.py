"""Verify Silver<->Gold schema parity and primary key coverage.

Uses a baseline file to track known pre-existing field differences.
Only NEW mismatches (not in the baseline) trigger blocking failures.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path

import yaml

from bioetl.domain.contracts import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLAssayParametersGoldSchema,
    ChEMBLCellLineGoldSchema,
    ChEMBLCompoundRecordGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLProteinClassGoldSchema,
    ChEMBLPublicationGoldSchema,
    ChEMBLPublicationSimilarityGoldSchema,
    ChEMBLPublicationTermGoldSchema,
    ChEMBLSubcellularFractionGoldSchema,
    ChEMBLTargetComponentGoldSchema,
    ChEMBLTargetGoldSchema,
    ChEMBLTissueGoldSchema,
    CrossRefPublicationGoldSchema,
    OpenAlexPublicationGoldSchema,
    PubChemCompoundGoldSchema,
    PubMedPublicationGoldSchema,
    SemanticScholarPublicationGoldSchema,
    UniProtIDMappingGoldSchema,
    UniProtProteinGoldSchema,
)
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

PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASELINE_PATH = Path(__file__).resolve().parent / "schema_parity_baseline.json"


@dataclass(frozen=True)
class SchemaPair:
    """Silver/Gold schema pair with pipeline config for PK loading."""

    name: str
    silver_schema: object
    gold_model: type
    config_path: str


SCHEMA_PAIRS: tuple[SchemaPair, ...] = (
    SchemaPair(
        "chembl_activity",
        CHEMBL_ACTIVITY_SCHEMA,
        ChEMBLActivityGoldSchema,
        "configs/entities/chembl/activity.yaml",
    ),
    SchemaPair(
        "chembl_assay",
        CHEMBL_ASSAY_SCHEMA,
        ChEMBLAssayGoldSchema,
        "configs/entities/chembl/assay.yaml",
    ),
    SchemaPair(
        "chembl_assay_parameters",
        CHEMBL_ASSAY_PARAMETERS_SCHEMA,
        ChEMBLAssayParametersGoldSchema,
        "configs/entities/chembl/assay_parameters.yaml",
    ),
    SchemaPair(
        "chembl_cell_line",
        CHEMBL_CELL_LINE_SCHEMA,
        ChEMBLCellLineGoldSchema,
        "configs/entities/chembl/cell_line.yaml",
    ),
    SchemaPair(
        "chembl_compound_record",
        CHEMBL_COMPOUND_RECORD_SCHEMA,
        ChEMBLCompoundRecordGoldSchema,
        "configs/entities/chembl/compound_record.yaml",
    ),
    SchemaPair(
        "chembl_document",
        CHEMBL_PUBLICATION_SCHEMA,
        ChEMBLPublicationGoldSchema,
        "configs/entities/chembl/publication.yaml",
    ),
    SchemaPair(
        "chembl_document_similarity",
        CHEMBL_DOCUMENT_SIMILARITY_SCHEMA,
        ChEMBLPublicationSimilarityGoldSchema,
        "configs/entities/chembl/publication_similarity.yaml",
    ),
    SchemaPair(
        "chembl_document_term",
        CHEMBL_DOCUMENT_TERM_SCHEMA,
        ChEMBLPublicationTermGoldSchema,
        "configs/entities/chembl/publication_term.yaml",
    ),
    SchemaPair(
        "chembl_molecule",
        CHEMBL_MOLECULE_SCHEMA,
        ChEMBLMoleculeGoldSchema,
        "configs/entities/chembl/molecule.yaml",
    ),
    SchemaPair(
        "chembl_protein_class",
        CHEMBL_PROTEIN_CLASS_SCHEMA,
        ChEMBLProteinClassGoldSchema,
        "configs/entities/chembl/protein_class.yaml",
    ),
    SchemaPair(
        "chembl_target",
        CHEMBL_TARGET_SCHEMA,
        ChEMBLTargetGoldSchema,
        "configs/entities/chembl/target.yaml",
    ),
    SchemaPair(
        "chembl_target_component",
        CHEMBL_TARGET_COMPONENT_SCHEMA,
        ChEMBLTargetComponentGoldSchema,
        "configs/entities/chembl/target_component.yaml",
    ),
    SchemaPair(
        "chembl_tissue",
        CHEMBL_TISSUE_SCHEMA,
        ChEMBLTissueGoldSchema,
        "configs/entities/chembl/tissue.yaml",
    ),
    SchemaPair(
        "chembl_subcellular_fraction",
        CHEMBL_SUBCELLULAR_FRACTION_SCHEMA,
        ChEMBLSubcellularFractionGoldSchema,
        "configs/entities/chembl/subcellular_fraction.yaml",
    ),
    SchemaPair(
        "pubchem_compound",
        PUBCHEM_COMPOUND_SCHEMA,
        PubChemCompoundGoldSchema,
        "configs/entities/pubchem/compound.yaml",
    ),
    SchemaPair(
        "pubmed_publication",
        PUBMED_PUBLICATION_SCHEMA,
        PubMedPublicationGoldSchema,
        "configs/entities/pubmed/publication.yaml",
    ),
    SchemaPair(
        "crossref_publication",
        CROSSREF_PUBLICATION_SCHEMA,
        CrossRefPublicationGoldSchema,
        "configs/entities/crossref/publication.yaml",
    ),
    SchemaPair(
        "openalex_publication",
        OPENALEX_PUBLICATION_SCHEMA,
        OpenAlexPublicationGoldSchema,
        "configs/entities/openalex/publication.yaml",
    ),
    SchemaPair(
        "semanticscholar_publication",
        SEMANTICSCHOLAR_PUBLICATION_SCHEMA,
        SemanticScholarPublicationGoldSchema,
        "configs/entities/semanticscholar/publication.yaml",
    ),
    SchemaPair(
        "uniprot_protein",
        UNIPROT_PROTEIN_SCHEMA,
        UniProtProteinGoldSchema,
        "configs/entities/uniprot/protein.yaml",
    ),
    SchemaPair(
        "uniprot_idmapping",
        UNIPROT_ID_MAPPING_SCHEMA,
        UniProtIDMappingGoldSchema,
        "configs/entities/uniprot/idmapping.yaml",
    ),
)


def _load_baseline() -> dict[str, dict[str, list[str]]]:
    """Load known field differences from baseline JSON."""
    if not BASELINE_PATH.exists():
        return {}
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    # Remove metadata keys
    return {k: v for k, v in data.items() if isinstance(v, dict)}


def _save_baseline(baseline: dict[str, dict[str, list[str]]]) -> None:
    """Write current differences to baseline JSON."""
    output: dict[str, object] = {
        "description": (
            "Known Silver<->Gold field differences. Only NEW mismatches not in "
            "this baseline trigger blocking failures. Update with: "
            "python src/tools/verify_schema_parity.py --update-baseline"
        ),
    }
    output.update(baseline)
    BASELINE_PATH.write_text(
        json.dumps(output, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )


def get_primary_keys(config_path: str) -> list[str]:
    """Load business primary keys from unified entity config."""
    absolute_path = PROJECT_ROOT / config_path
    with absolute_path.open(encoding="utf-8") as file_obj:
        config = yaml.safe_load(file_obj) or {}

    if not isinstance(config, dict):
        raise TypeError(f"config must be dict in {config_path}")

    pipeline_cfg = config.get("pipeline")
    if isinstance(pipeline_cfg, dict):
        primary_keys = pipeline_cfg.get("business_primary_keys", [])
    else:
        primary_keys = config.get(
            "business_primary_keys", config.get("primary_keys", [])
        )

    if not isinstance(primary_keys, list):
        raise TypeError(f"business_primary_keys must be list in {config_path}")
    return primary_keys


def _append_baseline_differences(
    *,
    pair_name: str,
    missing_in_gold: list[str],
    missing_in_silver: list[str],
    known_silver_only: set[str],
    known_gold_only: set[str],
    warnings: list[str],
    blocking: list[str],
) -> None:
    """Split gaps into baselined informational warnings and new blocking ones."""
    new_missing_in_gold = [field for field in missing_in_gold if field not in known_silver_only]
    new_missing_in_silver = [field for field in missing_in_silver if field not in known_gold_only]
    baselined_in_gold = [field for field in missing_in_gold if field in known_silver_only]
    baselined_in_silver = [field for field in missing_in_silver if field in known_gold_only]

    if baselined_in_gold:
        warnings.append(f"{pair_name}: baselined Silver->Gold gaps: {baselined_in_gold}")
    if baselined_in_silver:
        warnings.append(f"{pair_name}: baselined Gold->Silver gaps: {baselined_in_silver}")
    if new_missing_in_gold:
        blocking.append(
            f"{pair_name}: NEW fields in Silver but missing in Gold: {new_missing_in_gold}"
        )
    if new_missing_in_silver:
        blocking.append(
            f"{pair_name}: NEW fields in Gold but missing in Silver: {new_missing_in_silver}"
        )


def _validate_primary_key(
    *,
    pair: SchemaPair,
    primary_key: str,
    silver_fields: dict[str, object],
    gold_columns: dict[str, object],
    warnings: list[str],
    blocking: list[str],
) -> None:
    """Validate PK presence and nullability across Silver and Gold layers."""
    if primary_key not in silver_fields:
        blocking.append(
            f"{pair.name}: PK '{primary_key}' missing in Silver schema ({pair.config_path})"
        )
        return

    if primary_key not in gold_columns:
        blocking.append(
            f"{pair.name}: PK '{primary_key}' missing in Gold schema ({pair.config_path})"
        )
        return

    silver_nullable = silver_fields[primary_key].nullable
    gold_nullable = gold_columns[primary_key].nullable

    if silver_nullable:
        warnings.append(f"{pair.name}: PK '{primary_key}' is nullable in Silver schema")
    if gold_nullable:
        warnings.append(f"{pair.name}: PK '{primary_key}' is nullable in Gold schema")
    if silver_nullable != gold_nullable:
        blocking.append(
            f"{pair.name}: PK '{primary_key}' nullable mismatch "
            f"(Silver={silver_nullable}, Gold={gold_nullable})"
        )


def check_schema_pair(
    pair: SchemaPair,
    baseline: dict[str, dict[str, list[str]]],
) -> tuple[list[str], list[str]]:
    """Return (blocking_errors, warning_errors) for one schema pair."""
    blocking: list[str] = []
    warnings: list[str] = []

    silver_fields = {field.name: field for field in pair.silver_schema}
    gold_columns = pair.gold_model.to_schema().columns

    missing_in_gold = sorted(set(silver_fields) - set(gold_columns))
    missing_in_silver = sorted(set(gold_columns) - set(silver_fields))

    # Filter out known baseline differences
    known = baseline.get(pair.name, {})
    known_silver_only = set(known.get("silver_only", []))
    known_gold_only = set(known.get("gold_only", []))
    _append_baseline_differences(
        pair_name=pair.name,
        missing_in_gold=missing_in_gold,
        missing_in_silver=missing_in_silver,
        known_silver_only=known_silver_only,
        known_gold_only=known_gold_only,
        warnings=warnings,
        blocking=blocking,
    )

    primary_keys = get_primary_keys(pair.config_path)
    if not primary_keys:
        warnings.append(
            f"{pair.name}: no business_primary_keys declared in {pair.config_path}"
        )

    for primary_key in primary_keys:
        _validate_primary_key(
            pair=pair,
            primary_key=primary_key,
            silver_fields=silver_fields,
            gold_columns=gold_columns,
            warnings=warnings,
            blocking=blocking,
        )

    return blocking, warnings


def _build_current_differences() -> dict[str, dict[str, list[str]]]:
    """Compute current Silver<->Gold differences for all schema pairs."""
    result: dict[str, dict[str, list[str]]] = {}
    for pair in SCHEMA_PAIRS:
        silver_fields = {field.name for field in pair.silver_schema}
        gold_columns = set(pair.gold_model.to_schema().columns)
        missing_in_gold = sorted(silver_fields - gold_columns)
        missing_in_silver = sorted(gold_columns - silver_fields)
        if missing_in_gold or missing_in_silver:
            entry: dict[str, list[str]] = {}
            if missing_in_gold:
                entry["silver_only"] = missing_in_gold
            if missing_in_silver:
                entry["gold_only"] = missing_in_silver
            result[pair.name] = entry
    return result


def main() -> int:
    """Run parity checks and return process exit code."""
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        choices=["all", "blocking", "warnings"],
        default="all",
        help="Which checks should affect process exit code.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Update the baseline file with current differences.",
    )
    args = parser.parse_args()

    if args.update_baseline:
        differences = _build_current_differences()
        _save_baseline(differences)
        print(f"Baseline updated: {BASELINE_PATH}")
        return 0

    baseline = _load_baseline()
    blocking_errors: list[str] = []
    warning_errors: list[str] = []

    for pair in SCHEMA_PAIRS:
        blocking, warnings = check_schema_pair(pair, baseline)
        blocking_errors.extend(blocking)
        warning_errors.extend(warnings)

    print("\n=== Blocking checks (Silver<->Gold parity, PK coverage) ===")
    if blocking_errors:
        for error in blocking_errors:
            print(f"[FAIL] {error}")
    else:
        print("[OK] No new blocking schema parity issues.")

    print("\n=== Warning checks (non-blocking quality signals) ===")
    if warning_errors:
        for warning in warning_errors:
            print(f"[WARN] {warning}")
    else:
        print("[OK] No schema warnings.")

    if args.mode == "blocking":
        return 1 if blocking_errors else 0
    if args.mode == "warnings":
        return 1 if warning_errors else 0
    return 1 if blocking_errors or warning_errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
