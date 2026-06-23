"""Validation severity levels for composite pipeline execution."""

from __future__ import annotations

from enum import Enum


class ValidationSeverity(Enum):
    """Severity levels for validation issues."""

    BLOCKER = "blocker"
    WARNING = "warning"
    INFO = "info"


class ValidationLayer(Enum):
    """Validation layers with distinct responsibilities."""

    STRUCTURAL = "structural"
    DEEP_PREFLIGHT = "deep_preflight"
    RUNTIME_GUARD = "runtime_guard"


class IssueCode(Enum):
    """Stable taxonomy of issue codes for composite validation."""

    # Structural validation issues
    CMP_STR_SCHEMA_001 = "CMP-STR-SCHEMA-001"  # Invalid schema format
    CMP_STR_CONFIG_002 = "CMP-STR-CONFIG-002"  # Missing required config field
    CMP_STR_FORMAT_003 = "CMP-STR-FORMAT-003"  # Invalid config file format

    # Deep preflight issues
    CMP_PF_AGG_001 = "CMP-PF-AGG-001"  # Missing group_by fields
    CMP_PF_AGG_002 = "CMP-PF-AGG-002"  # Group_by field not found in schema
    CMP_PF_AGG_003 = "CMP-PF-AGG-003"  # Missing aggregations
    CMP_PF_AGG_004 = "CMP-PF-AGG-004"  # Unsupported aggregation function
    CMP_PF_AGG_005 = "CMP-PF-AGG-005"  # Source field not found in schema
    CMP_PF_AGG_006 = "CMP-PF-AGG-006"  # Field shadowing warning
    CMP_PF_CV_002 = "CMP-PF-CV-002"  # Cross-validation pairs cannot be empty
    CMP_PF_CV_003 = "CMP-PF-CV-003"  # Cross-validation pair must be a dictionary
    CMP_PF_CV_004 = (
        "CMP-PF-CV-004"  # Cross-validation pair must have exactly one source mapping
    )
    CMP_PF_CV_005 = (
        "CMP-PF-CV-005"  # Cross-validation source not found in pipeline sources
    )
    CMP_PF_CV_006 = "CMP-PF-CV-006"  # Comparison sources must be string or list
    CMP_PF_CV_007 = "CMP-PF-CV-007"  # Comparison source not found in pipeline sources
    CMP_PF_CV_008 = "CMP-PF-CV-008"  # Cross-validation rules cannot be empty
    CMP_PF_CV_009 = "CMP-PF-CV-009"  # Rule must be a string type
    CMP_PF_CV_010 = "CMP-PF-CV-010"  # Unsupported cross-validation rule type
    CMP_PF_CV_011 = "CMP-PF-CV-011"  # Coverage threshold must be between 0.0 and 1.0
    CMP_PF_CV_012 = "CMP-PF-CV-012"  # Consistency threshold must be between 0.0 and 1.0
    CMP_PF_CV_013 = "CMP-PF-CV-013"  # Cross-validation does not cover all sources
    CMP_PF_LIN_001 = "CMP-PF-LIN-001"  # Insufficient lineage tracking
    CMP_PF_LIN_002 = "CMP-PF-LIN-002"  # Missing lineage policy
    CMP_PF_FIELD_001 = "CMP-PF-FIELD-001"  # Conflicting field priorities
    CMP_PF_DEP_001 = "CMP-PF-DEP-001"  # Missing required dependency
    CMP_PF_ENR_001 = "CMP-PF-ENR-001"  # Invalid enricher configuration

    # Runtime guard issues
    CMP_RT_CARD_001 = "CMP-RT-CARD-001"  # Cardinality violation
    CMP_RT_GRAIN_001 = "CMP-RT-GRAIN-001"  # Post-aggregation grain mismatch
    CMP_RT_RESUME_001 = "CMP-RT-RESUME-001"  # Incompatible resume attempt
    CMP_RT_PHASE_001 = "CMP-RT-PHASE-001"  # Invalid phase transition
    CMP_RT_SHADOW_001 = "CMP-RT-SHADOW-001"  # Field shadowing detected

    def is_blocker(self) -> bool:
        """Return True if this issue code represents a blocker."""
        return self.value.startswith("CMP-STR-") or self in {
            IssueCode.CMP_PF_AGG_001,
            IssueCode.CMP_PF_AGG_002,
            IssueCode.CMP_PF_AGG_003,
            IssueCode.CMP_PF_AGG_004,
            IssueCode.CMP_PF_AGG_005,
            IssueCode.CMP_PF_CV_002,
            IssueCode.CMP_PF_CV_003,
            IssueCode.CMP_PF_CV_004,
            IssueCode.CMP_PF_CV_005,
            IssueCode.CMP_PF_CV_006,
            IssueCode.CMP_PF_CV_007,
            IssueCode.CMP_PF_CV_008,
            IssueCode.CMP_PF_CV_009,
            IssueCode.CMP_PF_CV_010,
            IssueCode.CMP_PF_CV_011,
            IssueCode.CMP_PF_CV_012,
            IssueCode.CMP_PF_LIN_001,
            IssueCode.CMP_RT_CARD_001,
            IssueCode.CMP_RT_GRAIN_001,
            IssueCode.CMP_RT_RESUME_001,
            IssueCode.CMP_RT_PHASE_001,
        }
