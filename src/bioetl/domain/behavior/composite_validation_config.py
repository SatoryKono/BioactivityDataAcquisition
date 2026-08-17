"""Input value object for composite validation."""

from __future__ import annotations

from dataclasses import dataclass

from bioetl.domain.behavior.preflight_governance import GovernancePolicy
from bioetl.domain.types import JsonDict


@dataclass(frozen=True)
class CompositeValidationConfig:
    """Inputs and governance knobs for composite validation."""

    pipeline_name: str
    composite_config: JsonDict
    execution_context: JsonDict | None = None
    strict_mode: bool = True
    governance_policy: GovernancePolicy = GovernancePolicy.BLOCK_ON_BLOCKERS_ONLY
