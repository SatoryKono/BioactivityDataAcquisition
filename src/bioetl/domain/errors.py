"""Общие исключения BioETL."""

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
    """Базовое исключение BioETL."""


class ConfigError(BioetlError):
    """Ошибки конфигурации."""


class ConfigValidationError(ConfigError):
    """Ошибки валидации конфигурации."""


class ProviderError(BioetlError):
    """Ошибки провайдера данных."""

    def __init__(
        self, provider: str, message: str, *, cause: Exception | None = None
    ) -> None:
        super().__init__(message)
        self.provider = provider
        self.cause = cause


class ClientError(ProviderError):
    """Базовое исключение для клиентских ошибок."""

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
    """Сетевые ошибки клиента."""


class ClientRateLimitError(ClientError):
    """Ошибки ограничения запросов (rate limit)."""


class ClientResponseError(ClientError):
    """Ошибки ответа клиента."""


class PipelineStageError(BioetlError):
    """Исключение для сбоев на стадиях пайплайна."""

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
        """Делает исключение сериализуемым для multiprocessing."""

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
    """Восстанавливает PipelineStageError после unpickle."""
    return PipelineStageError(
        provider=provider,
        entity=entity,
        stage=stage,
        attempt=attempt,
        run_id=run_id,
        cause=cause,
    )
