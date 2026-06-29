"""Shared control-plane identity ref helpers for manifest builders."""

from __future__ import annotations

__all__ = ["build_control_plane_identity_ref_values"]


def build_control_plane_identity_ref_values(
    *,
    contract_identity_values: dict[str, str | None],
    required_persistence_profile: str | None,
) -> dict[str, str | None]:
    """Return reusable control-plane identity kwargs shared by ref builders."""
    return {
        **contract_identity_values,
        "required_persistence_profile": required_persistence_profile,
    }
