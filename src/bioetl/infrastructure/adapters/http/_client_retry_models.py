"""Internal retry-state models for HTTP client retry orchestration."""

from __future__ import annotations

from dataclasses import dataclass


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
