"""Composition services for cross-cutting concerns.

Import owner modules directly for service implementations. This package keeps
only the stable versioning surface and the ``versioning`` submodule namespace.
"""

from __future__ import annotations

from bioetl.composition.services.versioning import (
    compute_config_hash,
    get_code_revision_provenance,
    get_dependency_lock_hash,
    get_git_commit,
    get_pipeline_version,
)

from . import versioning

__all__ = [
    "compute_config_hash",
    "get_code_revision_provenance",
    "get_dependency_lock_hash",
    "get_git_commit",
    "get_pipeline_version",
    "versioning",
]
