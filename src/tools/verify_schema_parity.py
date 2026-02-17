"""Programmatically verify parity between Domain entities, Silver schemas, and Gold contracts.

This tool is CI-friendly and can produce a machine-readable JSON report.
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import logging
import sys
from collections.abc import Iterable
from pathlib import Path
from types import UnionType
from typing import Any, Union, get_args, get_origin

from bioetl.domain.contracts.gold import (
    ChEMBLActivityGoldSchema,
    ChEMBLAssayGoldSchema,
    ChEMBLMoleculeGoldSchema,
    ChEMBLTargetGoldSchema,
)
from bioetl.domain.entities.bioactivity import Bioactivity
from bioetl.domain.entities.chembl_activity import Assay
from bioetl.domain.entities.chembl_structures import Molecule, Target
from bioetl.infrastructure.schemas.silver import (
    CHEMBL_ACTIVITY_SCHEMA,
    CHEMBL_ASSAY_SCHEMA,
    CHEMBL_MOLECULE_SCHEMA,
    CHEMBL_TARGET_SCHEMA,
)

# Configure logging for CLI output
logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)

SYSTEM_FIELDS = {
    "_run_id",
    "_run_type",
    "_source_batch_id",
    "_ingestion_ts",
    "entity_id",
    "content_hash",
    "ingestion_ts",
    "run_id",
    "run_type",
    "source_batch_id",
}


def _normalize_type(type_obj: Any) -> str:
    """Normalize type representation for cross-schema comparison."""
    if type_obj is None:
        return "unknown"

    origin = get_origin(type_obj)
    if origin in (UnionType, Union):
        args = [arg for arg in get_args(type_obj) if arg is not type(None)]
        if len(args) == 1:
            return _normalize_type(args[0])
        return " | ".join(sorted(_normalize_type(arg) for arg in args))

    if origin in (list, tuple, set, dict):
        type_args = get_args(type_obj)
        origin_name = str(getattr(origin, "__name__", "unknown"))
        if type_args:
            inner = ", ".join(_normalize_type(arg) for arg in type_args)
            return f"{origin_name}[{inner}]"
        return origin_name

    if isinstance(type_obj, str):
        return type_obj

    if hasattr(type_obj, "__name__"):
        return str(type_obj.__name__)

    text = str(type_obj)
    return text.replace("typing.", "")


def get_domain_fields(cls: type[Any]) -> dict[str, dict[str, Any]]:
    """Return domain field metadata keyed by field name."""
    result: dict[str, dict[str, Any]] = {}
    for field in dataclasses.fields(cls):
        result[field.name] = {
            "name": field.name,
            "type": _normalize_type(field.type),
            "nullable": "NoneType" in str(field.type) or "| None" in str(field.type),
            "description": field.metadata.get("description")
            if field.metadata
            else None,
        }
    return result


def get_silver_fields(schema: Any) -> dict[str, dict[str, Any]]:
    """Return PyArrow field metadata keyed by field name."""
    result: dict[str, dict[str, Any]] = {}
    for field in schema:
        description = None
        if field.metadata and b"description" in field.metadata:
            description = field.metadata[b"description"].decode("utf-8")

        result[field.name] = {
            "name": field.name,
            "type": str(field.type),
            "nullable": bool(field.nullable),
            "description": description,
        }
    return result


def get_gold_fields(model: Any) -> dict[str, dict[str, Any]]:
    """Return Pandera model field metadata keyed by field name."""
    result: dict[str, dict[str, Any]] = {}
    schema = model.to_schema()
    for name, column in schema.columns.items():
        result[name] = {
            "name": name,
            "type": str(column.dtype),
            "nullable": bool(column.nullable),
            "description": column.description,
        }
    return result


def _compare_field_details(
    entity_name: str,
    left_label: str,
    right_label: str,
    left_fields: dict[str, dict[str, Any]],
    right_fields: dict[str, dict[str, Any]],
) -> list[dict[str, Any]]:
    """Compare types/nullability/descriptions for common fields."""
    mismatches: list[dict[str, Any]] = []

    for field_name in sorted(set(left_fields) & set(right_fields)):
        left = left_fields[field_name]
        right = right_fields[field_name]

        for attr in ("type", "nullable", "description"):
            if left[attr] != right[attr]:
                mismatches.append(
                    {
                        "entity": entity_name,
                        "field": field_name,
                        "attribute": attr,
                        "left_schema": left_label,
                        "right_schema": right_label,
                        "left_value": left[attr],
                        "right_value": right[attr],
                    }
                )

    return mismatches


def _set_without_system(names: Iterable[str]) -> set[str]:
    return {name for name in names if name not in SYSTEM_FIELDS}


def check_parity(
    name: str, domain_cls: type[Any], silver_schema: Any, gold_model: Any
) -> dict[str, Any]:
    """Check parity for one entity and return structured results."""
    logger.info("Checking %s...", name)

    domain_fields = get_domain_fields(domain_cls)
    silver_fields = get_silver_fields(silver_schema)
    gold_fields = get_gold_fields(gold_model)

    domain_names = _set_without_system(domain_fields.keys())
    silver_names = _set_without_system(silver_fields.keys())
    gold_names = _set_without_system(gold_fields.keys())

    missing_in_silver = sorted(domain_names - silver_names)
    missing_in_gold = sorted(silver_names - gold_names)
    missing_in_silver_from_gold = sorted(gold_names - silver_names)

    silver_gold_mismatches = _compare_field_details(
        entity_name=name,
        left_label="silver",
        right_label="gold",
        left_fields={
            k: v for k, v in silver_fields.items() if k in silver_names & gold_names
        },
        right_fields={
            k: v for k, v in gold_fields.items() if k in silver_names & gold_names
        },
    )

    domain_silver_mismatches = _compare_field_details(
        entity_name=name,
        left_label="domain",
        right_label="silver",
        left_fields={
            k: v for k, v in domain_fields.items() if k in domain_names & silver_names
        },
        right_fields={
            k: v for k, v in silver_fields.items() if k in domain_names & silver_names
        },
    )

    issues_count = (
        len(missing_in_silver)
        + len(missing_in_gold)
        + len(missing_in_silver_from_gold)
        + len(silver_gold_mismatches)
        + len(domain_silver_mismatches)
    )

    if issues_count == 0:
        logger.info("  [OK] No parity issues found.")
    else:
        if missing_in_silver:
            logger.error(
                "  [ERROR] Domain fields missing in Silver: %s", missing_in_silver
            )
        if missing_in_gold:
            logger.error("  [ERROR] Silver fields missing in Gold: %s", missing_in_gold)
        if missing_in_silver_from_gold:
            logger.error(
                "  [ERROR] Gold fields missing in Silver: %s",
                missing_in_silver_from_gold,
            )
        if silver_gold_mismatches:
            logger.error(
                "  [ERROR] Silver ↔ Gold detail mismatches: %d",
                len(silver_gold_mismatches),
            )
        if domain_silver_mismatches:
            logger.error(
                "  [ERROR] Domain ↔ Silver detail mismatches: %d",
                len(domain_silver_mismatches),
            )

    return {
        "entity": name,
        "summary": {
            "missing_in_silver": len(missing_in_silver),
            "missing_in_gold": len(missing_in_gold),
            "missing_in_silver_from_gold": len(missing_in_silver_from_gold),
            "silver_gold_mismatches": len(silver_gold_mismatches),
            "domain_silver_mismatches": len(domain_silver_mismatches),
            "total_issues": issues_count,
        },
        "missing_in_silver": missing_in_silver,
        "missing_in_gold": missing_in_gold,
        "missing_in_silver_from_gold": missing_in_silver_from_gold,
        "silver_gold_mismatches": silver_gold_mismatches,
        "domain_silver_mismatches": domain_silver_mismatches,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--report-path",
        type=Path,
        default=Path("artifacts/schema-parity-report.json"),
        help="Path to machine-readable JSON report.",
    )
    parser.add_argument(
        "--fail-on-mismatch",
        action="store_true",
        default=True,
        help="Exit non-zero when mismatches are found (default behavior).",
    )
    parser.add_argument(
        "--no-fail-on-mismatch",
        action="store_false",
        dest="fail_on_mismatch",
        help="Always exit zero, even if mismatches are found.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    report: dict[str, Any] = {
        "tool": "verify_schema_parity",
        "version": 2,
        "results": [
            check_parity(
                "Molecule", Molecule, CHEMBL_MOLECULE_SCHEMA, ChEMBLMoleculeGoldSchema
            ),
            check_parity(
                "Target", Target, CHEMBL_TARGET_SCHEMA, ChEMBLTargetGoldSchema
            ),
            check_parity(
                "Bioactivity",
                Bioactivity,
                CHEMBL_ACTIVITY_SCHEMA,
                ChEMBLActivityGoldSchema,
            ),
            check_parity("Assay", Assay, CHEMBL_ASSAY_SCHEMA, ChEMBLAssayGoldSchema),
        ],
    }

    total_issues = sum(item["summary"]["total_issues"] for item in report["results"])
    report["summary"] = {
        "entities_checked": len(report["results"]),
        "total_issues": total_issues,
        "status": "pass" if total_issues == 0 else "fail",
    }

    args.report_path.parent.mkdir(parents=True, exist_ok=True)
    args.report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    logger.info("\nJSON report written to %s", args.report_path)

    if total_issues and args.fail_on_mismatch:
        logger.error("\nSchema parity FAILED (%d issues).", total_issues)
        return 1

    logger.info("\nSchema parity PASSED.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
