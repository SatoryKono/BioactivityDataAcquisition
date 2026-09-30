"""Short-lived, server-local selector catalog with one in-flight disk scan."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from time import monotonic

from bioetl.application.observability.control_plane_evidence.timing import (
    evidence_stage,
)
from bioetl.application.services.run_reports.query import ReportIndexEntry
from bioetl.domain.control_plane import RunManifest, WorkflowManifest
from bioetl.domain.ports import RunManifestPort, WorkflowManifestPort
from bioetl.interfaces.http._selector_options_cache import SelectorOptionsCache

SelectorCatalogSnapshot = tuple[tuple[RunManifest, ...], tuple[WorkflowManifest, ...]]
SELECTOR_ENDPOINT_CONCURRENCY = 4
SELECTOR_CATALOG_TTL_SECONDS = 5.0
SELECTOR_ENDPOINT_QUEUE_TIMEOUT_SECONDS = 2.0


class SelectorCatalog:
    """Share scans and briefly cache manifests, never ledger evidence or errors.

    Cancelling a caller cannot cancel the shared scan or start a duplicate.
    Successful snapshots expire five seconds after completion.
    """

    def __init__(self) -> None:
        self.options = SelectorOptionsCache()
        self._task: asyncio.Task[SelectorCatalogSnapshot] | None = None
        self._snapshot: SelectorCatalogSnapshot | None = None
        self._expires_at = 0.0
        self._report_tasks: dict[
            tuple[str, ...], asyncio.Task[list[ReportIndexEntry]]
        ] = {}
        self._report_snapshots: dict[
            tuple[str, ...], tuple[list[ReportIndexEntry], float]
        ] = {}

    async def read_reports(
        self,
        scopes: dict[str, tuple[str, ...]],
        loader: Callable[[dict[str, tuple[str, ...]]], list[ReportIndexEntry]],
    ) -> list[ReportIndexEntry]:
        """Share report index reads for the same owner scope; retain one snapshot.

        The loader enumerates owners only. Workflow, run ID, type and status
        filtering still happens after this read against checked identities.
        """
        key = tuple(
            sorted(set(scopes.get("pipeline", ())) - {"", "All", "all", "$__all", ".*"})
        )
        snapshot = self._report_snapshots.get(key)
        if snapshot is not None and monotonic() < snapshot[1]:
            return snapshot[0]
        if key not in self._report_tasks:
            task = asyncio.create_task(
                asyncio.to_thread(_read_report_catalog, loader, {"pipeline": key})
            )
            self._report_tasks[key] = task
            task.add_done_callback(lambda result: self._complete_reports(key, result))
        return await asyncio.shield(self._report_tasks[key])

    def _complete_reports(
        self, key: tuple[str, ...], task: asyncio.Task[list[ReportIndexEntry]]
    ) -> None:
        self._report_tasks.pop(key)
        if not task.cancelled() and task.exception() is None:
            if key not in self._report_snapshots and len(self._report_snapshots) >= 32:
                self._report_snapshots.pop(next(iter(self._report_snapshots)))
            self._report_snapshots[key] = (
                task.result(),
                monotonic() + SELECTOR_CATALOG_TTL_SECONDS,
            )

    async def read(
        self, manifests: RunManifestPort, workflows: WorkflowManifestPort | None
    ) -> SelectorCatalogSnapshot:
        """Read a fresh catalog, sharing any already running scan."""
        if self._snapshot is not None and monotonic() < self._expires_at:
            return self._snapshot
        if self._task is None:
            self._snapshot = None
            self._task = asyncio.create_task(self._load(manifests, workflows))
            self._task.add_done_callback(self._complete)
        return await asyncio.shield(self._task)

    def _complete(self, task: asyncio.Task[SelectorCatalogSnapshot]) -> None:
        self._task = None
        if not task.cancelled() and task.exception() is None:
            self._snapshot = task.result()
            self._expires_at = monotonic() + SELECTOR_CATALOG_TTL_SECONDS

    @staticmethod
    async def _load(
        manifests: RunManifestPort, workflows: WorkflowManifestPort | None
    ) -> SelectorCatalogSnapshot:
        # Drain both reads on failure before permitting a retry; a thread-backed
        # read cannot be cancelled when its sibling fails.
        manifest_task = asyncio.create_task(
            asyncio.to_thread(_read_manifest_catalog, manifests)
        )
        workflow_task = asyncio.create_task(
            asyncio.to_thread(_read_workflow_catalog, workflows)
            if workflows is not None
            else asyncio.sleep(0, result=())
        )
        await asyncio.gather(manifest_task, workflow_task, return_exceptions=True)
        return manifest_task.result(), workflow_task.result()


def _read_manifest_catalog(manifests: RunManifestPort) -> tuple[RunManifest, ...]:
    """Read the run manifest catalog under the request-bound stage observer."""
    with evidence_stage("selector_manifest_catalog"):
        return manifests.list_all()


def _read_workflow_catalog(
    workflows: WorkflowManifestPort,
) -> tuple[WorkflowManifest, ...]:
    """Read the workflow manifest catalog under the request-bound stage observer."""
    with evidence_stage("selector_workflow_catalog"):
        return workflows.list_all()


def _read_report_catalog(
    loader: Callable[[dict[str, tuple[str, ...]]], list[ReportIndexEntry]],
    scopes: dict[str, tuple[str, ...]],
) -> list[ReportIndexEntry]:
    """Read the report index under the request-bound stage observer."""
    with evidence_stage("selector_report_catalog"):
        return loader(scopes)
