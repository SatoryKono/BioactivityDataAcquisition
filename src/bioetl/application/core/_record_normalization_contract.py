"""Shared record-normalization runtime contracts."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from bioetl.application.core._record_normalization_hash_support import (
        _NormalizationProfileLike,
    )
    from bioetl.application.core.normalization_rules import NormalizationRulesPolicy
    from bioetl.domain.normalization.profiles import FieldRule
    from bioetl.domain.types import JsonDict

__all__ = [
    "NormalizationContractError",
    "_NormalizationFinding",
    "_RecordNormalizationMappingHost",
]


@dataclass(frozen=True, slots=True)
class _NormalizationFinding:
    field_name: str
    reason_code: str
    action_taken: str
    dq_warn: bool = True


class NormalizationContractError(ValueError):
    """Raised when profile-backed runtime normalization would fall back implicitly."""


class _RecordNormalizationMappingHost(Protocol):
    """Structural host contract for ``RecordNormalizationMappingMixin`` (#10596).

    Attributes are read-only properties so frozen dataclass hosts such as
    ``RecordNormalizationProcessor`` satisfy the Protocol structurally instead
    of relying on ``cast(Any, None)`` class-level defaults.
    """

    @property
    def provider(self) -> str: ...

    @property
    def entity_type(self) -> str | None: ...

    @property
    def profile(self) -> _NormalizationProfileLike | None: ...

    @property
    def rule_set(self) -> NormalizationRulesPolicy: ...

    @property
    def allow_compatibility_fallback(self) -> bool: ...

    def _is_passthrough_field(self, field_name: str) -> bool: ...

    def _normalize_field_value(
        self,
        field_name: str,
        value: object,
        record: JsonDict,
    ) -> object: ...

    def _normalize_special_field(self, field_name: str, value: object) -> object: ...

    def _normalize_string_field(self, field_name: str, value: str) -> str | None: ...

    def _profile_rule(self, field_name: str) -> FieldRule | None: ...

    def _normalize_profile_field_value(
        self,
        rule: FieldRule,
        value: object,
        record: JsonDict,
    ) -> object: ...

    def _reapply_record_aware_profile_rules(self, record: JsonDict) -> JsonDict: ...

    def _normalize_named_text_field(
        self,
        field_name: str,
        value: str,
    ) -> str | None: ...

    def _canonicalize_json_like_string(self, value: str) -> str: ...
