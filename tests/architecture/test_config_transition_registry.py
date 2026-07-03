"""Guardrails for registered config compatibility shapes."""

from __future__ import annotations

import pytest

from datetime import date
from pathlib import Path
from typing import Any

import yaml

pytestmark = pytest.mark.architecture

PROJECT_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = (
    PROJECT_ROOT / "configs" / "quality" / "config_compatibility_registry.yaml"
)

MIGRATION_STATUSES = {"migration-supported", "deprecated-migration"}
PERMANENT_STATUSES = {"canonical-alias"}
RETIRED_STATUSES = {"rejected"}
VALID_STATUSES = MIGRATION_STATUSES | PERMANENT_STATUSES | RETIRED_STATUSES

SOURCE_NORMALIZER = (
    PROJECT_ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "config"
    / "source_normalizers"
    / "source.py"
)
PIPELINE_NORMALIZER = (
    PROJECT_ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "config"
    / "pipeline_payload_normalization.py"
)
PIPELINE_SCHEMA = PROJECT_ROOT / "configs" / "_schema" / "pipeline.json"
CONFIG_CI_CONTRACT = (
    PROJECT_ROOT
    / "src"
    / "bioetl"
    / "infrastructure"
    / "config"
    / "config_ci_contract.py"
)

REQUIRED_MARKERS = {
    SOURCE_NORMALIZER: {
        "_sync_timeout_aliases": "source.timeout_timeout_sec_alias",
        "_normalize_rate_limit": "source.rate_limit_with_api_key_alias",
        "_RETIRED_SOURCE_ALIAS_SECTIONS": "source.retired_transport_alias_sections",
        "_RETIRED_PROVIDER_PAGINATION_KEYS": "source.retired_provider_pagination_aliases",
        "_RETIRED_SOURCE_ROOT_KEYS": "source.retired_root_batch_size_alias",
    },
    PIPELINE_NORMALIZER: {
        "_collect_forbidden_pipeline_source_overrides": (
            "pipeline.inline_source_pagination_overrides_rejected"
        ),
    },
    PIPELINE_SCHEMA: {},
    CONFIG_CI_CONTRACT: {},
}


def _load_registry() -> dict[str, Any]:
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict), "config compatibility registry must be a mapping"
    return payload


def _entries(payload: dict[str, Any]) -> list[dict[str, Any]]:
    entries: list[dict[str, Any]] = []
    for section in ("accepted_shapes", "retired_rejected_shapes"):
        section_entries = payload.get(section)
        assert isinstance(section_entries, list), (
            f"config compatibility registry section {section} must be a list"
        )
        for entry in section_entries:
            assert isinstance(entry, dict), (
                f"config compatibility registry section {section} contains non-mapping"
            )
            entries.append(entry)
    return entries


def test_config_compatibility_registry_has_explicit_policy() -> None:
    """Registry must declare scope, owner, review date, and policy constraints."""
    payload = _load_registry()

    assert payload.get("version") == 1
    assert payload.get("policy_scope") == "config_compatibility_shapes"
    assert payload.get("review_owner") == "config-governance"
    assert date.fromisoformat(str(payload["last_reviewed"]))

    policy = payload.get("policy")
    assert isinstance(policy, dict), "registry must declare policy block"
    constraints = policy.get("constraints")
    assert isinstance(constraints, list), "registry policy must list constraints"
    assert any("Domain must not import infrastructure" in item for item in constraints)
    assert any("Gold strict validation" in item for item in constraints)
    assert any("No new compatibility shape" in item for item in constraints)

    burn_down = policy.get("burn_down")
    assert isinstance(burn_down, dict), "registry must declare burn-down policy"
    assert burn_down.get("linked_issue") == "#4516"
    assert burn_down.get("mode") == "fail-fast-no-growth"
    assert burn_down.get("expired_shape_policy") == "fail-ci"
    exit_strategy = policy.get("accepted_shape_exit_strategy")
    assert isinstance(exit_strategy, dict)
    assert exit_strategy.get("linked_issue") == "#4516"
    assert exit_strategy.get("review_date") == "2026-09-30"
    assert set(exit_strategy.get("allowed_strategies", [])) == {
        "retain-permanent-canonical-alias"
    }


def test_config_compatibility_entries_are_bounded_or_justified() -> None:
    """Every compatibility entry needs a sunset date or permanent rationale."""
    payload = _load_registry()
    seen_ids: set[str] = set()

    for entry in _entries(payload):
        entry_id = entry.get("id")
        status = entry.get("status")
        assert isinstance(entry_id, str) and entry_id, "entry id must be non-empty"
        assert entry_id not in seen_ids, f"duplicate registry entry id: {entry_id}"
        seen_ids.add(entry_id)
        assert status in VALID_STATUSES, f"{entry_id} has invalid status {status!r}"
        assert entry.get("canonical_target"), f"{entry_id} must define canonical_target"
        assert entry.get("risk") in {"low", "medium", "high"}, (
            f"{entry_id} must declare risk"
        )

        if status in MIGRATION_STATUSES:
            remove_after = entry.get("remove_after")
            assert isinstance(remove_after, str) and remove_after, (
                f"{entry_id} must define remove_after"
            )
            assert date.fromisoformat(remove_after), (
                f"{entry_id} remove_after must be ISO date"
            )
            assert entry.get("exit_criteria"), f"{entry_id} must define exit_criteria"
        elif status in PERMANENT_STATUSES:
            assert entry.get("permanent_rationale"), (
                f"{entry_id} must define permanent_rationale"
            )
            assert entry.get("review_decision") == "retain-permanent", (
                f"{entry_id} permanent aliases must record review_decision="
                "'retain-permanent'"
            )
            decision_recorded_on = entry.get("decision_recorded_on")
            assert isinstance(decision_recorded_on, str) and decision_recorded_on, (
                f"{entry_id} permanent aliases must define decision_recorded_on"
            )
            assert date.fromisoformat(decision_recorded_on), (
                f"{entry_id} decision_recorded_on must be ISO date"
            )
            assert entry.get("exit_strategy") == "retain-permanent-canonical-alias", (
                f"{entry_id} permanent aliases must declare the reviewed exit strategy"
            )


def test_config_compatibility_burn_down_budget_is_not_exceeded() -> None:
    """Compatibility-shape count must not grow without explicit budget review."""
    payload = _load_registry()
    policy = payload["policy"]
    assert isinstance(policy, dict)
    burn_down = policy["burn_down"]
    assert isinstance(burn_down, dict)

    accepted_entries = payload["accepted_shapes"]
    rejected_entries = payload["retired_rejected_shapes"]
    assert isinstance(accepted_entries, list)
    assert isinstance(rejected_entries, list)

    migration_supported_count = sum(
        1
        for entry in accepted_entries
        if isinstance(entry, dict) and entry.get("status") in MIGRATION_STATUSES
    )
    assert len(accepted_entries) <= int(burn_down["accepted_shape_max"])
    assert migration_supported_count <= int(burn_down["migration_supported_shape_max"])
    assert len(rejected_entries) >= int(burn_down["retired_rejected_shape_min"])


def test_temporary_config_compatibility_shapes_are_not_expired() -> None:
    """Temporary compatibility shapes must fail CI after their removal date."""
    today = date(2026, 5, 21)
    payload = _load_registry()

    expired = [
        str(entry["id"])
        for entry in _entries(payload)
        if entry.get("status") in MIGRATION_STATUSES
        and date.fromisoformat(str(entry["remove_after"])) < today
    ]

    assert not expired, (
        "Temporary config compatibility shapes expired and must be removed or "
        "re-reviewed:\n" + "\n".join(expired)
    )


def test_config_compatibility_entries_reference_existing_files() -> None:
    """Registry evidence must point at existing source and test files."""
    payload = _load_registry()

    for entry in _entries(payload):
        entry_id = entry["id"]
        for field in ("source_files", "test_files"):
            paths = entry.get(field)
            assert isinstance(paths, list) and paths, f"{entry_id} must list {field}"
            for rel_path in paths:
                assert isinstance(rel_path, str) and rel_path, (
                    f"{entry_id} has invalid {field} path"
                )
                assert (PROJECT_ROOT / rel_path).exists(), (
                    f"{entry_id} references missing {field} path: {rel_path}"
                )


def test_active_config_compatibility_markers_are_registered() -> None:
    """Normalizer markers must not introduce unregistered legacy-shape behavior."""
    payload = _load_registry()
    registered_ids = {entry["id"] for entry in _entries(payload)}
    missing: list[str] = []

    for path, marker_map in REQUIRED_MARKERS.items():
        source = path.read_text(encoding="utf-8")
        rel_path = path.relative_to(PROJECT_ROOT)
        for marker, entry_id in marker_map.items():
            if marker in source and entry_id not in registered_ids:
                missing.append(f"{rel_path}: {marker} -> {entry_id}")

    assert not missing, (
        "Config compatibility markers must be registered before they are accepted:\n"
        + "\n".join(missing)
    )


def test_no_new_unregistered_config_compatibility_test_names() -> None:
    """Legacy/migration config tests must be explicitly tied to registry scope."""
    config_tests = PROJECT_ROOT / "tests" / "unit" / "infrastructure" / "config"
    suspects = sorted(config_tests.glob("*legacy*normalization*.py"))
    registry_text = REGISTRY_PATH.read_text(encoding="utf-8")

    missing = [
        path.relative_to(PROJECT_ROOT).as_posix()
        for path in suspects
        if path.relative_to(PROJECT_ROOT).as_posix() not in registry_text
    ]

    assert not missing, (
        "Legacy config normalization tests must be listed in "
        "config_compatibility_registry.yaml:\n" + "\n".join(missing)
    )
