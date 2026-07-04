"""Shared data types for composite preflight validation."""

from __future__ import annotations

from dataclasses import dataclass, field

__all__ = [
    "FieldInfo",
    "PreflightValidationError",
    "PreflightValidationResult",
    "ProfileInfo",
    "SchemaFields",
    "ValidationIssue",
]


@dataclass(frozen=True, slots=True)
class FieldInfo:
    """Information about a field from a source schema."""

    name: str
    dtype: str
    nullable: bool
    source: str


@dataclass(frozen=True, slots=True)
class ProfileInfo:
    """Deterministic normalization-profile metadata for one source."""

    source: str
    profile_name: str
    profile_version: str
    profile_hash: str
    field_hashes: dict[str, str]


@dataclass(frozen=True, slots=True)
class ValidationIssue:
    """A single validation issue found during preflight check."""

    field: str
    source: str
    issue_type: str
    message: str
    severity: str = "error"


@dataclass
class PreflightValidationResult:
    """Result of preflight validation."""

    is_valid: bool
    issues: list[ValidationIssue] = field(default_factory=list)
    resolved_fields: dict[str, str] = field(default_factory=dict)
    profile_refs: dict[str, ProfileInfo] = field(default_factory=dict)

    @property
    def errors(self) -> list[ValidationIssue]:
        """Get only error-level issues."""
        return [issue for issue in self.issues if issue.severity == "error"]

    @property
    def warnings(self) -> list[ValidationIssue]:
        """Get only warning-level issues."""
        return [issue for issue in self.issues if issue.severity == "warning"]


class PreflightValidationError(Exception):
    """Raised when preflight validation fails with blocking errors."""

    def __init__(self, result: PreflightValidationResult) -> None:
        self.result = result
        error_msgs = [f"  - {error.field}: {error.message}" for error in result.errors]
        super().__init__(
            "Composite pipeline preflight validation failed with "
            f"{len(result.errors)} error(s):\n" + "\n".join(error_msgs)
        )


SchemaFields = dict[str, FieldInfo]
