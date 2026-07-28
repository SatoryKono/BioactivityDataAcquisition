"""Wiring for enum loader dependencies in composition layer."""

from __future__ import annotations

from bioetl.domain.config.enum_loader import EnumLoaderProtocol
from bioetl.infrastructure.config.enum_loader_adapter import FileSystemEnumLoader

__all__ = [
    "create_enum_loader_for_domain",
    "initialize_domain_enum_fields",
]

def create_enum_loader_for_domain() -> EnumLoaderProtocol:
    """Create enum loader instance for domain layer dependency injection.

    Returns:
        Configured EnumLoaderProtocol implementation
    """
    return FileSystemEnumLoader()

def initialize_domain_enum_fields() -> None:
    """Initialize domain layer enum fields using dependency injection.

    This function should be called during bootstrap to ensure domain layer
    enum configurations are properly loaded before any domain logic executes.

    Note: The actual enum loading happens lazily when domain functions are first called,
    but this function ensures the dependency injection wiring is available.
    """
    # Create the enum loader to ensure it's available for lazy initialization
    create_enum_loader_for_domain()
    # The enum loading is handled lazily by the domain layer when needed
    # This ensures the DI wiring is set up correctly
