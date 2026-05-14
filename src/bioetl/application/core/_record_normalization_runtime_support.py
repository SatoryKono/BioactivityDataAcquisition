"""Runtime helpers for record normalization findings and profile contract gaps."""

from __future__ import annotations

from typing import TYPE_CHECKING

from bioetl.domain.normalization.json import canonicalize_json_string
from bioetl.domain.normalization.text import normalize_string

if TYPE_CHECKING:
    from bioetl.application.core.record_normalization_processor import (
        _NormalizationFinding,
    )
    from bioetl.domain.context import PipelineContext
    from bioetl.domain.normalization.profiles import FieldRule
    from bioetl.domain.types import JsonDict

_MALFORMED_JSON_EVENT = "silver_normalization_malformed_json"
_MALFORMED_JSON_REASON_CODE = "malformed_json_normalized_to_null"


def project_normalization_findings(
    findings: tuple[_NormalizationFinding, ...],
    record: JsonDict,
    *,
    context: PipelineContext | None,
    index: int | None,
    provider: str,
    entity_type: str | None,
) -> JsonDict:
    """Project transient normalization findings into DQ flags and logs."""
    if not findings:
        return record

    projected = dict(record)
    projected["_dq_warn"] = True

    if context is None:
        return projected

    for finding in findings:
        context.logger.warning(
            _MALFORMED_JSON_EVENT,
            provider=provider,
            entity_type=entity_type,
            record_index=index,
            reason_code=finding.reason_code,
            field=finding.field_name,
            action_taken=finding.action_taken,
            dq_warn=finding.dq_warn,
            proposed_normalized_outcome=None,
        )
    return projected


def profile_json_runtime_finding(
    rule: FieldRule,
    *,
    field_name: str,
    raw_value: object,
    normalized_value: object,
    finding_factory: type[_NormalizationFinding],
) -> _NormalizationFinding | None:
    """Return one runtime finding when JSON normalization collapses invalid input."""
    if normalized_value is not None or not isinstance(raw_value, str):
        return None

    normalized_text = normalize_string(raw_value)
    if normalized_text is None or not _rule_uses_json_policy(rule):
        return None

    try:
        canonicalize_json_string(normalized_text)
    except ValueError:
        return finding_factory(
            field_name=field_name,
            reason_code=_MALFORMED_JSON_REASON_CODE,
            action_taken="set_null_and_warn",
        )
    return None


def should_forbid_fallback(
    *,
    has_profile: bool,
    allow_compatibility_fallback: bool,
    field_name: str,
    passthrough_fields: frozenset[str],
) -> bool:
    """Return whether fallback normalization must fail closed for one field."""
    return (
        has_profile
        and not allow_compatibility_fallback
        and not field_name.startswith("_")
        and field_name not in passthrough_fields
    )


def raise_profile_gap(provider: str, entity_type: str | None, field_name: str) -> None:
    """Raise the canonical profile-gap error for implicit fallback attempts."""
    from bioetl.application.core.record_normalization_processor import (
        NormalizationContractError,
    )

    entity_label = entity_type or "<unknown>"
    raise NormalizationContractError(
        "profile-backed normalization cannot fall back implicitly for "
        f"{provider}.{entity_label} field {field_name!r}; "
        "add an explicit normalization profile rule or enable "
        "allow_compatibility_fallback for bounded compatibility paths"
    )


def _rule_uses_json_policy(rule: FieldRule) -> bool:
    notes = (rule.notes or "").casefold()
    normalizer_name = getattr(rule.normalizer, "__name__", "").casefold()
    return "json" in notes or "json" in normalizer_name
