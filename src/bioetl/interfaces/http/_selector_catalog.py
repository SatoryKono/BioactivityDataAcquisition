"""Short-lived, server-local selector catalog with one in-flight disk scan."""

from __future__ import annotations

import asyncio
from time import monotonic

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
