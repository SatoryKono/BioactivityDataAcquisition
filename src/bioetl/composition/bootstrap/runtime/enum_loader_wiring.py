"""Wiring for enum loader dependencies in composition layer."""

from __future__ import annotations

from bioetl.domain.config.enum_loader import EnumLoaderPort
from bioetl.infrastructure.config.enum_loader_adapter import FileSystemEnumLoader

__all__ = ["create_enum_loader_for_domain"]


def create_enum_loader_for_domain() -> EnumLoaderPort:
    """Create enum loader instance for domain layer dependency injection.
    
    Returns:
        Configured EnumLoaderPort implementation
    """
    return FileSystemEnumLoader()
