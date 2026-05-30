#!/usr/bin/env python3
"""Scaffold root hash_policy sections for non-ChEMBL entity configs from profiles."""

from __future__ import annotations

import io
import os
import sys
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML

ROOT = Path(__file__).resolve().parents[3]
ENTITIES = ROOT / "configs" / "entities"

if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from bioetl.domain.normalization.profiles.registry import resolve_normalization_profile

NON_CHEMBL_TARGETS: tuple[tuple[str, str], ...] = (
    ("crossref", "publication"),
    ("openalex", "publication"),
    ("pubmed", "publication"),
    ("semanticscholar", "publication"),
    ("pubchem", "compound"),
    ("uniprot", "protein"),
    ("uniprot", "idmapping"),
)

STANDARD_RUNTIME_EXCLUDE: frozenset[str] = frozenset(
    {
        "_ingestion_ts",
        "_run_id",
        "_run_type",
        "_dq_warn",
        "_dq_error",
        "_source_batch_id",
        "_index",
        "_lookup_method",
        "_original_id",
        "_source",
    }
)


def _yaml_rt() -> YAML:
    yaml = YAML()
    yaml.preserve_quotes = True
    yaml.default_flow_style = False
    yaml.width = 120
    return yaml


def _atomic_write(path: Path, yaml: YAML, data: dict[str, Any]) -> None:
    buffer = io.StringIO()
    yaml.dump(data, buffer)
    payload = buffer.getvalue()
    tmp = path.with_suffix(f"{path.suffix}.tmp")
    tmp.write_text(payload, encoding="utf-8")
    try:
        os.replace(tmp, path)
    except OSError:
        path.write_text(payload, encoding="utf-8")
        tmp.unlink(missing_ok=True)


def _normalization_block() -> dict[str, Any]:
    return {
        "trim_strings": True,
        "round_floats": {"enabled": True, "precision": 10},
        "dates": {"enabled": True, "format": "YYYY-MM-DD"},
        "null_handling": {"nan_to_null": True, "inf_to_null": True},
    }


def _build_hash_policy(
    *,
    provider: str,
    entity: str,
    profile_name: str,
    include_fields: list[str],
    exclude_fields: list[str],
) -> dict[str, Any]:
    return {
        "provider": provider,
        "entity": entity,
        "contract": {
            "version": "1.0.0",
            "migration_note": (
                f"Explicit config-level hash contract aligned with normalization "
                f"profile {profile_name}."
            ),
        },
        "hash_policy": {
            "algorithm": "sha256",
            "canonicalization": "provider + canonical_json_dumps(normalized_record)",
            "include_fields": include_fields,
            "exclude_fields": exclude_fields,
            "exclude_patterns": ["^_dq_"],
            "normalization": _normalization_block(),
        },
    }


def _exclude_fields_for_profile(profile: Any) -> list[str]:
    excluded = set(STANDARD_RUNTIME_EXCLUDE)
    excluded.update(field for field in profile.meta_fields if field.startswith("_"))
    excluded.update(profile.hash_excluded_fields)
    excluded.discard("entity_id")
    excluded.discard("content_hash")
    return sorted(excluded)


def scaffold_entity(provider: str, entity: str) -> bool:
    path = ENTITIES / provider / f"{entity}.yaml"
    profile = resolve_normalization_profile(provider, entity)
    if profile is None:
        raise ValueError(f"No normalization profile for {provider}/{entity}")

    yaml = _yaml_rt()
    data = yaml.load(path)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid entity config: {path}")

    if isinstance(data.get("hash_policy"), dict) and data["hash_policy"]:
        return False

    contracts = data.get("contracts")
    if not isinstance(contracts, dict):
        raise ValueError(f"Missing contracts section in {path}")
    if contracts.get("hash_include"):
        raise ValueError(f"contracts.hash_include must be empty before hash_policy in {path}")
    if contracts.get("hash_exclude"):
        raise ValueError(f"contracts.hash_exclude must be empty before hash_policy in {path}")

    include_fields = sorted(profile.hash_included_fields)
    if not include_fields:
        raise ValueError(f"Profile {provider}/{entity} produced empty include_fields")

    data["hash_policy"] = _build_hash_policy(
        provider=provider,
        entity=entity,
        profile_name=profile.profile_name,
        include_fields=include_fields,
        exclude_fields=_exclude_fields_for_profile(profile),
    )
    _atomic_write(path, yaml, data)
    return True


def main() -> None:
    touched = 0
    for provider, entity in NON_CHEMBL_TARGETS:
        if scaffold_entity(provider, entity):
            touched += 1
            print(f"scaffolded hash_policy {provider}/{entity}")
    print(f"touched={touched}")


if __name__ == "__main__":
    main()
