# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict.
"""Lifecycle ratchet for deprecated ChEMBL ENTITY_MAPPING alias (#7495)."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.adapters.chembl._entity_mapping_lookup import (
    build_legacy_entity_mapping,
)
from bioetl.infrastructure.adapters.chembl.entity_mapper import (
    CHEMBL_API_BASE,
    ENTITY_MAPPING,
    ENTITY_MAPPING_LIFECYCLE,
    ChemblEntityMapper,
)

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
INVENTORY = ROOT / "configs/quality/chembl_entity_mapping_compatibility.yaml"


def _load_inventory() -> dict[str, object]:
    payload = yaml.safe_load(INVENTORY.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _src_entity_mapping_importers() -> list[str]:
    """Return first-party src paths that reference ENTITY_MAPPING (excluding owner)."""
    owner = Path("src/bioetl/infrastructure/adapters/chembl/entity_mapper.py")
    hits: list[str] = []
    for path in (ROOT / "src").rglob("*.py"):
        rel = path.relative_to(ROOT).as_posix()
        if Path(rel) == owner:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        imports_or_loads_alias = any(
            (isinstance(node, ast.alias) and node.name == "ENTITY_MAPPING")
            or (
                isinstance(node, ast.Name)
                and node.id == "ENTITY_MAPPING"
                and isinstance(node.ctx, ast.Load)
            )
            for node in ast.walk(tree)
        )
        if imports_or_loads_alias:
            hits.append(rel)
    return sorted(hits)


def test_entity_mapping_lifecycle_inventory_is_complete() -> None:
    inventory = _load_inventory()
    alias = inventory["alias"]
    assert isinstance(alias, dict)
    assert inventory["decision"] == "retain_external_compatibility_zero_first_party_src"
    assert inventory["new_src_import_policy"] == "fail_fast_review_required"
    assert alias["symbol"] == "ENTITY_MAPPING"
    assert alias["max_src_importer_count"] == 0
    assert alias["allowed_src_importers"] == []
    assert alias["external_breaking_change_required"] is True
    assert str(alias["review_date"]) >= "2026-09-30"
    assert alias["migration_path"]
    assert alias["exit_criteria"]
    for rel in alias["owner_tests"]:
        assert (ROOT / str(rel)).is_file(), rel


def test_entity_mapping_module_lifecycle_matches_inventory() -> None:
    inventory = _load_inventory()
    alias = inventory["alias"]
    assert isinstance(alias, dict)
    assert ENTITY_MAPPING_LIFECYCLE["symbol"] == alias["symbol"]
    assert ENTITY_MAPPING_LIFECYCLE["internal_callers_zero"] is True
    assert ENTITY_MAPPING_LIFECYCLE["max_src_importer_count"] == 0
    assert ENTITY_MAPPING_LIFECYCLE["linked_issue"] == 7495
    assert (ROOT / str(alias["path"])).is_file()


def test_entity_mapping_has_zero_first_party_src_importers() -> None:
    importers = _src_entity_mapping_importers()
    assert importers == [], (
        f"ENTITY_MAPPING must keep zero first-party src importers; found: {importers}"
    )


def test_entity_mapping_equals_canonical_builder() -> None:
    """Alias must remain a pure re-export of build_legacy_entity_mapping()."""
    expected = build_legacy_entity_mapping()
    assert ENTITY_MAPPING == expected
    assert ENTITY_MAPPING["compound"] == "molecule"
    assert ENTITY_MAPPING["publication"] == "document"
    assert ENTITY_MAPPING["activity"] == "activity"
    assert ENTITY_MAPPING["target"] == "target"
    assert ENTITY_MAPPING["assay"] == "assay"
    assert ENTITY_MAPPING["document"] == "document"
    assert ENTITY_MAPPING["document_similarity"] == "document_similarity"
    assert ENTITY_MAPPING["document_term"] == "document"


def test_entity_mapping_urls_match_chembl_entity_mapper() -> None:
    """Known-entity keys in the legacy map align with ChemblEntityMapper URLs."""
    for entity, resource in ENTITY_MAPPING.items():
        if not ChemblEntityMapper.is_known_entity(entity):
            assert entity.startswith("document")
            assert resource
            continue
        url = ChemblEntityMapper.get_resource_url(entity)
        assert url == f"{CHEMBL_API_BASE}/{resource}"
        assert resource in url
        assert not url.endswith(".json")
