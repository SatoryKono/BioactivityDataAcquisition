"""Stable checkpoint compatibility runtime facade."""

from __future__ import annotations

from bioetl.application.services._checkpoint_compatibility_runtime_core import (
    check_config_compatibility,
    check_phase_compatibility,
    check_schema_compatibility,
    determine_verdict_value,
    generate_message,
    generate_recovery_suggestions,
)
from bioetl.application.services._checkpoint_compatibility_runtime_identity import (
    CheckpointExecutionIdentityFallbackContext,
    ExecutionIdentityCompatibilityContext,
    check_execution_identity_compatibility,
)
from bioetl.application.services._checkpoint_compatibility_runtime_identity_details import (
    IdentityDetailsRequest,
    build_identity_details,
    generate_details,
)

__all__ = [
    "CheckpointExecutionIdentityFallbackContext",
    "ExecutionIdentityCompatibilityContext",
    "IdentityDetailsRequest",
    "build_identity_details",
    "check_config_compatibility",
    "check_execution_identity_compatibility",
    "check_phase_compatibility",
    "check_schema_compatibility",
    "determine_verdict_value",
    "generate_details",
    "generate_message",
    "generate_recovery_suggestions",
]
