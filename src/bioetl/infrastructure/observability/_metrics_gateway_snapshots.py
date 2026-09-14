"""Partition process metrics into independently replaceable gateway snapshots."""

from __future__ import annotations

from collections.abc import Iterable
from copy import copy
from dataclasses import dataclass
from typing import Protocol

from prometheus_client.core import Metric


class MetricCollector(Protocol):
    """Exposition surface shared by full and restricted registries."""

    def collect(self) -> Iterable[Metric]: ...


@dataclass(frozen=True)
class MetricSnapshot:
    """Materialized samples keep one publication internally consistent."""

    metrics: tuple[Metric, ...]

    def collect(self) -> Iterable[Metric]:
        """Expose the original HELP/TYPE and selected samples."""
        return iter(self.metrics)


def partition_snapshots(
    registry: MetricCollector,
    *,
    job: str,
) -> list[tuple[str, dict[str, str], MetricSnapshot]]:
    """Keep pipeline/run-type snapshots and workflow jobs independent.

    Pipeline-only counters have one owner group, so workflow and standalone
    flushes cannot expose the same ledger/checkpoint series twice. Workflow
    metric jobs use the existing bounded workflow label, never a run identity.
    Empty families are omitted; an unrelated process cannot erase their data.
    """
    partitions: dict[tuple[str, tuple[tuple[str, str], ...]], dict[str, Metric]] = {}
    for metric in registry.collect():
        for sample in metric.samples:
            labels = sample.labels
            workflow = labels.get("workflow")
            sample_job = f"{job}_workflow_{workflow}" if workflow else job
            # Integrity refresh scans persisted scopes beyond this process's
            # executed runs. It must not replace their runtime snapshots.
            if metric.name == "bioetl_manifest_ledger_integrity_ratio":
                sample_job = f"{job}_control_plane"
            group = tuple(
                (key, labels[key]) for key in ("pipeline", "run_type") if key in labels
            )
            families = partitions.setdefault((sample_job, group), {})
            if metric.name not in families:
                family = copy(metric)
                family.samples = []
                families[metric.name] = family
            families[metric.name].samples.append(sample)
    # Replace the legacy unscoped process group before publishing scoped
    # samples, avoiding duplicate-series rejection during the transition.
    return [
        (sample_job, dict(group), MetricSnapshot(tuple(families.values())))
        for (sample_job, group), families in sorted(partitions.items())
    ]
