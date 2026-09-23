"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from collections.abc import Callable

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import JsonValue

__all__ = [
    "_accumulate_field_matrix_evidence",
    "_empty_normalization_evidence_payload",
    "_enrich_registry_normalization_evidence",
    "_finalize_normalization_evidence_defaults",
]


def _empty_normalization_evidence_payload() -> dict[str, JsonValue]:
    return {
        "profile_field_count": 0,
        "fallback_field_count": 0,
        "fallback_business_field_count": 0,
        "fallback_technical_passthrough_field_count": 0,
    }


def _accumulate_field_matrix_evidence(
    evidence: dict[str, dict[str, JsonValue]],
    rows: list[dict[str, object]],
    *,
    fallback_business: str,
    fallback_technical_passthrough: str,
) -> None:
    for row in rows:
        pipeline_name = str(row.get("pipeline_name", "")).strip()
        pipeline_kind = str(row.get("pipeline_kind", "")).strip()
        if not pipeline_name or pipeline_kind != "entity":
            continue
        payload = evidence.setdefault(
            pipeline_name, _empty_normalization_evidence_payload()
        )
        source = str(row.get("normalization_source", "")).strip()
        if source == "profile":
            payload["profile_field_count"] = (
                _coerce_int(payload["profile_field_count"]) + 1
            )
            continue
        payload["fallback_field_count"] = (
            _coerce_int(payload["fallback_field_count"]) + 1
        )
        if source == fallback_business:
            payload["fallback_business_field_count"] = (
                _coerce_int(payload["fallback_business_field_count"]) + 1
            )
        elif source == fallback_technical_passthrough:
            payload["fallback_technical_passthrough_field_count"] = (
                _coerce_int(payload["fallback_technical_passthrough_field_count"]) + 1
            )


def _enrich_registry_normalization_evidence(
    evidence: dict[str, dict[str, JsonValue]],
    registry: list[tuple[str, str]],
    resolve_module_path: Callable[[str, str], str | None],
) -> None:
    for provider, entity in registry:
        pipeline_name = f"{provider}_{entity}"
        payload = evidence.setdefault(
            pipeline_name, _empty_normalization_evidence_payload()
        )
        payload["normalization_profile_registered"] = True
        module_path = resolve_module_path(provider, entity)
        if module_path is not None:
            payload["normalization_profile_module_path"] = module_path


def _finalize_normalization_evidence_defaults(
    evidence: dict[str, dict[str, JsonValue]],
) -> None:
    for payload in evidence.values():
        payload.setdefault("normalization_profile_registered", False)
