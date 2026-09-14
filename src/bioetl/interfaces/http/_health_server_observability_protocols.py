"""Protocol surface for HealthServer observability routing."""

from __future__ import annotations

import asyncio
from typing import Protocol

from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.ports import RunManifestPort
from bioetl.domain.types import RunID


class _HealthResponseSupport(Protocol):
    async def _send_text_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        body: str,
        *,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None: ...

    async def _send_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        message: str,
    ) -> None: ...

    async def _send_payload_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        payload: dict[str, object],
    ) -> None: ...


class _RunLedgerLookup(Protocol):
    def list_entries_by_run_id(self, run_id: RunID) -> list[RunLedgerEntry]: ...


class _HealthObservabilityRoutingHost(_HealthResponseSupport, Protocol):
    @property
    def _run_manifest_port(self) -> RunManifestPort | None: ...

    @property
    def _forensic_endpoint_limiter(self) -> asyncio.Semaphore: ...

    @property
    def _prometheus_base_url(self) -> str: ...

    @property
    def _run_ledger_port(self) -> _RunLedgerLookup | None: ...

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...
