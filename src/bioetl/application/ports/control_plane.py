"""Control-plane application ports."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.domain.control_plane import (
        ControlPlaneArtifactLifecycleApplyResult,
        ControlPlaneArtifactLifecyclePlan,
        ControlPlaneArtifactLifecyclePolicy,
    )


class ControlPlaneArtifactLifecycleStoreProtocol(Protocol):
    """Plan/apply artifact lifecycle for a selected run."""

    def plan(
        self,
        policy: ControlPlaneArtifactLifecyclePolicy,
        *,
        dry_run: bool,
    ) -> ControlPlaneArtifactLifecyclePlan: ...

    def apply(
        self,
        plan: ControlPlaneArtifactLifecyclePlan,
    ) -> ControlPlaneArtifactLifecycleApplyResult: ...
