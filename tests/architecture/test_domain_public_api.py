"""Tests for domain layer public API completeness.

REQ-ARCH-027: Domain layer __all__ must be complete and tested.
All public symbols exported from domain submodules should be listed in __all__.
"""

from __future__ import annotations

from pathlib import Path



def test_domain_all_is_complete(src_dir: Path) -> None:
    """Verify domain/__init__.py __all__ contains all public symbols.

    REQ-ARCH-027: All public symbols from domain submodules must be in __all__.
    This ensures stable public API and prevents accidental exports.
    """
    import bioetl.domain as domain

    # Symbols that are not meant to be public (internal, dunder, submodules)
    excluded_patterns = {
        "__builtins__",
        "__cached__",
        "__doc__",
        "__file__",
        "__loader__",
        "__name__",
        "__package__",
        "__path__",
        "__spec__",
        # Special imports (from __future__ import annotations)
        "annotations",
        # Submodules (imported but not re-exported individually)
        "config",
        "context",
        "entities",
        "error_classifier",
        "events",
        "exceptions",
        "filter_config",
        "medallion",
        "ports",
        "resilience",
        "serialization",
        "transformations",
        "types",
    }

    # Get all attributes from the module
    all_attrs = set(dir(domain))

    # Filter to public symbols only (not starting with _)
    public_attrs = {
        attr for attr in all_attrs
        if not attr.startswith("_") and attr not in excluded_patterns
    }

    # Get declared __all__
    declared_all = set(domain.__all__)

    # Check for symbols in module but not in __all__
    missing_from_all = public_attrs - declared_all
    assert not missing_from_all, (
        "Public symbols missing from domain.__all__:\n"
        + "\n".join(f"  - {s}" for s in sorted(missing_from_all))
    )

    # Check for symbols in __all__ but not actually exported
    not_exported = declared_all - public_attrs
    assert not not_exported, (
        "Symbols in __all__ but not exported from domain:\n"
        + "\n".join(f"  - {s}" for s in sorted(not_exported))
    )


def test_domain_all_symbols_are_importable() -> None:
    """Verify all symbols in domain.__all__ can be imported.

    REQ-ARCH-028: All symbols declared in __all__ must be importable.
    """
    from bioetl import domain

    for symbol in domain.__all__:
        assert hasattr(domain, symbol), (
            f"Symbol '{symbol}' is in __all__ but cannot be accessed on domain module"
        )
        # Verify it's not None (actual object exists)
        obj = getattr(domain, symbol)
        assert obj is not None or symbol in {"None"}, (
            f"Symbol '{symbol}' is None - may indicate broken import"
        )


def test_domain_public_api_categories() -> None:
    """Verify domain __all__ has expected categories of exports.

    REQ-ARCH-029: Domain layer must export all standard categories:
    - Types (enums, type aliases)
    - Entities (domain objects)
    - Ports (Protocol interfaces)
    - Exceptions (error hierarchy)
    - Transformations (pure functions)
    """
    from bioetl import domain

    all_symbols = set(domain.__all__)

    # Check for essential types
    essential_types = {"RunType", "RunID", "EntityID", "ContentHash", "ErrorType"}
    missing_types = essential_types - all_symbols
    assert not missing_types, f"Missing essential types: {missing_types}"

    # Check for essential ports
    essential_ports = {"DataSourcePort", "StoragePort", "CheckpointPort", "MetricsPort"}
    missing_ports = essential_ports - all_symbols
    assert not missing_ports, f"Missing essential ports: {missing_ports}"

    # Check for essential exceptions
    essential_exceptions = {"BioETLError", "CriticalError", "RecoverableError"}
    missing_exceptions = essential_exceptions - all_symbols
    assert not missing_exceptions, f"Missing essential exceptions: {missing_exceptions}"

    # Check for context
    assert "PipelineContext" in all_symbols, "PipelineContext must be in __all__"
    assert "PipelineRunContext" in all_symbols, "PipelineRunContext must be in __all__"


def test_domain_no_infrastructure_types_in_all() -> None:
    """Verify domain.__all__ does not export infrastructure types.

    REQ-ARCH-030: Domain layer must not expose infrastructure concerns.
    """
    from bioetl import domain

    # Patterns that would indicate infrastructure leakage
    infrastructure_patterns = [
        "Prometheus",
        "HTTP",
        "Delta",
        "Polars",
        "Client",
        "Adapter",
        "Writer",
        "Reader",
    ]

    for symbol in domain.__all__:
        for pattern in infrastructure_patterns:
            assert pattern not in symbol, (
                f"Symbol '{symbol}' appears to be infrastructure type "
                f"(contains '{pattern}') - should not be in domain.__all__"
            )


def test_domain_exports_all_submodule_symbols() -> None:
    """Validate domain.__all__ includes all public submodule exports.

    REQ-ARCH-031: Domain facade must re-export all public symbols from submodules.
    This ensures that `from bioetl.domain import X` works for any public symbol X
    defined in exceptions, ports, or entities submodules.
    """
    from bioetl import domain
    from bioetl.domain import exceptions, ports, entities

    domain_all = set(domain.__all__)

    # Submodules with __all__ that should be fully exported
    submodules = [
        ("exceptions", exceptions),
        ("ports", ports),
        ("entities", entities),
    ]

    missing_symbols: list[str] = []

    for submodule_name, submodule in submodules:
        for symbol in submodule.__all__:
            if symbol not in domain_all:
                missing_symbols.append(f"{submodule_name}.{symbol}")

    assert not missing_symbols, (
        "Submodule symbols missing from domain.__all__:\n"
        + "\n".join(f"  - {s}" for s in sorted(missing_symbols))
    )
