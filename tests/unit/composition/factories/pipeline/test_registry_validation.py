from __future__ import annotations

from pathlib import Path

import yaml

from bioetl.composition.factories.pipeline.config_types import PipelineFactoryConfig
from bioetl.composition.factories.pipeline.registry_validation import (
    validate_registry_manifest,
)


class _DummyTransformer:
    def transform(self) -> None:  # pragma: no cover - signature marker only
        return None


def _write_yaml(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        yaml.safe_dump(payload, sort_keys=False, allow_unicode=True),
        encoding="utf-8",
    )


def _write_provider_config(configs_root: Path, provider: str) -> None:
    _write_yaml(
        configs_root / "providers" / f"{provider}.yaml",
        {
            "provider": provider,
            "source": {
                "provider_config": {"provider": provider},
                "rate_limit": {"requests_per_second": 1, "burst": 1},
                "circuit_breaker": {
                    "failure_threshold": 3,
                    "recovery_timeout": 60,
                },
            },
            "entities": ["publication"],
        },
    )


def _write_entity_config(
    configs_root: Path,
    *,
    provider: str,
    entity: str,
    include_contracts: bool = True,
) -> None:
    payload: dict[str, object] = {
        "provider": provider,
        "entity": entity,
        "pipeline": {
            "pipeline_name": f"{provider}_{entity}",
            "provider": provider,
            "entity_type": entity,
            "business_primary_keys": [f"{entity}_id"],
            "sink": {
                "silver": {
                    "enabled": True,
                    "format": "delta",
                    "sort_by": ["entity_id"],
                },
                "gold": {"enabled": True, "sort_by": ["entity_id"]},
            },
        },
        "schema": {},
        "quality": {},
        "filters": {},
    }
    if include_contracts:
        payload["contracts"] = {"primary_key": {"business": [f"{entity}_id"]}}
    _write_yaml(configs_root / "entities" / provider / f"{entity}.yaml", payload)


def _registry_entry(
    *,
    pipeline_name: str,
    provider: str,
    entity: str,
) -> PipelineFactoryConfig:
    return PipelineFactoryConfig(
        pipeline_name=pipeline_name,
        provider=provider,
        entity_type=entity,
        transformer_class=_DummyTransformer,
        silver_schema=None,
        gold_schema=object(),
        pandera_silver_schema=object(),
    )


def test_validate_registry_manifest_accepts_matching_registry_and_config_tree(
    tmp_path: Path,
) -> None:
    configs_root = tmp_path / "configs"
    _write_provider_config(configs_root, "crossref")
    _write_entity_config(configs_root, provider="crossref", entity="publication")

    errors = validate_registry_manifest(
        configs_root=configs_root,
        pipeline_configs=(
            _registry_entry(
                pipeline_name="crossref_publication",
                provider="crossref",
                entity="publication",
            ),
        ),
    )

    assert errors == []


def test_validate_registry_manifest_reports_drift_and_missing_bindings(
    tmp_path: Path,
) -> None:
    configs_root = tmp_path / "configs"
    _write_provider_config(configs_root, "crossref")
    _write_entity_config(configs_root, provider="crossref", entity="publication")
    _write_entity_config(
        configs_root,
        provider="crossref",
        entity="orphan_entity",
        include_contracts=False,
    )

    errors = validate_registry_manifest(
        configs_root=configs_root,
        pipeline_configs=(
            _registry_entry(
                pipeline_name="crossref_publication",
                provider="crossref",
                entity="publication",
            ),
            _registry_entry(
                pipeline_name="crossref_publication",
                provider="crossref",
                entity="missing_entity",
            ),
        ),
    )

    assert any(
        "duplicate pipeline_name: crossref_publication" in error for error in errors
    )
    assert any("crossref/missing_entity.yaml" in error for error in errors)
    assert any(
        "orphan_entity.yaml -> crossref_orphan_entity" in error for error in errors
    )
    assert any("missing contracts section" in error for error in errors)
