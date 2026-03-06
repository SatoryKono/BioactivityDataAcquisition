"""Default contract policy for transformer lineage/hash behavior."""

from __future__ import annotations

import dataclasses


@dataclasses.dataclass(frozen=True)
class _DefaultContractPolicy:
    """Fallback contract policy when none is injected."""

    primary_key: list[str] = dataclasses.field(default_factory=lambda: ["entity_id"])
    merge_keys: list[str] = dataclasses.field(default_factory=lambda: ["entity_id"])
    rename_map: dict[str, str] = dataclasses.field(
        default_factory=lambda: {
            "run_id": "_run_id",
            "run_type": "_run_type",
            "source_batch_id": "_source_batch_id",
            "ingestion_ts": "_ingestion_ts",
            "source": "_source",
        }
    )
    hash_include: list[str] = dataclasses.field(default_factory=list)
    hash_exclude: list[str] = dataclasses.field(
        default_factory=lambda: ["_ingestion_ts", "_run_id", "_run_type"]
    )
