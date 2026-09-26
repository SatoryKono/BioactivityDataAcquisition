# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Architecture guardrails for intentional entity-specific pipeline overrides."""

from __future__ import annotations

import pytest

from pathlib import Path
from typing import Any

import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
ENTITIES_DIR = PROJECT_ROOT / "configs" / "entities"


def _load_yaml(path: Path) -> dict[str, Any]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return payload if isinstance(payload, dict) else {}


def _entity_configs() -> dict[str, dict[str, Any]]:
    configs: dict[str, dict[str, Any]] = {}
    for path in sorted(ENTITIES_DIR.rglob("*.yaml")):
        rel = path.relative_to(ENTITIES_DIR)
        if len(rel.parts) != 2:
            continue
        configs[f"{rel.parts[0]}/{rel.stem}"] = _load_yaml(path)
    return configs


def test_page_size_override_is_publication_only() -> None:
    """ChEMBL publication is the sole entity using pipeline.page_size_override."""
    holders: list[str] = []
    for rel_key, payload in _entity_configs().items():
        pipeline = payload.get("pipeline")
        if isinstance(pipeline, dict) and "page_size_override" in pipeline:
            holders.append(rel_key)

    assert holders == ["chembl/publication"]
    publication = _load_yaml(ENTITIES_DIR / "chembl" / "publication.yaml")
    pipeline = publication["pipeline"]
    assert pipeline["page_size_override"] == 1000


def test_therapeutic_flag_field_policy_is_molecule_only() -> None:
    """ChEMBL molecule is the sole entity with explicit therapeutic_flag policy."""
    holders: list[str] = []
    for rel_key, payload in _entity_configs().items():
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        field_policy = pipeline.get("field_policy")
        if isinstance(field_policy, dict) and "therapeutic_flag" in field_policy:
            holders.append(rel_key)

    assert holders == ["chembl/molecule"]


def test_uniprot_source_api_surface_is_idmapping_and_protein_only() -> None:
    """UniProt REST mapping endpoints are declared only on UniProt entity configs."""
    holders: list[str] = []
    for rel_key, payload in _entity_configs().items():
        pipeline = payload.get("pipeline")
        if not isinstance(pipeline, dict):
            continue
        source = pipeline.get("source")
        if not isinstance(source, dict):
            continue
        api = source.get("api")
        if isinstance(api, dict) and api:
            holders.append(rel_key)

    assert holders == ["uniprot/idmapping", "uniprot/protein"]

    for rel_key in holders:
        payload = _entity_configs()[rel_key]
        api = payload["pipeline"]["source"]["api"]
        assert api.get("base_url")
        assert api.get("from_db")
        assert api.get("to_db")


def test_quality_thresholds_are_limited_to_composites_and_idmapping() -> None:
    """Only composite contracts and UniProt idmapping override DQ thresholds."""
    holders: list[str] = []
    for rel_key, payload in _entity_configs().items():
        quality = payload.get("quality")
        if isinstance(quality, dict) and "thresholds" in quality:
            holders.append(rel_key)

    composite_holders = [
        "composite/activity",
        "composite/assay",
        "composite/molecule",
        "composite/publication",
        "composite/target",
    ]
    assert holders == [*composite_holders, "uniprot/idmapping"]

    for rel_key in composite_holders:
        assert _entity_configs()[rel_key]["quality"]["thresholds"] == {
            "soft_fail": 0.05,
            "hard_fail": 0.50,
        }

    thresholds = _entity_configs()["uniprot/idmapping"]["quality"]["thresholds"]
    assert isinstance(thresholds, dict)
    assert "soft_fail" in thresholds
    assert "hard_fail" in thresholds
