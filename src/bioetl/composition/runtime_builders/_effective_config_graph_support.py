"""Composition facade. Implementation lives in `bioetl.infrastructure.config.effective_config_graph` (#11241)."""

from __future__ import annotations

from bioetl.infrastructure.config.effective_config_graph import (
    _DEPENDENCY_PROVENANCE_FILES,
    build_effective_config_candidate_paths,
)

__all__ = ["_DEPENDENCY_PROVENANCE_FILES", "build_effective_config_candidate_paths"]
