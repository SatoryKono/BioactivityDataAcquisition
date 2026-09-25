"""Short-lived, server-local selector catalog with one in-flight disk scan."""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from time import monotonic

from bioetl.application.services.run_reports.query import ReportIndexEntry
from bioetl.domain.control_plane import RunManifest, WorkflowManifest
from bioetl.domain.ports import RunManifestPort, WorkflowManifestPort

SelectorCatalogSnapshot = tuple[tuple[RunManifest, ...], tuple[WorkflowManifest, ...]]
SELECTOR_ENDPOINT_CONCURRENCY = 4
SELECTOR_CATALOG_TTL_SECONDS = 5.0


class SelectorCatalog:
    """Share scans and briefly cache manifests, never ledger evidence or errors.

    Cancelling a caller cannot cancel the shared scan or start a duplicate.
    Successful snapshots expire five seconds after completion.
    """

    def __init__(self) -> None:
        self._task: asyncio.Task[SelectorCatalogSnapshot] | None = None
        self._snapshot: SelectorCatalogSnapshot | None = None
        self._expires_at = 0.0
        self._report_tasks: dict[
            tuple[str, ...], asyncio.Task[list[ReportIndexEntry]]
        ] = {}
        self._report_snapshot: tuple[
            tuple[str, ...], list[ReportIndexEntry], float
        ] | None = None

    async def read_reports(
        self,
        scopes: dict[str, tuple[str, ...]],
        loader: Callable[[dict[str, tuple[str, ...]]], list[ReportIndexEntry]],
    ) -> list[ReportIndexEntry]:
        """Share report index reads for the same owner scope; retain one snapshot.

        The loader enumerates owners only. Workflow, run ID, type and status
        filtering still happens after this read against checked identities.
        """
        key = tuple(sorted(set(scopes.get("pipeline", ())) - {"", "All", "all", "$__all", ".*"}))
        snapshot = self._report_snapshot
        if snapshot is not None and snapshot[0] == key and monotonic() < snapshot[2]:
            return snapshot[1]
        if key not in self._report_tasks:
            self._report_snapshot = None
            task = asyncio.create_task(asyncio.to_thread(loader, {"pipeline": key}))
            self._report_tasks[key] = task
            task.add_done_callback(lambda result: self._complete_reports(key, result))
        return await asyncio.shield(self._report_tasks[key])

    def _complete_reports(
        self, key: tuple[str, ...], task: asyncio.Task[list[ReportIndexEntry]]
    ) -> None:
        self._report_tasks.pop(key)
        if not task.cancelled() and task.exception() is None:
            self._report_snapshot = (
                key, task.result(), monotonic() + SELECTOR_CATALOG_TTL_SECONDS
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
        manifest_task = asyncio.create_task(asyncio.to_thread(manifests.list_all))
        workflow_task = asyncio.create_task(
            asyncio.to_thread(workflows.list_all)
            if workflows is not None
            else asyncio.sleep(0, result=())
        )
        await asyncio.gather(manifest_task, workflow_task, return_exceptions=True)
        return manifest_task.result(), workflow_task.result()
