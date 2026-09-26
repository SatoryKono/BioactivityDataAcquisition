"""Thin composition re-export of domain artifact-publication policy (#11226)."""

from __future__ import annotations

from bioetl.domain.control_plane.artifact_publication_policy import (
    requires_artifact_publication_closure,
    validate_artifact_recorder_attachment,
)

__all__ = [
    "requires_artifact_publication_closure",
    "validate_artifact_recorder_attachment",
]
