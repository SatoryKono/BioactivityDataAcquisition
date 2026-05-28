"""Support helpers for cross-cutting reproducibility contract tests."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

from bioetl.application.composite.merger_metrics_mixin import MergeMetricsRecorderMixin
from bioetl.application.composite.runner_pkg.runner_observability_mixin import (
    CompositeRunnerObservabilityMixin,
)
from bioetl.domain.composite.config import (
    CompositeConfig,
    DependencyConfig,
    EnricherConfig,
    MergeConfig,
    SeedConfig,
)
from bioetl.domain.composite.strategy import ConflictResolution, MergeStrategy
from bioetl.domain.types import RunID


@dataclass(frozen=True)
class ManifestIdentity:
    pipeline_name: str = "chembl_activity"
    provider: str = "chembl"
    entity: str = "activity"
    contract_ref: str = "chembl.activity"


DEFAULT_MANIFEST_IDENTITY = ManifestIdentity()


class InMemoryRunLedgerStore:
    def __init__(self) -> None:
        self._items: dict[str, list[object]] = {}

    def append(self, entry: object) -> None:
        manifest_id = entry.manifest_id
        self._items.setdefault(manifest_id, []).append(entry)

    def list_entries(self, manifest_id: str) -> tuple[object, ...]:
        return tuple(self._items.get(manifest_id, ()))


def make_merge_metrics_mixin() -> MergeMetricsRecorderMixin:
    mixin = MergeMetricsRecorderMixin.__new__(MergeMetricsRecorderMixin)
    mixin._logger = MagicMock()
    mixin._config = SimpleNamespace(exclude_fields=())
    return mixin


class CompositeReplayHost(CompositeRunnerObservabilityMixin):
    def __init__(self) -> None:
        self._config = SimpleNamespace(
            name="publication",
            dq=SimpleNamespace(
                soft_fail_threshold=0.1,
                hard_fail_threshold=0.2,
            ),
            merge=SimpleNamespace(
                output_silver_path="silver/publication",
                output_gold_path="gold/publication",
            ),
        )
        self._logger = MagicMock()
        self._run_id = RunID(UUID("00000000-0000-0000-0000-000000000401"))
        self._run_id_str = str(self._run_id)
        self._runtime = SimpleNamespace(cached_bronze_date="2025-02-03")
        self._started_at = datetime(2025, 2, 5, 9, 30, tzinfo=UTC)
        self._dq_report_service = None
        self._quarantine_port = AsyncMock()
        self._metrics = None


def build_replay_matrix_composite_config() -> CompositeConfig:
    """Build a canonical composite config for full-envelope exact replay evidence."""
    return CompositeConfig(
        name="composite_publication",
        version="1.0.0",
        seed=SeedConfig(
            pipeline="pubmed_publication",
            output_keys=("publication_id",),
            silver_table="publication",
        ),
        dependencies=(
            DependencyConfig(
                pipeline="crossref_publication",
                join_keys=("publication_id",),
                silver_table="publication",
            ),
        ),
        enrichers=(
            EnricherConfig(
                pipeline="openalex_publication",
                join_keys=("publication_id",),
                silver_table="publication",
            ),
        ),
        merge=MergeConfig(
            strategy=MergeStrategy.LEFT_OUTER,
            conflict_resolution=ConflictResolution.SEED_PRIORITY,
            output_silver_path="data/output/silver/composite/publication",
            output_gold_path="data/output/gold/composite/publication",
        ),
    )


def write_composite_snapshot_envelope(bronze_root: Path) -> None:
    """Materialize seed/dependency/enricher cached-Bronze files for replay tests."""
    for provider, entity in (
        ("pubmed", "publication"),
        ("crossref", "publication"),
        ("openalex", "publication"),
    ):
        bronze_day = bronze_root / provider / entity / "2026-01-01"
        bronze_day.mkdir(parents=True, exist_ok=True)
        (bronze_day / f"batch_{provider}_{entity}.jsonl.zst").write_bytes(
            f"{provider}:{entity}:snapshot".encode()
        )


def load_manifest_payload(data_dir: Path, manifest_id: str) -> dict[str, object]:
    manifest_path = (
        data_dir / "output" / "control" / "run_manifest" / f"{manifest_id}.json"
    )
    return json.loads(manifest_path.read_text(encoding="utf-8"))
