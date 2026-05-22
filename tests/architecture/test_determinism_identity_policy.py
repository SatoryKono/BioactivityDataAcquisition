"""Architecture guardrails for deterministic identity-generation policy."""

from __future__ import annotations

import ast
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from inspect import signature
from pathlib import Path

import pytest
import yaml

from bioetl.composition.runtime_builders._run_manifest_refs import (
    legacy_config_hash_from_resolved_config_hash,
)
from bioetl.domain.normalization import build_execution_identity_payload

ROOT = Path(__file__).resolve().parents[2]
POLICY_YAML = ROOT / "configs" / "quality" / "determinism_identity_policy.yaml"
POLICY_REVIEW_DATE = date(2026, 5, 15)
SCAN_ROOTS = (ROOT / "src" / "bioetl",)
REQUIRED_ENTRY_FIELDS = frozenset(
    {
        "path",
        "symbol",
        "generator",
        "identity_field",
        "semantic_classification",
        "replay_semantics",
        "rationale",
        "issue",
    }
)


@dataclass(frozen=True, slots=True)
class Uuid4CallSite:
    """One production uuid4 call site that must be policy reviewed."""

    path: str
    symbol: str
    line: int


def _load_policy() -> dict[str, object]:
    with POLICY_YAML.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}
    assert isinstance(payload, dict), "determinism identity policy must be a mapping"
    return payload


def _build_parent_map(tree: ast.AST) -> dict[ast.AST, ast.AST]:
    return {
        child: node for node in ast.walk(tree) for child in ast.iter_child_nodes(node)
    }


def _assignment_target_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
        return node.target.id
    if isinstance(node, ast.Assign):
        names = [target.id for target in node.targets if isinstance(target, ast.Name)]
        if len(names) == 1:
            return names[0]
    return None


def _uuid4_call_symbol(node: ast.AST, parents: dict[ast.AST, ast.AST]) -> str:
    class_names: list[str] = []
    function_names: list[str] = []
    assignment_target: str | None = None

    current = node
    while current in parents:
        current = parents[current]
        if assignment_target is None:
            assignment_target = _assignment_target_name(current)
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef)):
            function_names.append(current.name)
        elif isinstance(current, ast.ClassDef):
            class_names.append(current.name)

    if function_names:
        return ".".join([*reversed(class_names), *reversed(function_names)])
    if assignment_target and class_names:
        return ".".join([*reversed(class_names), assignment_target])
    if class_names:
        return ".".join(reversed(class_names))
    return "<module>"


def _is_uuid4_call(node: ast.AST) -> bool:
    if not isinstance(node, ast.Call):
        return False
    if isinstance(node.func, ast.Name):
        return node.func.id == "uuid4"
    return isinstance(node.func, ast.Attribute) and node.func.attr == "uuid4"


def _iter_uuid4_call_sites() -> set[Uuid4CallSite]:
    discovered: set[Uuid4CallSite] = set()
    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            tree = ast.parse(path.read_text(encoding="utf-8"))
            parents = _build_parent_map(tree)
            relative_path = path.relative_to(ROOT).as_posix()
            for node in ast.walk(tree):
                if _is_uuid4_call(node):
                    discovered.add(
                        Uuid4CallSite(
                            path=relative_path,
                            symbol=_uuid4_call_symbol(node, parents),
                            line=node.lineno,
                        )
                    )
    return discovered


def _policy_occurrence_call_sites(payload: dict[str, object]) -> set[tuple[str, str]]:
    entries = payload["allowed_occurrence_identity_generators"]
    assert isinstance(entries, list)
    return {
        (str(entry["path"]), str(entry["symbol"]))
        for entry in entries
        if isinstance(entry, dict)
    }


def _format_call_sites(call_sites: Iterator[Uuid4CallSite]) -> str:
    return "\n".join(
        f"{site.path}:{site.line} {site.symbol}"
        for site in sorted(call_sites, key=lambda site: (site.path, site.line))
    )


@pytest.mark.architecture
def test_determinism_identity_policy_has_expected_shape() -> None:
    """Occurrence-only random identity generators must be explicit and fresh."""
    payload = _load_policy()

    assert payload["version"] == 1
    assert payload["policy_scope"] == "deterministic_identity_generation"
    assert date.fromisoformat(str(payload["review_date"])) >= POLICY_REVIEW_DATE
    reduction_plan = payload.get("compatibility_reduction_plan")
    assert isinstance(reduction_plan, dict)
    assert reduction_plan.get("linked_issue") == "#4517"
    assert reduction_plan.get("review_date") == "2026-09-30"
    assert set(reduction_plan.get("allowed_outcomes", [])) == {
        "retain_occurrence_only_generator",
        "keep_compatibility_alias_but_block_new_semantics",
        "keep_hash_policy_split_until_backfill",
    }

    entries = payload.get("allowed_occurrence_identity_generators")
    assert isinstance(entries, list) and entries
    occurrence_budget = reduction_plan.get("occurrence_identity_budget")
    assert isinstance(occurrence_budget, dict)
    assert occurrence_budget.get("max_allowed_call_sites") == len(entries)
    assert isinstance(occurrence_budget.get("ratchet_policy"), str)

    seen_call_sites: set[tuple[str, str]] = set()
    for entry in entries:
        assert isinstance(entry, dict)
        assert REQUIRED_ENTRY_FIELDS <= set(entry)
        assert str(entry["path"]).startswith("src/bioetl/")
        assert str(entry["generator"]) == "uuid4"
        assert str(entry["semantic_classification"]) == "occurrence-only"
        assert str(entry["replay_semantics"]) == "excluded_from_execution_fingerprint"
        assert str(entry["rationale"]).strip()
        assert str(entry["issue"]).startswith("#")
        call_site = (str(entry["path"]), str(entry["symbol"]))
        assert call_site not in seen_call_sites, (
            "Each occurrence identity policy row must own one source call site: "
            f"{call_site}"
        )
        seen_call_sites.add(call_site)

    legacy_config_hash_policy = payload.get("legacy_config_hash_policy")
    assert isinstance(legacy_config_hash_policy, dict)
    assert legacy_config_hash_policy["field"] == "config_hash"
    assert legacy_config_hash_policy["alias_of"] == "resolved_config_hash"
    assert legacy_config_hash_policy["semantic_classification"] == (
        "compatibility-only"
    )
    assert legacy_config_hash_policy["replay_identity_anchor"] is False
    assert legacy_config_hash_policy["primary_semantic_anchor"] == (
        "effective_config_hash"
    )
    assert set(legacy_config_hash_policy["canonical_replay_anchors"]) == {
        "execution_fingerprint",
        "resolved_config_hash",
        "effective_config_hash",
    }
    assert str(legacy_config_hash_policy["issue"]) == "#4467"
    assert (
        legacy_config_hash_policy["reviewed_outcome"]
        == "keep_compatibility_alias_but_block_new_semantics"
    )

    hash_policy_budget = reduction_plan.get("replay_hash_policy_budget")
    assert isinstance(hash_policy_budget, dict)
    assert hash_policy_budget.get("allowed_legacy_alias_fields") == ["config_hash"]
    assert set(hash_policy_budget.get("allowed_hash_datetime_defaults", [])) == {
        "v1_date",
        "v2_datetime_utc",
    }
    assert isinstance(hash_policy_budget.get("ratchet_policy"), str)


@pytest.mark.architecture
def test_uuid4_identity_generators_are_policy_allowlisted() -> None:
    """New runtime uuid4 call sites require policy review before replay use."""
    payload = _load_policy()
    allowed_call_sites = _policy_occurrence_call_sites(payload)
    discovered_call_sites = _iter_uuid4_call_sites()
    discovered_keys = {
        (call_site.path, call_site.symbol) for call_site in discovered_call_sites
    }

    unreviewed = {
        call_site
        for call_site in discovered_call_sites
        if (call_site.path, call_site.symbol) not in allowed_call_sites
    }
    assert not unreviewed, (
        "Unreviewed uuid4 identity generation found in src/bioetl runtime paths:\n"
        + _format_call_sites(iter(unreviewed))
    )
    assert allowed_call_sites <= discovered_keys, (
        "Determinism identity policy contains stale call sites without uuid4 usage:\n"
        + "\n".join(
            f"{path} {symbol}"
            for path, symbol in sorted(allowed_call_sites - discovered_keys)
        )
    )


@pytest.mark.architecture
def test_policy_entries_still_match_source_files() -> None:
    """Policy entries must point to live files and live uuid4 call sites."""
    payload = _load_policy()
    entries = payload["allowed_occurrence_identity_generators"]
    assert isinstance(entries, list)
    discovered_call_sites = {
        (call_site.path, call_site.symbol) for call_site in _iter_uuid4_call_sites()
    }

    for entry in entries:
        assert isinstance(entry, dict)
        path = ROOT / str(entry["path"])
        assert path.exists(), f"Missing policy source path: {entry['path']}"
        call_site = (str(entry["path"]), str(entry["symbol"]))
        assert call_site in discovered_call_sites, (
            "Policy call site no longer calls uuid4: "
            f"{entry['symbol']} in {entry['path']}"
        )


@pytest.mark.architecture
def test_legacy_config_hash_cannot_become_execution_identity_anchor() -> None:
    """The compatibility alias must stay outside semantic execution fingerprints."""
    payload = _load_policy()
    legacy_policy = payload["legacy_config_hash_policy"]
    assert isinstance(legacy_policy, dict)

    assert legacy_config_hash_from_resolved_config_hash("resolved-hash") == (
        "resolved-hash"
    )

    execution_identity_params = set(
        signature(build_execution_identity_payload).parameters
    )
    assert "effective_config_hash" in execution_identity_params
    assert "config_hash" not in execution_identity_params
    assert "run_id" not in execution_identity_params
    assert "manifest_id" not in execution_identity_params
    assert "created_at" not in execution_identity_params
    assert legacy_policy["replay_identity_anchor"] is False
    assert legacy_policy["primary_semantic_anchor"] in execution_identity_params
