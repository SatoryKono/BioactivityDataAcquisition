"""Bootstrap functions for ADR CLI operations.

Provides a factory for the ADR service port used by CLI commands and
other interfaces. Uses default repository-relative path for ADR docs.
"""

from __future__ import annotations

from typing import cast

from bioetl.domain.ports import AdrServicePort
from bioetl.infrastructure.adr.fs_adr_service import FilesystemAdrCatalog

__all__ = ["bootstrap_adr_service"]


def bootstrap_adr_service() -> AdrServicePort:
    """Bootstrap ADR service using default filesystem implementation.

    Returns:
        AdrServicePort wired to the repository docs folder.
    """

    # Default path is used inside FilesystemAdrCatalog; allow future injection via env
    service = FilesystemAdrCatalog()
    return cast(AdrServicePort, service)
