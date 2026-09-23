"""Helpers extracted from the graph sync kernel (AUD-002)."""

from __future__ import annotations

from memory.graph.sync_pkg._core_convert import _coerce_int
from memory.graph.sync_pkg._core_models import JsonValue

__all__ = [
    "_NORMALIZATION_EVIDENCE_STATEMENT",
    "_normalization_statement_params",
]

_NORMALIZATION_EVIDENCE_STATEMENT = """
MATCH (p:pipeline_surface {name: $pipeline_name})
SET p.normalization_profile_registered = $normalization_profile_registered,
    p.normalization_profile_module_path = $normalization_profile_module_path,
    p.profile_field_count = $profile_field_count,
    p.fallback_field_count = $fallback_field_count,
    p.fallback_business_field_count = $fallback_business_field_count,
    p.fallback_technical_passthrough_field_count = $fallback_technical_passthrough_field_count
WITH p
OPTIONAL MATCH (p)-[rp:DEPENDS_ON {provenance: 'normalization_registry'}]->(:module_surface)
DELETE rp
WITH p
OPTIONAL MATCH (e:entity_config {name: $pipeline_name})
SET e.normalization_profile_registered = $normalization_profile_registered,
    e.normalization_profile_module_path = $normalization_profile_module_path,
    e.profile_field_count = $profile_field_count,
    e.fallback_field_count = $fallback_field_count,
    e.fallback_business_field_count = $fallback_business_field_count,
    e.fallback_technical_passthrough_field_count = $fallback_technical_passthrough_field_count
WITH p, e
OPTIONAL MATCH (e)-[re:DEPENDS_ON {provenance: 'normalization_registry'}]->(:module_surface)
DELETE re
WITH p, e
OPTIONAL MATCH (m:module_surface {name: $module_path})
FOREACH (_ IN CASE WHEN m IS NULL THEN [] ELSE [1] END |
    MERGE (p)-[:DEPENDS_ON {provenance: 'normalization_registry'}]->(m)
)
FOREACH (_ IN CASE WHEN e IS NULL OR m IS NULL THEN [] ELSE [1] END |
    MERGE (e)-[:DEPENDS_ON {provenance: 'normalization_registry'}]->(m)
)
RETURN $pipeline_name AS pipeline_name
""".strip()


def _normalization_statement_params(
    pipeline_name: str,
    evidence: dict[str, JsonValue],
) -> dict[str, JsonValue]:
    module_path = evidence.get("normalization_profile_module_path")
    normalized_module_path = (
        str(module_path) if isinstance(module_path, str) and module_path else None
    )
    return {
        "pipeline_name": pipeline_name,
        "normalization_profile_registered": bool(
            evidence.get("normalization_profile_registered", False)
        ),
        "normalization_profile_module_path": normalized_module_path,
        "profile_field_count": _coerce_int(evidence.get("profile_field_count", 0), 0),
        "fallback_field_count": _coerce_int(evidence.get("fallback_field_count", 0), 0),
        "fallback_business_field_count": _coerce_int(
            evidence.get("fallback_business_field_count", 0), 0
        ),
        "fallback_technical_passthrough_field_count": _coerce_int(
            evidence.get("fallback_technical_passthrough_field_count", 0), 0
        ),
        "module_path": normalized_module_path,
    }
