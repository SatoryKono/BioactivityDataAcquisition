"""Runtime helpers for optional lineage-fragment materialization."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from typing import TYPE_CHECKING, TypeVar, cast

from bioetl.domain.ports import LineageStorePort

if TYPE_CHECKING:
    from bioetl.domain.lineage import LineageGraphFragment

__all__ = [
    "persist_lineage_fragment_if_present",
    "resolve_metadata_and_lineage_fragment",
]

MetadataT = TypeVar("MetadataT")


def _has_explicit_member(target: object, member_name: str) -> bool:
    """Return whether a method/property is explicitly present on instance or class."""
    return member_name in vars(target) or getattr(type(target), member_name, None) is not None


def resolve_metadata_and_lineage_fragment(
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
            metadata = cast("MetadataT", bundle.metadata)
            lineage_fragment = cast(
                "LineageGraphFragment | None",
                bundle.lineage_fragment,
            )
            return metadata, lineage_fragment
        if (
            coordinator_factory_name is not None
            and _has_explicit_member(coordinator, coordinator_factory_name)
        ):
            coordinator_factory = getattr(coordinator, coordinator_factory_name, None)
            if callable(coordinator_factory):
                return cast("MetadataT", coordinator_factory(input_data)), None
    return fallback_factory(), None


async def persist_lineage_fragment_if_present(
    *,
    lineage_store: LineageStorePort | None,
    lineage_fragment: LineageGraphFragment | None,
) -> None:
    """Persist one lineage fragment when lineage storage is configured."""
    if lineage_store is None or lineage_fragment is None:
        return
    await asyncio.to_thread(lineage_store.save, lineage_fragment)
