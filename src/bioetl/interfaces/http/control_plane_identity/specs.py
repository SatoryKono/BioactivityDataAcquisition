"""Control Plane identity anchor specification facade."""

from __future__ import annotations

from bioetl.interfaces.http.control_plane_identity.p0_specs import P0_ANCHOR_SPECS
from bioetl.interfaces.http.control_plane_identity.p1_specs import P1_ANCHOR_SPECS
from bioetl.interfaces.http.control_plane_identity.p2_specs import P2_ANCHOR_SPECS
from bioetl.interfaces.http.control_plane_identity.spec_constants import (
    ALLOWED_LOW_CARDINALITY_LABELS,
    CHECKPOINT_ANCHORS,
    TERMINAL_STATUSES,
)
from bioetl.interfaces.http.control_plane_identity.types import AnchorSpec

ANCHOR_SPECS: tuple[AnchorSpec, ...] = (
    *P0_ANCHOR_SPECS,
    *P1_ANCHOR_SPECS,
    *P2_ANCHOR_SPECS,
)
SPEC_BY_NAME = {spec.name: spec for spec in ANCHOR_SPECS}
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

__all__ = [
    "ALLOWED_LOW_CARDINALITY_LABELS",
    "ANCHOR_SPECS",
    "CHECKPOINT_ANCHORS",
    "OVERVIEW_NAMES",
    "SPEC_BY_NAME",
    "TERMINAL_STATUSES",
]
