"""Protocol surface for HealthServer observability routing."""

from __future__ import annotations

import asyncio
from typing import Protocol

from bioetl.application.observability.control_plane_evidence import (
    ControlPlaneEvidenceService,
)
from bioetl.domain.control_plane import RunLedgerEntry
from bioetl.domain.ports import (
    CheckpointPort,
    RunLedgerPort,
    RunManifestPort,
    RunReportStorePort,
    WorkflowManifestPort,
)
from bioetl.domain.types import RunID
from bioetl.interfaces.http._selector_catalog import SelectorCatalog


class _HealthResponseSupport(Protocol):
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
    async def _send_text_response(
        self,
        writer: asyncio.StreamWriter,
        status_code: int,
        body: str,
        *,
        content_type: str = "text/plain; charset=utf-8",
    ) -> None: ...

    @property
    def _run_report_store(self) -> RunReportStorePort: ...

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


class _HealthRoutingHost(_HealthResponseSupport, Protocol):
    @property
    def _run_report_store(self) -> RunReportStorePort: ...

    @property
    def _control_plane_evidence_service(
        self,
    ) -> ControlPlaneEvidenceService | None: ...

    @property
    def _forensic_endpoint_limiter(self) -> asyncio.Semaphore: ...

    @property
    def _selector_endpoint_limiter(self) -> asyncio.Semaphore: ...

    @property
    def _selector_catalog(self) -> SelectorCatalog: ...

    @property
    def _checkpoint_port(self) -> CheckpointPort | None: ...

    @property
    def _run_manifest_port(self) -> RunManifestPort | None: ...

    @property
    def _run_ledger_port(self) -> RunLedgerPort | None: ...

    @property
    def _workflow_manifest_port(self) -> WorkflowManifestPort | None: ...

    @property
    def _data_root(self) -> str | None: ...

    @property
    def _runtime_source_id(self) -> str | None: ...

    def _read_required_param(self, query: dict[str, str], name: str) -> str: ...

    @staticmethod
    def _read_optional_param(query: dict[str, str], name: str) -> str | None: ...

    @staticmethod
    def _is_all_scope_token(value: str | None) -> bool: ...

    def _read_int_param(
        self,
        query: dict[str, str],
        name: str,
        default: int,
        *,
        minimum: int,
    ) -> int: ...

    @classmethod
    def _read_scope_csv_param(
        cls,
        query: dict[str, str],
        name: str,
    ) -> tuple[str, ...]: ...
