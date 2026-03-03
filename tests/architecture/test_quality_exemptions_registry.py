"""Architecture quality-gate tests for exemption registry metadata."""

from __future__ import annotations

from bioetl.infrastructure.quality import (
    get_registry_values,
    load_exemptions_registry,
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


def test_exemption_registries_are_not_empty() -> None:
    for registry_name in (
        "file_size_limits",
        "function_complexity",
        "function_length",
        "class_size",
        "class_method_count",
        "god_object",
        "domain_complexity",
    ):
        values = get_registry_values(registry_name)
        assert values, f"Registry '{registry_name}' must not be empty"
