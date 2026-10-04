"""Extracted _build_operator_replay_projection for the hotspot coverage floor (#11016)."""

from __future__ import annotations

from collections.abc import Callable
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from bioetl.application.services.control_plane.manifest.diagnostics.replay_projection_payload import (
        _ReplayProjectionContextKwargs,
    )


def _build_operator_replay_projection(
    *,
    context_kwargs: _ReplayProjectionContextKwargs,
    replay_family_contract: dict[str, object],
    replay_family_contract_payload: dict[str, object],
    build_inputs: Callable[..., dict[str, object]],
    build_payload: Callable[..., dict[str, object]],
    build_taxonomy: Callable[..., dict[str, object]],
) -> dict[str, object]:
    """Return canonical operator-facing replay projection fields."""
    replay_inputs = build_inputs(**context_kwargs)
    payload = build_payload(
        **context_kwargs,
        replay_family_contract=replay_family_contract,
        replay_family_contract_payload=replay_family_contract_payload,
        replay_inputs=replay_inputs,
    )
    projection = build_taxonomy(**payload)
    parentage = payload["replay_parentage"]
    projection["replay_parentage"] = (
        dict(parentage) if isinstance(parentage, dict) else parentage
    )
    return projection
