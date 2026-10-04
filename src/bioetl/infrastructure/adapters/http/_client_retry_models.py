"""Internal retry-state models for HTTP client retry orchestration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

import httpx

from bioetl.domain.ports import LoggerPort, TracingPort
from bioetl.domain.resilience import RetryConfig
from bioetl.domain.types import RunID


@dataclass(frozen=True, slots=True)
class _RequestAttemptOutcome:
    """Retry-stage outcome for a single request attempt."""

    should_retry: bool
    status_code: int
    retries_increment: int
    last_error: Exception | None


@dataclass(slots=True)
class _RetryRequestState:
    """Mutable request-level retry state for the main retry loop."""

    status_code: int = 0
    retries: int = 0
    attempts_made: int = 0
    last_error: Exception | None = None

    def record_attempt(self, attempt: int) -> None:
        """Track the most recent attempt index as a 1-based count."""
        self.attempts_made = attempt + 1

    def apply_attempt_outcome(self, outcome: _RequestAttemptOutcome) -> bool:
        """Apply one retry outcome and report whether the loop should continue."""
        self.status_code = outcome.status_code
        self.retries += outcome.retries_increment
        self.last_error = outcome.last_error
        return outcome.should_retry


class _RetryRequestHost(Protocol):
    """Static host contract implemented by the concrete HTTP retry mixin."""

    retry_config: RetryConfig
    provider: str
    logger: LoggerPort | None
    _tracer: TracingPort | None
    run_id: RunID | None

    def _get_client(self) -> httpx.AsyncClient: ...

    def _observability_run_id(self) -> str: ...

    def _can_retry(self, attempt: int, retries_used: int) -> bool: ...

    async def _handle_retry_delay(
        self, attempt: int, url: str = "", response: httpx.Response | None = None
    ) -> float: ...

    def _log_retry(
        self,
        url: str,
        method: str,
        attempt: int,
        wait_seconds: float,
        *,
        status_code: int | None = None,
        reason: str | None = None,
    ) -> None: ...

    def _record_retry_budget_exhausted(self, method: str, url: str) -> None: ...

    def _record_request_metrics(
        self,
        method: str,
        duration: float,
        status_code: int,
        retries: int,
        last_error: Exception | None,
    ) -> None: ...

    def _should_continue_retry(
        self,
        result: httpx.Response | _RequestAttemptOutcome,
        retry_state: _RetryRequestState,
    ) -> bool: ...

    async def _execute_single_attempt(
        self,
        client: httpx.AsyncClient,
        method: str,
        url: str,
        attempt_number: int = 1,
        **kwargs: object,
    ) -> httpx.Response: ...
