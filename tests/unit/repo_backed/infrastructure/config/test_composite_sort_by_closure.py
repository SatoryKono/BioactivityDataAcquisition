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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""CF-027: shipped composite sort_by stays closed; priorities stay shared."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from bioetl.infrastructure.config.composite_config_api import load_composite_config

pytestmark = pytest.mark.repo_backed

_COMPOSITES = ("activity", "assay", "molecule", "publication", "target")
_MIGRATED = ("activity", "molecule", "target")
_SORT_BY_KEYS = frozenset({"silver", "gold"})
_COMPOSITES_DIR = Path("configs/composites")
_SHARED_POLICY = _COMPOSITES_DIR / "field_groups" / "shared_policy.yaml"
_PUBLISHED_SCHEMA = Path("configs/_schema/composite.json")


def _load_yaml(path: Path) -> dict[str, object]:
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def _merge_section(path: Path) -> dict[str, object]:
    payload = _load_yaml(path)
    composite = payload["composite"]
    assert isinstance(composite, dict)
    merge = composite["merge"]
    assert isinstance(merge, dict)
    return merge


def _shared_field_priorities() -> dict[str, tuple[str, ...]]:
    payload = _load_yaml(_SHARED_POLICY)
    merge = payload["merge"]
    assert isinstance(merge, dict)
    priorities = merge["field_priorities"]
    assert isinstance(priorities, dict)
    expected: dict[str, tuple[str, ...]] = {}
    for key, value in priorities.items():
        assert isinstance(key, str)
        assert isinstance(value, list)
        assert all(isinstance(item, str) for item in value)
        expected[key] = tuple(value)
    return expected


@pytest.mark.parametrize("name", _COMPOSITES)
def test_shipped_sort_by_is_only_silver_and_gold(name: str) -> None:
    """Dead per-field keys must not sit under merge.sort_by."""
    merge = _merge_section(_COMPOSITES_DIR / f"{name}.yaml")
    sort_by = merge["sort_by"]
    assert isinstance(sort_by, dict)
    assert set(sort_by) == _SORT_BY_KEYS
    assert "field_priorities" not in merge


@pytest.mark.parametrize("name", _MIGRATED)
def test_migrated_composites_load_shared_field_priorities(name: str) -> None:
    """activity/molecule/target load, and shared policy remains the priority owner."""
    loaded = load_composite_config(name)
    assert dict(loaded.merge.field_priorities) == _shared_field_priorities()
    assert set(loaded.merge.sort_by_silver)
    assert set(loaded.merge.sort_by_gold)


def test_published_merge_sort_by_schema_forbids_additional_properties() -> None:
    """configs/_schema/composite.json must match MergeSortBySchema extra=forbid."""
    schema = json.loads(_PUBLISHED_SCHEMA.read_text(encoding="utf-8"))
    sort_by = schema["$defs"]["MergeSortBySchema"]
    assert sort_by["additionalProperties"] is False
    assert set(sort_by["properties"]) == _SORT_BY_KEYS
