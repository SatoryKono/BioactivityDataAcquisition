# Host attrs/methods provided by concrete composition.
"""Internal fetch-routing surface for the PubChem adapter."""

from __future__ import annotations

__all__ = ["_PubChemClientFetchMixin"]

from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, Protocol, cast

from bioetl.domain.types import JsonDict
from bioetl.infrastructure.adapters.pubchem.fetch_flow import (
    ExecutorTimeoutState,
    wait_for_executor,
)
from bioetl.infrastructure.adapters.sync_base import BaseSyncAdapter

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

    from bioetl.infrastructure.adapters.pubchem.fetch_strategies import (
        PubChemFetchStrategies,
    )


class _PoolFinalizer(Protocol):
    """Owned-pool finalizer surface used when a timed-out worker is abandoned."""

    @property
    def alive(self) -> bool: ...

    def detach(self) -> None: ...


class _PubChemClientFetchMixin:
    """Fetch routing and filtered dispatch for the PubChem adapter."""

    _strategies: PubChemFetchStrategies = cast(
        Any, None
    )  # Any: host attr default (PD3)
    _executor_timeout_sec: float | None
    _executor_timeout_state: ExecutorTimeoutState
    _owns_thread_pool: bool
    thread_pool: ThreadPoolExecutor

    async def _run_in_executor(
        self,
        func: Callable[..., object],
        *args: object,
    ) -> object:
        """Wait for one SDK call. A timeout leaves the worker thread running."""
        return await wait_for_executor(
            BaseSyncAdapter._run_in_executor(cast(BaseSyncAdapter, self), func, *args),
            self._executor_timeout_sec,
            self._executor_timeout_state,
        )

    async def close(self) -> None:
        """Do not block the event loop on a worker that may still be in urllib."""
        if self._executor_timeout_state.timed_out and self._owns_thread_pool:
            finalizer = cast(_PoolFinalizer | None, getattr(self, "_finalizer", None))
            if finalizer is not None and finalizer.alive:
                finalizer.detach()
            self.thread_pool.shutdown(wait=False, cancel_futures=True)
            return
        await BaseSyncAdapter.close(cast(BaseSyncAdapter, self))

    async def _fetch_compound(
        self, query: str | None, limit: int | None
    ) -> AsyncIterator[JsonDict]:
        """Fetch compounds by query."""
        if not query:
            raise ValueError("Query is required for compound fetch")
        async for record in self._strategies.fetch_by_query(query, limit):
            yield record

    async def fetch(
        self,
        entity_type: str,
        limit: int | None = None,
        query: str | None = None,
        filter_ids: list[str] | None = None,
        filter_field: str | None = None,
        offset: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch records from PubChem via search or filter routes."""
        del offset
        if filter_ids and filter_field:
            async for record in self.fetch_filtered(
                entity_type, filter_ids, filter_field, limit
            ):
                yield record
            return

        fetch_methods: dict[str, Callable[[], AsyncIterator[JsonDict]]] = {
            "compound": lambda: self._fetch_compound(query, limit),
            "substance": lambda: self._strategies.fetch_substances(query, limit),
            "assay": lambda: self._strategies.fetch_assays(query, limit),
        }

        method = fetch_methods.get(entity_type)
        if method is None:
            raise ValueError(f"Unsupported entity type: {entity_type}")

        async for record in method():
            yield record

    async def fetch_filtered(
        self,
        entity_type: str,
        filter_ids: list[str],
        filter_field: str,
        limit: int | None = None,
    ) -> AsyncIterator[JsonDict]:
        """Fetch PubChem records by filter ID list."""
        if entity_type != "compound":
            raise ValueError(
                f"fetch_filtered only supports 'compound', got: {entity_type}"
            )

        if filter_field in ("smiles", "canonical_smiles"):
            async for record in self._strategies.fetch_by_smiles(filter_ids, limit):
                yield record
        elif filter_field == "cid":
            async for record in self._strategies.fetch_by_cids(filter_ids, limit):
                yield record
        elif filter_field in ("inchikey", "inchi_key"):
            async for record in self._strategies.fetch_by_inchikey(filter_ids, limit):
                yield record
        else:
            raise ValueError(f"Unsupported filter_field: {filter_field}")
