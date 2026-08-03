# Host attrs/methods provided by concrete composition.
"""Runtime helpers for optional lineage-fragment materialization."""

from __future__ import annotations

import asyncio
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from typing import TYPE_CHECKING, Any, TypeVar, cast

from bioetl.domain.behavior.composite_metadata_helpers import (
    parse_composite_field_sources,
    parse_composite_list,
)
from bioetl.domain.control_plane.reproducibility_policy import (
    STRICT_PERSISTENCE_PROFILES,
)
from bioetl.domain.ports import LineageStorePort

if TYPE_CHECKING:
    from bioetl.domain.lineage import LineageGraphFragment
    from bioetl.domain.ports import MetricsPort

__all__ = [
    "emit_composite_source_selection_metrics",
    "emit_lineage_refs_missing_metric",
    "lineage_fragment_publication_required",
    "persist_lineage_fragment_if_present",
    "resolve_metadata_and_lineage_fragment",
]

MetadataT = TypeVar("MetadataT")


def _emit_lineage_fragment_metric(
    metrics: MetricsPort | None,
    *,
    pipeline_name: str | None,
    layer: str | None,
    status: str,
) -> None:
    """Emit one lineage fragment persistence metric when metrics are enabled."""
    if metrics is None:
        return
    metrics.increment_counter(
        "bioetl_lineage_fragments_emitted_total",
        1,
        {
            "pipeline": pipeline_name or "unknown",
            "layer": layer or "unknown",
            "status": status,
        },
    )


def lineage_fragment_publication_required(coordinator: object | None) -> bool:
    """Return whether the coordinator run context requires lineage persistence."""
    run_context = getattr(coordinator, "run_context", None)
    exact_replay = getattr(run_context, "exact_replay", False) is True
    raw_profile = getattr(run_context, "required_persistence_profile", "")
    profile = raw_profile.strip().lower() if isinstance(raw_profile, str) else ""
    return exact_replay or profile in STRICT_PERSISTENCE_PROFILES


def emit_lineage_refs_missing_metric(
    metrics: MetricsPort | None,
    *,
    pipeline_name: str | None,
    layer: str,
    ref_type: str,
    missing_count: int = 1,
) -> None:
    """Emit one missing-upstream-reference metric when refs are absent."""
    if metrics is None or missing_count <= 0:
        return
    metrics.increment_counter(
        "bioetl_lineage_refs_missing_total",
        missing_count,
        {
            "pipeline": pipeline_name or "unknown",
            "layer": layer,
            "ref_type": ref_type,
        },
    )


def _collect_composite_sources(
    *,
    sources_used: Sequence[str] | None,
    records: Sequence[Mapping[str, object]] | None,
) -> tuple[str, ...]:
    """Collect unique composite sources from explicit and record-level metadata."""
    sources: set[str] = {str(source) for source in sources_used or () if source}
    if records is not None:
        for record in records:
            sources.update(
                source
                for source in parse_composite_list(record.get("_source_providers"))
                if source
            )
    return tuple(sorted(sources))


def _collect_field_source_counts(
    records: Sequence[Mapping[str, object]] | None,
) -> Mapping[str, int]:
    """Count unique field->provider selections across composite records."""
    if records is None:
        return {}
    provider_fields: set[tuple[str, str]] = set()
    for record in records:
        for field_name, provider in parse_composite_field_sources(
            record.get("_field_sources")
        ).items():
            if provider and field_name:
                provider_fields.add((provider, field_name))
    counts: Counter[str] = Counter()
    for provider, _field_name in sorted(provider_fields):
        counts[provider] += 1
    return {provider: counts[provider] for provider in sorted(counts)}


def emit_composite_source_selection_metrics(
    metrics: MetricsPort | None,
    *,
    pipeline_name: str | None,
    layer: str,
    sources_used: Sequence[str] | None = None,
    records: Sequence[Mapping[str, object]] | None = None,
) -> None:
    """Emit low-cardinality aggregate metrics for composite source decisions."""
    if metrics is None:
        return

    for source in _collect_composite_sources(
        sources_used=sources_used,
        records=records,
    ):
        metrics.increment_counter(
            "bioetl_composite_source_selection_total",
            1,
            {
                "pipeline": pipeline_name or "unknown",
                "decision_type": f"{layer}_source_included",
                "selected_source": source,
            },
        )

    for source, field_count in _collect_field_source_counts(records).items():
        metrics.increment_counter(
            "bioetl_composite_source_selection_total",
            field_count,
            {
                "pipeline": pipeline_name or "unknown",
                "decision_type": f"{layer}_field_selected",
                "selected_source": source,
            },
        )


def _has_explicit_member(target: object, member_name: str) -> bool:
    """Return whether a method/property is explicitly present on instance or class."""
    return (
        member_name in vars(target)
        or getattr(type(target), member_name, None) is not None
    )


def resolve_metadata_and_lineage_fragment[MetadataT](
    *,
    coordinator: object | None,
    bundle_factory_name: str,
    coordinator_factory_name: str | None,
    input_data: object,
    fallback_factory: Callable[[], MetadataT],
) -> tuple[MetadataT, LineageGraphFragment | None]:
    """Resolve metadata through bundle-aware coordinator seams when available."""
    if coordinator is not None:
        bundle_factory = (
            getattr(coordinator, bundle_factory_name, None)
            if _has_explicit_member(coordinator, bundle_factory_name)
            else None
        )
        if callable(bundle_factory):
            bundle = bundle_factory(input_data)
            metadata = cast(
                "MetadataT",
                cast(Any, bundle).metadata,  # Any: lineage bundle duck-type
            )
            lineage_fragment = cast(
                "LineageGraphFragment | None",
                cast(Any, bundle).lineage_fragment,  # Any: lineage bundle duck-type
            )
            return metadata, lineage_fragment
        if coordinator_factory_name is not None and _has_explicit_member(
            coordinator, coordinator_factory_name
        ):
            coordinator_factory = getattr(coordinator, coordinator_factory_name, None)
            if callable(coordinator_factory):
                return cast("MetadataT", coordinator_factory(input_data)), None
    return fallback_factory(), None


async def persist_lineage_fragment_if_present(
    *,
    lineage_store: LineageStorePort | None,
    lineage_fragment: LineageGraphFragment | None,
    metrics: MetricsPort | None = None,
    pipeline_name: str | None = None,
    layer: str | None = None,
    required: bool = False,
) -> None:
    """Persist one lineage fragment when lineage storage is configured."""
    if lineage_fragment is None:
        if required:
            raise RuntimeError(
                "Strict metadata publication requires a lineage fragment: "
                f"pipeline={pipeline_name or 'unknown'}, layer={layer or 'unknown'}"
            )
        return
    if lineage_store is None:
        if required:
            raise RuntimeError(
                "Strict metadata publication requires a lineage store: "
                f"pipeline={pipeline_name or 'unknown'}, layer={layer or 'unknown'}"
            )
        return
    try:
        # Keep blocking lineage store I/O off the event loop (ARCH-CR-01 / #6863).
        await asyncio.to_thread(lineage_store.save, lineage_fragment)
    except (OSError, TypeError, ValueError):
        _emit_lineage_fragment_metric(
            metrics,
            pipeline_name=pipeline_name,
            layer=layer,
            status="failed",
        )
        raise
    _emit_lineage_fragment_metric(
        metrics,
        pipeline_name=pipeline_name,
        layer=layer,
        status="success",
    )
