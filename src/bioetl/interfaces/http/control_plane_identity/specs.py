"""Control Plane identity anchor specification facade."""

from __future__ import annotations

from bioetl.interfaces.http.control_plane_identity.p0_specs import P0_ANCHOR_SPECS
from bioetl.interfaces.http.control_plane_identity.p1_specs import P1_ANCHOR_SPECS
from bioetl.interfaces.http.control_plane_identity.p2_specs import P2_ANCHOR_SPECS
from bioetl.interfaces.http.control_plane_identity.spec_constants import (
    ALLOWED_LOW_CARDINALITY_LABELS,
    ANCHOR_SPEC_VERSION,
    CHECKPOINT_ANCHORS,
    SPEC_VALIDATION_RULES,
    TERMINAL_STATUSES,
)
from bioetl.interfaces.http.control_plane_identity.types import AnchorSpec


def _anchor_specs_by_unique_name(
    specs: tuple[AnchorSpec, ...],
) -> dict[str, AnchorSpec]:
    """Fail closed when two specs share a name instead of silently overwriting."""
    by_name: dict[str, AnchorSpec] = {}
    for spec in specs:
        if spec.name in by_name:
            raise ValueError(f"duplicate AnchorSpec name: {spec.name}")
        by_name[spec.name] = spec
    return by_name


ANCHOR_SPECS: tuple[AnchorSpec, ...] = (
    *P0_ANCHOR_SPECS,
    *P1_ANCHOR_SPECS,
    *P2_ANCHOR_SPECS,
)
SPEC_BY_NAME = _anchor_specs_by_unique_name(ANCHOR_SPECS)
OVERVIEW_NAMES = frozenset(
    {
        "run_id",
        "manifest_id",
        "pipeline_name",
        "provider_entity",
        "runtime_mode",
        "execution_fingerprint",
        "effective_config_hash",
        "contract_ref",
        "contract_version",
        "input_snapshot_identity_fingerprint",
        "replay_capability",
        "replay_mode",
        "checkpoint_anchor_status",
        "composite_run_identity",
        "identity_graph_complete",
    }
)


def get_current_spec_version() -> str:
    """Return the current HTTP control-plane identity spec version."""
    return ANCHOR_SPEC_VERSION


def is_spec_version_compatible(version: str) -> bool:
    """Return whether a spec version is compatible with the current major line."""
    current_major = ANCHOR_SPEC_VERSION.split(".", maxsplit=1)[0]
    candidate_major = str(version).split(".", maxsplit=1)[0]
    return candidate_major == current_major


__all__ = [
    "ALLOWED_LOW_CARDINALITY_LABELS",
    "ANCHOR_SPECS",
    "ANCHOR_SPEC_VERSION",
    "CHECKPOINT_ANCHORS",
    "OVERVIEW_NAMES",
    "SPEC_BY_NAME",
    "SPEC_VALIDATION_RULES",
    "TERMINAL_STATUSES",
    "get_current_spec_version",
    "is_spec_version_compatible",
]
