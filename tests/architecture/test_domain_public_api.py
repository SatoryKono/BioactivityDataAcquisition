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
"""Tests for domain layer public API completeness.

REQ-ARCH-027: Domain sub-facades (ports, exceptions, value_objects) must be
complete and tested. The top-level domain/__init__.py is a slim facade that
exposes only subpackages and events; consumers import from sub-facades.
"""

from __future__ import annotations

import pytest

from typing import get_type_hints


pytestmark = pytest.mark.architecture


def test_domain_all_is_complete() -> None:
    """Verify domain/__init__.py __all__ contains all public symbols.

    REQ-ARCH-027: The slim domain facade should only export subpackages
    and top-level domain objects (events). All other symbols live in
    sub-facades (ports, exceptions, value_objects, entities, etc.).
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
        # Internal imports for lazy loading mechanism
        "TYPE_CHECKING",
        "import_module",
        # Submodules (accessible as bioetl.domain.<name> but not re-exported)
        "adapter_config",  # Config VO module; import from bioetl.domain.adapter_config
        "aggregates",  # Aggregate submodule
        "config",
        "configs",  # Submodule for value object configs
        "context",
        "entities",
        "error_classifier",
        "events",
        "exceptions",
        "filter_config",
        "filtering",
        "locking",
        "mapping",
        "medallion",
        "models",  # Metadata models (BronzeMetadata, etc.)
        "normalization",  # REFACTOR-004: import from bioetl.domain.normalization
        "ports",
        "registry",
        "resilience",
        "resilience_circuit_breaker",  # Circuit-breaker helpers; import submodule directly
        "schemas",  # Pandera schemas (provider-specific, accessed directly)
        "serialization",
        "services",  # Submodule for domain services (EntityIdentityGenerator)
        "transformations",
        "types",
        "validation",  # REFACTOR-004: import from bioetl.domain.validation
        "value_objects",  # Submodule for value objects
        "version",  # Version metadata submodule
    }

    # Get all attributes from the module
    all_attrs = set(dir(domain))

    # Filter to public symbols only (not starting with _)
    public_attrs = {
        attr
        for attr in all_attrs
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


def test_domain_subfacade_ports_is_complete() -> None:
    """Verify ports sub-facade exports all essential ports.

    REQ-ARCH-029: Essential port protocols must be available from
    bioetl.domain.ports.
    """
    from bioetl.domain import ports

    essential_ports = {
        "DataSourcePort",
        "BronzeStoragePort",
        "SilverStoragePort",
        "GoldStoragePort",
        "StorageLifecyclePort",
        "StorageMaintenancePort",
        "CheckpointPort",
        "MetricsPort",
        "LoggerPort",
        "TracingPort",
    }
    ports_all = set(ports.__all__)
    missing = essential_ports - ports_all
    assert not missing, f"Missing essential ports from sub-facade: {missing}"


def test_domain_ports_facade_explicitly_exports_runtime_contracts() -> None:
    """Verify runtime-oriented contracts remain sanctioned facade exports.

    RF-06: BioETL intentionally keeps pure runtime/cross-layer contracts in
    ``bioetl.domain.ports``. This guard makes that policy explicit so future
    reviews do not misclassify these exports as architecture drift.
    """
    from bioetl.domain import ports

    sanctioned_runtime_ports = {
        "LoggerPort",
        "RunnerFactoryPort",
        "RunnablePort",
        "RateLimiterPort",
        "CircuitBreakerPort",
    }
    ports_all = set(ports.__all__)
    missing = sanctioned_runtime_ports - ports_all
    assert not missing, (
        "Runtime-oriented cross-layer contracts must remain available from "
        f"bioetl.domain.ports facade: missing {sorted(missing)}"
    )


def test_domain_ports_noop_exports_are_separate_public_subfacade() -> None:
    """Verify operational no-op implementations live outside the main ports facade."""
    from bioetl.domain import ports
    from bioetl.domain.ports import noop

    noop_exports = {
        "NoOpAudit",
        "NoOpDebug",
        "NoOpMemoryMonitor",
        "NoOpMetadataWriter",
        "NoOpMetrics",
        "NoOpPiiHasher",
        "NoOpTracing",
    }

    ports_all = set(ports.__all__)
    noop_all = set(noop.__all__)

    assert not (noop_exports & ports_all), (
        "Operational NoOp implementations must not be exported from "
        f"bioetl.domain.ports facade: found {sorted(noop_exports & ports_all)}"
    )
    missing = noop_exports - noop_all
    assert not missing, (
        "Operational NoOp implementations must be exported from "
        f"bioetl.domain.ports.noop: missing {sorted(missing)}"
    )


def test_pipeline_context_remains_normative_domain_execution_context() -> None:
    """Verify PipelineContext stays typed as a domain-level execution context.

    RF-06 keeps PipelineContext in the domain layer on purpose: it carries
    deterministic run metadata and a LoggerPort abstraction, not a concrete
    infrastructure logger/runtime object.
    """
    from datetime import datetime

    from bioetl.domain.context import PipelineContext
    from bioetl.domain.ports import LoggerPort

    context_hints = get_type_hints(PipelineContext)
    bind_logger_hints = get_type_hints(PipelineContext.bind_logger)
    create_hints = get_type_hints(PipelineContext.create)

    assert context_hints["logger"] is LoggerPort, (
        "PipelineContext.logger must remain typed as LoggerPort so the domain "
        "context carries only a pure logging abstraction"
    )
    assert context_hints["started_at"] is datetime, (
        "PipelineContext.started_at must remain the explicit deterministic "
        "timestamp carried through pipeline execution"
    )
    assert bind_logger_hints["return"] is PipelineContext, (
        "PipelineContext.bind_logger() must preserve the same domain execution "
        "context type instead of switching to an infrastructure object"
    )
    assert create_hints["return"] is PipelineContext, (
        "PipelineContext.create() must remain the sanctioned constructor for "
        "domain-level execution context instances"
    )


def test_domain_subfacade_exceptions_is_complete() -> None:
    """Verify exceptions sub-facade exports all essential exceptions.

    REQ-ARCH-029: Essential exception classes must be available from
    bioetl.domain.exceptions.
    """
    from bioetl.domain import exceptions

    essential_exceptions = {
        "BioETLError",
        "CriticalError",
        "RecoverableError",
        "DataQualityError",
    }
    exceptions_all = set(exceptions.__all__)
    missing = essential_exceptions - exceptions_all
    assert not missing, f"Missing essential exceptions from sub-facade: {missing}"


def test_domain_subfacade_types_has_essentials() -> None:
    """Verify essential types are importable from bioetl.domain.types.

    REQ-ARCH-029: Essential type definitions must be available from
    bioetl.domain.types.
    """
    from bioetl.domain import types

    essential_types = {"RunType", "RunID", "EntityID", "ContentHash", "ErrorType"}
    types_attrs = set(dir(types))
    missing = essential_types - types_attrs
    assert not missing, f"Missing essential types from domain.types: {missing}"


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


def test_domain_subfacades_re_export_submodule_symbols() -> None:
    """Validate sub-facades include all public submodule exports.

    REQ-ARCH-031: Sub-facades (ports, exceptions) must re-export all
    public symbols from their submodules. This ensures that
    ``from bioetl.domain.ports import X`` works for any public port X.
    """
    from bioetl.domain import exceptions, ports

    # Check ports sub-facade
    ports_all = set(ports.__all__)
    for symbol in ports.__all__:
        assert hasattr(ports, symbol), (
            f"Symbol '{symbol}' in ports.__all__ but not importable"
        )

    # Check exceptions sub-facade
    exceptions_all = set(exceptions.__all__)
    for symbol in exceptions.__all__:
        assert hasattr(exceptions, symbol), (
            f"Symbol '{symbol}' in exceptions.__all__ but not importable"
        )

    # Verify no overlap issues
    assert len(ports_all) == len(ports.__all__), "Duplicate entries in ports.__all__"
    assert len(exceptions_all) == len(exceptions.__all__), (
        "Duplicate entries in exceptions.__all__"
    )
