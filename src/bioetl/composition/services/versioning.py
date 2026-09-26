"""Composition facade. Implementation lives in `bioetl.infrastructure.provenance.code_revision` (#11241)."""

from __future__ import annotations

from bioetl.infrastructure.provenance.code_revision import (
    CodeRevisionProvenance,
    compute_config_hash,
    get_code_revision_provenance,
    get_dependency_lock_hash,
    get_git_commit,
    get_pipeline_version,
)

__all__ = ['CodeRevisionProvenance', 'compute_config_hash', 'get_code_revision_provenance', 'get_dependency_lock_hash', 'get_git_commit', 'get_pipeline_version']
