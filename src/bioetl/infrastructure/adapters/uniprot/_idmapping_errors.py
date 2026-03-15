"""Exceptions for UniProt ID Mapping client."""

from __future__ import annotations

from bioetl.domain.exceptions.base import RecoverableError

__all__ = ["IDMappingJobError", "IDMappingTimeoutError"]


class IDMappingJobError(RecoverableError):
    """Raised when ID Mapping job fails."""

    def __init__(self, job_id: str, message: str) -> None:
        super().__init__(f"ID Mapping job {job_id} failed: {message}")
        self.job_id = job_id


class IDMappingTimeoutError(RecoverableError):
    """Raised when ID Mapping job polling times out."""

    def __init__(self, job_id: str, attempts: int) -> None:
        super().__init__(
            f"ID Mapping job {job_id} timed out after {attempts} polling attempts"
        )
        self.job_id = job_id
        self.attempts = attempts
