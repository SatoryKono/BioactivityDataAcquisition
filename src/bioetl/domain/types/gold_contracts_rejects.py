"""Gold reject taxonomy and helper functions."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from enum import StrEnum

from ._gold_contracts_support import (
    GOLD_CONTRACT_VERSION_UNKNOWN,
    coerce_mapping,
    default_rule_id,
    normalize_contract_version,
    normalize_optional_text,
    normalize_text_or_empty,
)

__all__ = [
    "GoldContractValidationError",
    "GoldRejectReason",
    "GoldRejectReasonCode",
    "build_gold_contract_reject_reason",
    "build_gold_semantic_reject_reason",
    "classify_gold_schema_error_reason",
    "normalize_reason_code",
    "resolve_gold_contract_version",
]


class GoldRejectReasonCode(StrEnum):
    """Canonical reject reason codes for Gold-layer failures."""

    CONTRACT_SCHEMA_FAILURE = "gold_contract_schema_failure"
    CONTRACT_REQUIRED_FAILURE = "gold_contract_required_failure"
    CONTRACT_REFERENCE_FAILURE = "gold_contract_reference_failure"
    SEMANTIC_BUSINESS_EXCLUSION = "gold_semantic_business_exclusion"
    SEMANTIC_PROFILE_EXCLUSION = "gold_semantic_profile_exclusion"

    @property
    def is_contract(self) -> bool:
        """Whether the reason code belongs to the contract/schema family."""
        return self.value.startswith("gold_contract_")

    @property
    def is_semantic(self) -> bool:
        """Whether the reason code belongs to the semantic/business family."""
        return self.value.startswith("gold_semantic_")


def normalize_reason_code(value: object) -> GoldRejectReasonCode:
    """Return a canonical Gold reject reason code."""
    if isinstance(value, GoldRejectReasonCode):
        return value
    if isinstance(value, str):
        return GoldRejectReasonCode(value)
    raise ValueError("reason_code must be a GoldRejectReasonCode or canonical string")


def _require_reason_code_family(
    *,
    reason_code: GoldRejectReasonCode,
    expected_family: str,
) -> None:
    is_valid = (
        reason_code.is_semantic
        if expected_family == "semantic"
        else reason_code.is_contract
    )
    if is_valid:
        return
    raise ValueError(
        f"gold_{expected_family} reject reason helper requires a {expected_family} code, got {reason_code.value}"
    )


@dataclass(frozen=True, slots=True)
class GoldRejectReason:
    """Structured reject payload used across Gold validation and DQ surfaces."""

    reason_code: GoldRejectReasonCode
    contract_version: str = GOLD_CONTRACT_VERSION_UNKNOWN
    rule_id: str = ""
    message: str = ""
    details: Mapping[str, object] = dataclass_field(default_factory=dict)
    field: str | None = None
    layer: str = "gold"
    config_path: str | None = None

    def __post_init__(self) -> None:
        object.__setattr__(self, "reason_code", normalize_reason_code(self.reason_code))
        object.__setattr__(
            self,
            "contract_version",
            normalize_contract_version(self.contract_version),
        )
        object.__setattr__(self, "rule_id", normalize_text_or_empty(self.rule_id))
        object.__setattr__(self, "message", normalize_text_or_empty(self.message))
        object.__setattr__(self, "field", normalize_optional_text(self.field))
        object.__setattr__(self, "layer", normalize_optional_text(self.layer) or "gold")
        object.__setattr__(
            self, "config_path", normalize_optional_text(self.config_path)
        )
        object.__setattr__(self, "details", coerce_mapping(self.details))


class GoldContractValidationError(ValueError):
    """Raised when Gold schema or contract validation fails."""

    def __init__(
        self,
        reject_reason: GoldRejectReason,
        *,
        original: Exception | None = None,
    ) -> None:
        self.reject_reason = reject_reason
        self.original = original
        super().__init__(reject_reason.message or reject_reason.reason_code.value)


def build_gold_contract_reject_reason(
    *,
    reason_code: GoldRejectReasonCode | str,
    contract_version: str | None = GOLD_CONTRACT_VERSION_UNKNOWN,
    rule_id: str | None = None,
    field: str | None = None,
    message: str = "",
    details: Mapping[str, object] | None = None,
    config_path: str | None = None,
) -> GoldRejectReason:
    """Build one contract-originated Gold reject payload."""
    normalized_reason_code = normalize_reason_code(reason_code)
    _require_reason_code_family(
        reason_code=normalized_reason_code,
        expected_family="contract",
    )
    return GoldRejectReason(
        reason_code=normalized_reason_code,
        contract_version=contract_version or GOLD_CONTRACT_VERSION_UNKNOWN,
        rule_id=rule_id or default_rule_id("gold.contract", field),
        message=message,
        details=details or {},
        field=field,
        config_path=config_path,
    )


def _infer_semantic_reason_code(semantic_scope: str | None) -> GoldRejectReasonCode:
    """Infer semantic reason code from scope."""
    return (
        GoldRejectReasonCode.SEMANTIC_PROFILE_EXCLUSION
        if normalize_optional_text(semantic_scope) == "profile"
        else GoldRejectReasonCode.SEMANTIC_BUSINESS_EXCLUSION
    )


def build_gold_semantic_reject_reason(
    *,
    reason_code: GoldRejectReasonCode | str | None = None,
    rule_id: str | None = None,
    field: str | None = None,
    message: str = "",
    details: Mapping[str, object] | None = None,
    contract_version: str | None = GOLD_CONTRACT_VERSION_UNKNOWN,
    semantic_scope: str | None = None,
    config_path: str | None = None,
) -> GoldRejectReason:
    """Build one semantic/business-rule Gold reject payload."""
    normalized_reason_code = (
        normalize_reason_code(reason_code)
        if reason_code is not None
        else _infer_semantic_reason_code(semantic_scope)
    )
    _require_reason_code_family(
        reason_code=normalized_reason_code,
        expected_family="semantic",
    )
    return GoldRejectReason(
        reason_code=normalized_reason_code,
        contract_version=contract_version or GOLD_CONTRACT_VERSION_UNKNOWN,
        rule_id=rule_id or default_rule_id("gold.semantic", field),
        message=message,
        details=details or {},
        field=field,
        config_path=config_path,
    )


def _is_required_field_error(error_text: str) -> bool:
    """Check if error indicates a required field violation."""
    return any(
        pattern in error_text
        for pattern in (
            "required",
            "missing",
            "not in dataframe",
            "nullable",
            "non-nullable",
        )
    )


def _is_reference_error(error_text: str) -> bool:
    """Check if error indicates a reference/foreign key violation."""
    return any(
        pattern in error_text for pattern in ("reference", "foreign key", "orphan")
    )


def classify_gold_schema_error_reason(exc: Exception) -> GoldRejectReasonCode:
    """Map schema failures to a contract reason code using a stable heuristic."""
    error_text = str(exc).lower()
    if _is_required_field_error(error_text):
        return GoldRejectReasonCode.CONTRACT_REQUIRED_FAILURE
    if _is_reference_error(error_text):
        return GoldRejectReasonCode.CONTRACT_REFERENCE_FAILURE
    return GoldRejectReasonCode.CONTRACT_SCHEMA_FAILURE


def _extract_version_from_attribute(schema: object, attr_name: str) -> str | None:
    """Extract version from a direct schema attribute."""
    return normalize_optional_text(getattr(schema, attr_name, None))


def _extract_version_from_standard_attributes(schema: object) -> str | None:
    for attr_name in ("active_version", "version"):
        version = _extract_version_from_attribute(schema, attr_name)
        if version is not None:
            return version
    return None


def _extract_version_from_metadata(schema: object) -> str | None:
    """Extract version from schema metadata mapping."""
    metadata = getattr(schema, "metadata", None)
    if not isinstance(metadata, Mapping):
        return None
    return normalize_optional_text(
        metadata.get("contract_version") or metadata.get("version")
    )


def _extract_version_from_config(schema: object) -> str | None:
    """Extract version from schema Config class."""
    config = getattr(schema, "Config", None)
    return normalize_optional_text(getattr(config, "contract_version", None))


def _invoke_to_schema(schema: object) -> object | None:
    to_schema = getattr(schema, "to_schema", None)
    if not callable(to_schema):
        return None
    try:
        return to_schema()
    except (AttributeError, RuntimeError, TypeError, ValueError):
        return None


def _known_contract_version_or_none(version: str) -> str | None:
    if version == GOLD_CONTRACT_VERSION_UNKNOWN:
        return None
    return version


def _extract_version_from_to_schema(schema: object) -> str | None:
    """Extract version by calling to_schema() if available."""
    resolved_schema = _invoke_to_schema(schema)
    if resolved_schema is None or resolved_schema is schema:
        return None
    return _known_contract_version_or_none(
        resolve_gold_contract_version(resolved_schema)
    )


def _resolve_version_from_schema(schema: object | None) -> str | None:
    if schema is None:
        return None
    version = _extract_version_from_standard_attributes(schema)
    if version is not None:
        return version
    for extractor in (
        _extract_version_from_metadata,
        _extract_version_from_config,
        _extract_version_from_to_schema,
    ):
        version = extractor(schema)
        if version is not None:
            return version
    return None


def resolve_gold_contract_version(
    schema: object | None,
    *,
    explicit_contract_version: str | None = None,
) -> str:
    """Resolve one contract version from explicit input or schema metadata."""
    explicit = normalize_optional_text(explicit_contract_version)
    if explicit is not None:
        return explicit
    return _resolve_version_from_schema(schema) or GOLD_CONTRACT_VERSION_UNKNOWN
