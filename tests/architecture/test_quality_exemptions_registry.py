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
"""Architecture quality-gate tests for exemption registry metadata."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from bioetl.infrastructure.quality import (
    EXEMPTION_REGISTRIES_ALLOW_EMPTY,
    REQUIRED_EXEMPTION_REGISTRIES,
    get_registry_values,
    load_exemptions_registry,
    validate_exemption_key_normalization,
    validate_exemption_target_references,
    validate_exemptions_registry,
)


pytestmark = [pytest.mark.architecture, pytest.mark.slow]


def test_exemption_registry_has_required_sections() -> None:
    raw = load_exemptions_registry()
    registries = raw.get("registries", {})
    missing = sorted(set(REQUIRED_EXEMPTION_REGISTRIES) - set(registries))
    assert not missing, f"Missing exemption registries: {missing}"


def test_exemption_registry_metadata_is_complete() -> None:
    metadata_errors, expired_entries = validate_exemptions_registry()
    assert not metadata_errors, (
        "Exemption registry metadata errors found:\n"
        + "\n".join(f"  - {e}" for e in metadata_errors)
    )
    # Expiry enforcement is controlled by CI gate mode (warn/block).
    assert isinstance(expired_entries, list)


def test_exemption_registry_does_not_reintroduce_warning_mode_until() -> None:
    """Legacy warning_mode_until gate must stay removed from live policy."""
    raw = load_exemptions_registry()
    policy = raw.get("policy", {})
    assert isinstance(policy, dict)
    assert "warning_mode_until" not in policy


def test_exemption_registry_file_size_keys_are_normalized() -> None:
    key_errors = validate_exemption_key_normalization()
    assert not key_errors, (
        "Exemption registry key normalization errors found:\n"
        + "\n".join(f"  - {e}" for e in key_errors)
    )


def test_exemption_registry_policy_requires_tracking_classification_and_due_date() -> (
    None
):
    """Registry policy must enforce tracking/classification/removal metadata."""
    raw = load_exemptions_registry()
    policy = raw.get("policy", {})
    assert isinstance(policy, dict), "policy section must be a mapping"

    required_fields = policy.get("required_fields", [])
    assert isinstance(required_fields, list), "policy.required_fields must be a list"
    assert "owner" in required_fields, "policy.required_fields must include 'owner'"
    assert "classification" in required_fields, (
        "policy.required_fields must include 'classification'"
    )
    assert "linked_rf" in required_fields, (
        "policy.required_fields must include 'linked_rf'"
    )
    assert "removal_step" in required_fields, (
        "policy.required_fields must include 'removal_step'"
    )
    assert any(field in required_fields for field in ("expires_on", "due_on")), (
        "policy.required_fields must include due-date field ('expires_on' or 'due_on')"
    )


def test_exemption_registry_zero_state_review_text_is_not_stale() -> None:
    """Empty exemption registries must not claim active exemptions remain."""
    raw = load_exemptions_registry()
    registries = raw.get("registries", {})
    assert isinstance(registries, dict)
    all_empty = all(
        isinstance(entries, dict) and not entries for entries in registries.values()
    )
    if not all_empty:
        return

    policy = raw.get("policy", {})
    assert isinstance(policy, dict)
    review_history = policy.get("review_history", [])
    assert isinstance(review_history, list)
    rationale_text = " ".join(
        str(item.get("rationale", ""))
        for item in review_history
        if isinstance(item, dict)
    ).lower()
    forbidden_fragments = (
        "two intentional exceptions",
        "active metric exemptions are already reduced to two",
    )
    assert not any(fragment in rationale_text for fragment in forbidden_fragments)
    assert "zero" in rationale_text


def test_exemption_registry_targets_are_live() -> None:
    """Path- and symbol-based exemptions must point to live source targets."""
    target_errors = validate_exemption_target_references()
    assert not target_errors, (
        "Exemption registry target-reference errors found:\n"
        + "\n".join(f"  - {e}" for e in target_errors)
    )


def test_exemption_registries_non_empty_except_allowlist() -> None:
    required_non_empty = set(REQUIRED_EXEMPTION_REGISTRIES) - set(
        EXEMPTION_REGISTRIES_ALLOW_EMPTY
    )
    for registry_name in sorted(required_non_empty):
        values = get_registry_values(registry_name)
        assert values, f"Registry '{registry_name}' must not be empty"


def test_allowlisted_empty_registry_remains_valid(tmp_path: Path) -> None:
    raw = load_exemptions_registry()
    registries = raw.get("registries", {})
    assert isinstance(registries, dict)
    registries["god_object"] = {}

    test_registry = tmp_path / "exemptions.yaml"
    test_registry.write_text(yaml.safe_dump(raw), encoding="utf-8")

    metadata_errors, _expired_entries = validate_exemptions_registry(test_registry)
    assert not any(
        error.startswith("god_object: registry must not be empty")
        for error in metadata_errors
    )

    values = get_registry_values("god_object", test_registry)
    assert values == {}


def test_allowlisted_empty_class_method_count_registry_remains_valid(
    tmp_path: Path,
) -> None:
    raw = load_exemptions_registry()
    registries = raw.get("registries", {})
    assert isinstance(registries, dict)
    registries["class_method_count"] = {}

    test_registry = tmp_path / "exemptions.class_method_count.empty.yaml"
    test_registry.write_text(yaml.safe_dump(raw), encoding="utf-8")

    metadata_errors, _expired_entries = validate_exemptions_registry(test_registry)
    assert not any(
        error.startswith("class_method_count: registry must not be empty")
        for error in metadata_errors
    )

    values = get_registry_values("class_method_count", test_registry)
    assert values == {}
