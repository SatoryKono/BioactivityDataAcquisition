"""Adapter runtime configuration value objects (domain purity)."""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["AdapterConfig"]


@dataclass(frozen=True, slots=True, init=False)
class AdapterConfig:
    """Validated adapter runtime knobs from provider config or direct tests.

    ``timeout`` is retained as a constructor alias for older direct adapter tests;
    ``timeout_sec`` remains the canonical stored field used by source configs.
    """

    batch_size: int = 20
    page_size: int = 1000
    timeout_sec: float = 30.0
    max_retries: int = 3
    retry_backoff_factor: float = 2.0
    rate_limit_requests_per_second: float = 5.0
    circuit_breaker_failure_threshold: int = 5
    circuit_breaker_recovery_timeout: int = 300
    enable_single_id_fallback: bool = False

    @staticmethod
    def _validate_timeout_alias(
        timeout: float | None,
        timeout_sec: float | None,
    ) -> None:
        """Validate that timeout and timeout_sec don't conflict."""
        if (
            timeout is not None
            and timeout_sec is not None
            and float(timeout) != float(timeout_sec)
        ):
            raise ValueError("timeout and timeout_sec must match when both are set")

    @staticmethod
    def _resolve_timeout(
        timeout: float | None,
        timeout_sec: float | None,
    ) -> float:
        """Resolve timeout value from alias or canonical parameter."""
        if timeout is not None:
            return float(timeout)
        if timeout_sec is None:
            return 30.0
        return float(timeout_sec)

    @staticmethod
    def _as_optional_float(value: object) -> float | None:
        """Coerce a legacy alias to float when numeric; otherwise None."""
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
        return None

    @staticmethod
    def _as_optional_int(value: object) -> int | None:
        """Coerce a legacy alias to int when numeric; otherwise None."""
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float) and value.is_integer():
            return int(value)
        return None

    @classmethod
    def _extract_legacy_aliases(
        cls,
        legacy_aliases: dict[str, object],
    ) -> tuple[float | None, int | None, int | None]:
        """Pop known retired constructor aliases; reject unknown keys."""
        timeout = cls._as_optional_float(legacy_aliases.pop("timeout", None))
        failure_threshold = cls._as_optional_int(
            legacy_aliases.pop("circuit_breaker_failure_threshold", None)
        )
        recovery_timeout = cls._as_optional_int(
            legacy_aliases.pop("circuit_breaker_recovery_timeout", None)
        )
        if legacy_aliases:
            unexpected = ", ".join(sorted(str(key) for key in legacy_aliases))
            raise TypeError(
                f"AdapterConfig() got unexpected keyword argument(s): {unexpected}"
            )
        return timeout, failure_threshold, recovery_timeout

    @staticmethod
    def _resolve_circuit_breaker(
        circuit_breaker: tuple[int, int],
        failure_threshold: int | None,
        recovery_timeout: int | None,
    ) -> tuple[int, int]:
        """Merge legacy circuit-breaker aliases into the canonical tuple."""
        if failure_threshold is None and recovery_timeout is None:
            return (int(circuit_breaker[0]), int(circuit_breaker[1]))
        return (
            int(failure_threshold)
            if failure_threshold is not None
            else int(circuit_breaker[0]),
            int(recovery_timeout)
            if recovery_timeout is not None
            else int(circuit_breaker[1]),
        )

    def _assign_fields(
        self,
        *,
        batch_size: int,
        page_size: int,
        timeout_sec: float,
        max_retries: int,
        retry_backoff_factor: float,
        rate_limit_requests_per_second: float,
        circuit_breaker: tuple[int, int],
        enable_single_id_fallback: bool,
    ) -> None:
        """Assign frozen dataclass fields via object.__setattr__."""
        object.__setattr__(self, "batch_size", batch_size)
        object.__setattr__(self, "page_size", page_size)
        object.__setattr__(self, "timeout_sec", float(timeout_sec))
        object.__setattr__(self, "max_retries", max_retries)
        object.__setattr__(self, "retry_backoff_factor", retry_backoff_factor)
        object.__setattr__(
            self,
            "rate_limit_requests_per_second",
            rate_limit_requests_per_second,
        )
        object.__setattr__(
            self,
            "circuit_breaker_failure_threshold",
            int(circuit_breaker[0]),
        )
        object.__setattr__(
            self,
            "circuit_breaker_recovery_timeout",
            int(circuit_breaker[1]),
        )
        object.__setattr__(
            self,
            "enable_single_id_fallback",
            enable_single_id_fallback,
        )

    def __init__(
        self,
        batch_size: int = 20,
        page_size: int = 1000,
        timeout_sec: float | None = None,
        max_retries: int = 3,
        retry_backoff_factor: float = 2.0,
        rate_limit_requests_per_second: float = 5.0,
        circuit_breaker: tuple[int, int] = (5, 300),
        enable_single_id_fallback: bool = False,
        **legacy_aliases: object,
    ) -> None:
        """Initialize adapter config while preserving retired constructor aliases."""
        timeout_value, failure_threshold, recovery_timeout = (
            self._extract_legacy_aliases(legacy_aliases)
        )
        self._validate_timeout_alias(timeout_value, timeout_sec)
        resolved_timeout = self._resolve_timeout(timeout_value, timeout_sec)
        resolved_breaker = self._resolve_circuit_breaker(
            circuit_breaker,
            failure_threshold,
            recovery_timeout,
        )
        self._assign_fields(
            batch_size=batch_size,
            page_size=page_size,
            timeout_sec=resolved_timeout,
            max_retries=max_retries,
            retry_backoff_factor=retry_backoff_factor,
            rate_limit_requests_per_second=rate_limit_requests_per_second,
            circuit_breaker=resolved_breaker,
            enable_single_id_fallback=enable_single_id_fallback,
        )
        self._validate()

    @property
    def timeout(self) -> float:
        """Backward-compatible alias for ``timeout_sec``."""
        return self.timeout_sec

    def _validate(self) -> None:
        """Validate configuration values on creation."""
        _validate_positive("batch_size", self.batch_size)
        _validate_positive("page_size", self.page_size)
        _validate_positive("timeout_sec", self.timeout_sec)
        _validate_non_negative("max_retries", self.max_retries)
        _validate_positive("retry_backoff_factor", self.retry_backoff_factor)
        _validate_positive(
            "rate_limit_requests_per_second",
            self.rate_limit_requests_per_second,
        )
        _validate_positive(
            "circuit_breaker_failure_threshold",
            self.circuit_breaker_failure_threshold,
        )
        _validate_positive(
            "circuit_breaker_recovery_timeout",
            self.circuit_breaker_recovery_timeout,
        )


def _validate_positive(name: str, value: int | float) -> None:
    """Validate that value is positive (> 0)."""
    if value <= 0:
        raise ValueError(f"{name} must be positive, got {value}")


def _validate_non_negative(name: str, value: int) -> None:
    """Validate that value is non-negative (>= 0)."""
    if value < 0:
        raise ValueError(f"{name} must be non-negative, got {value}")
