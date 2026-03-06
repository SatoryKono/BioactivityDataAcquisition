"""Architecture quality-gate tests for exemption registry metadata."""

from __future__ import annotations

from bioetl.infrastructure.quality import (
    get_registry_values,
    load_exemptions_registry,
    validate_exemption_key_normalization,
    validate_exemptions_registry,
)


def test_exemption_registry_has_required_sections() -> None:
    raw = load_exemptions_registry()
    registries = raw.get("registries", {})
    required = {
        "file_size_limits",
        "function_complexity",
        "function_length",
        "class_size",
        "class_method_count",
        "god_object",
        "domain_complexity",
    }
    missing = sorted(required - set(registries))
    assert not missing, f"Missing exemption registries: {missing}"


def test_exemption_registry_metadata_is_complete() -> None:
    metadata_errors, expired_entries = validate_exemptions_registry()
    assert not metadata_errors, (
        "Exemption registry metadata errors found:\n"
        + "\n".join(f"  - {e}" for e in metadata_errors)
    )
    # Expiry enforcement is controlled by CI gate mode (warn/block).
    assert isinstance(expired_entries, list)


def test_exemption_registry_file_size_keys_are_normalized() -> None:
    key_errors = validate_exemption_key_normalization()
    assert not key_errors, (
        "Exemption registry key normalization errors found:\n"
        + "\n".join(f"  - {e}" for e in key_errors)
    )


def test_exemption_registry_policy_requires_owner_removal_step_and_due_date() -> None:
    """Registry policy must enforce owner/removal-step/due-date metadata."""
    raw = load_exemptions_registry()
    policy = raw.get("policy", {})
    assert isinstance(policy, dict), "policy section must be a mapping"

    required_fields = policy.get("required_fields", [])
    assert isinstance(required_fields, list), "policy.required_fields must be a list"
    assert "owner" in required_fields, "policy.required_fields must include 'owner'"
    assert "removal_step" in required_fields, (
        "policy.required_fields must include 'removal_step'"
    )
    assert any(field in required_fields for field in ("expires_on", "due_on")), (
        "policy.required_fields must include due-date field ('expires_on' or 'due_on')"
    )


def test_exemption_registries_are_not_empty() -> None:
    for registry_name in (
        "file_size_limits",
        "function_complexity",
        "function_length",
        "class_size",
        "class_method_count",
        "god_object",
    ):
        values = get_registry_values(registry_name)
        assert values, f"Registry '{registry_name}' must not be empty"
