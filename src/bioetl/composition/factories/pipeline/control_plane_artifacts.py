"""Shared immutable control-plane artifact constructors for pipeline creation.

The compatibility builder is the canonical dataclass constructor; this keeps
its defaults and newly supported identity fields aligned with the port.
"""

from __future__ import annotations

from bioetl.domain.ports import (
    PipelineControlPlaneArtifacts as ControlPlaneArtifacts,
    PipelineControlPlaneArtifacts as build_control_plane_artifacts,
)

__all__ = ["ControlPlaneArtifacts", "build_control_plane_artifacts"]
