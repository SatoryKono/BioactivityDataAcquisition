"""Architecture guardrails for deterministic identity-generation policy."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
POLICY_YAML = ROOT / "configs" / "quality" / "determinism_identity_policy.yaml"
POLICY_REVIEW_DATE = date(2026, 5, 15)
SCAN_ROOTS = (
    ROOT / "src" / "bioetl" / "domain" / "aggregates",
    ROOT / "src" / "bioetl" / "composition" / "factories",
)
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


def _load_policy() -> dict[str, object]:
    with POLICY_YAML.open(encoding="utf-8") as stream:
        payload = yaml.safe_load(stream) or {}
    assert isinstance(payload, dict), "determinism identity policy must be a mapping"
    return payload


def _iter_uuid4_files() -> set[str]:
    discovered: set[str] = set()
    for root in SCAN_ROOTS:
        for path in root.rglob("*.py"):
            text = path.read_text(encoding="utf-8")
            if "uuid4(" in text or "from uuid import uuid4" in text:
                discovered.add(path.relative_to(ROOT).as_posix())
    return discovered


@pytest.mark.architecture
def test_determinism_identity_policy_has_expected_shape() -> None:
    """Occurrence-only random identity generators must be explicit and fresh."""
    payload = _load_policy()

    assert payload["version"] == 1
    assert payload["policy_scope"] == "deterministic_identity_generation"
    assert date.fromisoformat(str(payload["review_date"])) >= POLICY_REVIEW_DATE

    entries = payload.get("allowed_occurrence_identity_generators")
    assert isinstance(entries, list) and entries

    seen_paths: set[str] = set()
    for entry in entries:
        assert isinstance(entry, dict)
        assert REQUIRED_ENTRY_FIELDS <= set(entry)
        assert str(entry["path"]).startswith("src/bioetl/")
        assert str(entry["generator"]) == "uuid4"
        assert str(entry["semantic_classification"]) == "occurrence-only"
        assert str(entry["replay_semantics"]) == "excluded_from_execution_fingerprint"
        assert str(entry["rationale"]).strip()
        assert str(entry["issue"]).startswith("#")
        seen_paths.add(str(entry["path"]))

    assert len(seen_paths) == len(entries), (
        "Each occurrence identity policy row must own one source path."
    )


@pytest.mark.architecture
def test_uuid4_identity_generators_are_policy_allowlisted() -> None:
    """New uuid4 usage in deterministic-sensitive paths requires policy review."""
    payload = _load_policy()
    entries = payload["allowed_occurrence_identity_generators"]
    assert isinstance(entries, list)
    allowed_paths = {str(entry["path"]) for entry in entries}
    discovered_paths = _iter_uuid4_files()

    assert discovered_paths <= allowed_paths, (
        "Unreviewed uuid4 identity generation found in deterministic-sensitive "
        "domain/composition paths:\n"
        + "\n".join(sorted(discovered_paths - allowed_paths))
    )
    assert allowed_paths <= discovered_paths, (
        "Determinism identity policy contains stale paths without uuid4 usage:\n"
        + "\n".join(sorted(allowed_paths - discovered_paths))
    )


@pytest.mark.architecture
def test_policy_entries_still_match_source_files() -> None:
    """Policy entries must point to live files and live symbols."""
    payload = _load_policy()
    entries = payload["allowed_occurrence_identity_generators"]
    assert isinstance(entries, list)

    for entry in entries:
        assert isinstance(entry, dict)
        path = ROOT / str(entry["path"])
        assert path.exists(), f"Missing policy source path: {entry['path']}"
        text = path.read_text(encoding="utf-8")
        assert "uuid4(" in text, f"Policy path no longer calls uuid4: {entry['path']}"
        for symbol_part in str(entry["symbol"]).split("."):
            assert symbol_part in text, (
                "Policy symbol no longer appears in source file: "
                f"{entry['symbol']} in {entry['path']}"
            )
