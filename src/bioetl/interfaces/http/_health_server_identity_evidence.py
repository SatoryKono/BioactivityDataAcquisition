"""Compatibility wrapper for Control Plane identity evidence payload helpers."""

from bioetl.interfaces.http.control_plane_identity import (
    IDENTITY_EVIDENCE_CONTRACT,
    build_control_plane_identity_evidence_payload,
)

__all__ = [
    "IDENTITY_EVIDENCE_CONTRACT",
    "build_control_plane_identity_evidence_payload",
]
