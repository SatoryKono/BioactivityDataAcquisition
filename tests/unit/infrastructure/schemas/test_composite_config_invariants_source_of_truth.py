# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
from __future__ import annotations

import json
import os
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml
from hypothesis import given, settings
from hypothesis import strategies as st
from pydantic import ValidationError

from bioetl.domain.composite import CompositeConfig
from bioetl.infrastructure.schemas.composite_config import (
    CompositeConfigSchema,
    CompositeDQSchema,
    CrossValidationSchema,
    DependencySchema,
    EnricherSchema,
    ExecutionSchema,
    LineageSchema,
    MergeSchema,
    SeedSchema,
    validate_composite_config_payload,
)

pytestmark = pytest.mark.unit

SNAPSHOT_FILE = Path("tests/snapshots/composite_config_real_yaml_golden_master.json")
COMPOSITE_CONFIG_DIR = Path("configs/composites")


def _base_payload() -> dict[str, object]:
    return {
        "name": "composite_publication",
        "version": "1.0.0",
        "seed": {
            "pipeline": "chembl_publication",
            "output_keys": ["doi", "pmid"],
            "silver_table": "silver/chembl/publication",
        },
        "dependencies": [],
        "enrichers": [
            {
                "pipeline": "crossref_publication",
                "join_keys": ["doi"],
            }
        ],
        "merge": {
            "output": {
                "silver": "silver/composite/publication",
                "gold": "gold/composite/publication",
            },
            "sort_by": {
                "silver": ["entity_id", "publication_id"],
                "gold": ["entity_id", "publication_id"],
            },
        },
    }


def _project_domain_config(config: CompositeConfig) -> dict[str, Any]:
    return {
        "name": config.name,
        "version": config.version,
        "seed_pipeline": config.seed.pipeline,
        "seed_output_keys": list(config.seed.output_keys),
        "dependencies": [
            {
                "pipeline": dep.pipeline,
                "join_keys": list(dep.join_keys),
                "key_source": dep.key_source,
                "filter_field": dep.filter_field,
                "filter_fields": (
                    list(dep.filter_fields) if dep.filter_fields is not None else None
                ),
                "required": dep.required,
            }
            for dep in config.dependencies
        ],
        "enrichers": [
            {
                "pipeline": enricher.pipeline,
                "join_keys": list(enricher.join_keys),
                "required": enricher.required,
                "cardinality": enricher.cardinality.value,
            }
            for enricher in config.enrichers
        ],
        "merge": {
            "strategy": config.merge.strategy.value,
            "conflict_resolution": config.merge.conflict_resolution.value,
            "output_silver_path": config.merge.output_silver_path,
            "output_gold_path": config.merge.output_gold_path,
            "preserve_all_sources": config.merge.preserve_all_sources,
            "column_group_count": len(config.merge.column_groups),
        },
    }


def _collect_real_config_projection() -> dict[str, Any]:
    projection: dict[str, Any] = {}
    for config_path in sorted(COMPOSITE_CONFIG_DIR.glob("*.yaml")):
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        schema = validate_composite_config_payload(raw)
        projection[config_path.stem] = _project_domain_config(schema.to_domain())
    return projection


def _load_snapshot() -> dict[str, Any]:
    if not SNAPSHOT_FILE.exists():
        return {}
    with SNAPSHOT_FILE.open(encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, dict) else {}


def _save_snapshot(payload: dict[str, Any]) -> None:
    SNAPSHOT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with SNAPSHOT_FILE.open("w", encoding="utf-8", newline="\n") as f:
        json.dump(payload, f, indent=2, sort_keys=True)


def _build_domain_from_structural_payload(payload: dict[str, Any]) -> CompositeConfig:
    return CompositeConfig(
        name=str(payload["name"]),
        version=str(payload["version"]),
        seed=SeedSchema.model_validate(payload["seed"]).to_domain(),
        dependencies=tuple(
            DependencySchema.model_validate(dep).to_domain()
            for dep in payload.get("dependencies", [])
        ),
        enrichers=tuple(
            EnricherSchema.model_validate(enricher).to_domain()
            for enricher in payload.get("enrichers", [])
        ),
        merge=MergeSchema.model_validate(payload["merge"]).to_domain(),
        dq=CompositeDQSchema.model_validate(
            payload.get("dq_overrides", {})
        ).to_domain(),
        execution=ExecutionSchema.model_validate(
            payload.get("execution", {})
        ).to_domain(),
        lineage=LineageSchema.model_validate(payload.get("lineage", {})).to_domain(),
        cross_validation=CrossValidationSchema.model_validate(
            payload.get("cross_validation", {})
        ).to_domain(),
    )


def _schema_error_message(payload: dict[str, Any]) -> str:
    with pytest.raises(ValidationError) as exc:
        CompositeConfigSchema.model_validate(payload)
    return str(exc.value)


def _domain_error_message(payload: dict[str, Any]) -> str:
    with pytest.raises(ValueError) as exc:
        _build_domain_from_structural_payload(payload)
    return str(exc.value)


def test_composite_real_yaml_golden_master_snapshot() -> None:
    current = _collect_real_config_projection()
    update_snapshots = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
    if update_snapshots:
        _save_snapshot(current)
        pytest.skip("Updated composite config golden snapshot")

    snapshot = _load_snapshot()
    if not snapshot:
        pytest.fail(
            "Missing composite config golden snapshot. "
            "Run with UPDATE_SNAPSHOTS=1 to create baseline."
        )
    assert current == snapshot


@settings(deadline=None, max_examples=25)
@given(
    bad_join_key=st.text(min_size=1, max_size=20).filter(
        lambda value: value.strip() not in {"", "doi", "pmid"}
    )
)
def test_invalid_enricher_join_key_error_equivalence_property(
    bad_join_key: str,
) -> None:
    payload = deepcopy(_base_payload())
    payload["enrichers"] = [
        {"pipeline": "crossref_publication", "join_keys": [bad_join_key]}
    ]

    schema_msg = _schema_error_message(payload)
    domain_msg = _domain_error_message(payload)

    assert domain_msg in schema_msg
    assert "join_key" in domain_msg


@settings(deadline=None, max_examples=25)
@given(
    duplicate_name=st.text(min_size=1, max_size=20).filter(
        lambda value: value.strip() != ""
    )
)
def test_duplicate_enricher_error_equivalence_property(
    duplicate_name: str,
) -> None:
    payload = deepcopy(_base_payload())
    payload["enrichers"] = [
        {"pipeline": duplicate_name, "join_keys": ["doi"]},
        {"pipeline": duplicate_name, "join_keys": ["doi"]},
    ]

    schema_msg = _schema_error_message(payload)
    domain_msg = _domain_error_message(payload)

    assert domain_msg in schema_msg
    assert "Duplicate enricher pipelines" in domain_msg
