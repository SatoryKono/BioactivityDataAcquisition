"""Common BioETL exceptions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, SupportsIndex

if TYPE_CHECKING:
    from bioetl.domain.value_objects import RunId

__all__ = [
    "BioetlError",
    "ConfigError",
    "ConfigValidationError",
    "ProviderError",
    "ClientError",
    "ClientNetworkError",
    "ClientRateLimitError",
    "ClientResponseError",
    "PipelineStageError",
]


class BioetlError(Exception):
    """Base BioETL exception."""


class ConfigError(BioetlError):
    """Configuration errors."""


class ConfigValidationError(ConfigError):
    """Configuration validation errors."""


class ProviderError(BioetlError):
    """Data provider errors."""

    def __init__(
        self, provider: str, message: str, *, cause: Exception | None = None
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.cause = cause


class ClientError(ProviderError):
    """Base exception for client errors."""

    def __init__(
        self,
        provider: str,
        message: str,
        *,
        endpoint: str | None = None,
        cause: Exception | None = None,
        status_code: int | None = None,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(provider=provider, message=message, cause=cause)
        self.endpoint = endpoint
        self.status_code = status_code
        self.details = details or {}

    def __str__(self) -> str:
        base = f"{self.__class__.__name__} for provider '{self.provider}'"
        if self.endpoint:
            base += f" endpoint '{self.endpoint}'"
        if self.status_code is not None:
            base += f" (status={self.status_code})"
        return base + f": {self.args[0]}"


class ClientNetworkError(ClientError):
    """Client network errors."""


class ClientRateLimitError(ClientError):
    """Rate limit errors."""


class ClientResponseError(ClientError):
    """Client response errors."""


class PipelineStageError(BioetlError):
    """Exception for pipeline stage failures."""

    def __init__(
        self,
        provider: str,
        entity: str,
        stage: str,
        attempt: int,
        run_id: str | RunId,
        *,
        cause: Exception | None = None,
    ) -> None:
        message = (
            f"Stage '{stage}' failed for entity '{entity}' provider "
            f"'{provider}' on attempt {attempt} (run_id={run_id})"
        )
        super().__init__(message)
        self.provider = provider
        self.entity = entity
        self.stage = stage
        self.attempt = attempt
        self.run_id = str(run_id)  # Convert RunId to str for pickle compatibility
        self.cause = cause

    def __str__(self) -> str:
        base = (
            f"PipelineStageError(provider='{self.provider}', "
            f"entity='{self.entity}', stage='{self.stage}', "
            f"attempt={self.attempt}, run_id='{self.run_id}')"
        )
        return base + f": {self.args[0]}"

    def __reduce_ex__(self, protocol: SupportsIndex) -> tuple[Any, tuple[Any, ...]]:
        """Delegate to custom __reduce__ for all pickle protocols."""

        return self.__reduce__()

    def __reduce__(self) -> tuple[Any, tuple[Any, ...]]:
        """Make exception serializable for multiprocessing."""

        return (
            _rebuild_pipeline_stage_error,
            (
                self.provider,
                self.entity,
                self.stage,
                self.attempt,
                self.run_id,
                self.cause,
            ),
        )


def _rebuild_pipeline_stage_error(
    provider: str,
    entity: str,
    stage: str,
    attempt: int,
    run_id: str,
    cause: Exception | None,
) -> PipelineStageError:
    """Rebuild PipelineStageError after unpickle."""
    return PipelineStageError(
        provider=provider,
        entity=entity,
        stage=stage,
        attempt=attempt,
        run_id=run_id,
        cause=cause,
    )
