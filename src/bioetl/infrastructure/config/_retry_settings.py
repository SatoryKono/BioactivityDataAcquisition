"""Retry configuration settings for various operations."""

from __future__ import annotations

from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AtomicReplaceRetrySettings(BaseSettings):
    """Atomic ``Path.replace`` retry policy for metadata sidecars."""

    model_config = SettingsConfigDict(frozen=True)

    enabled: bool = Field(default=True)
    adaptive_backoff: bool = Field(default=True)
    max_retries: int = Field(default=20, ge=0, le=30)
    base_delay_seconds: float = Field(default=0.010, ge=0.0, le=5.0)
    max_delay_seconds: float = Field(default=0.250, ge=0.0, le=10.0)
    jitter_seconds: float = Field(default=0.010, ge=0.0, le=1.0)


class SilverMergeRetrySettings(BaseSettings):
    """Retry policy for Delta commit conflict retries in Silver merge."""

    model_config = SettingsConfigDict(frozen=True)

    enabled: bool = Field(default=True)
    adaptive_backoff: bool = Field(default=True)
    max_retries: int = Field(default=3, ge=0, le=20)
    base_delay_seconds: float = Field(default=0.250, ge=0.0, le=30.0)
    max_delay_seconds: float = Field(default=2.0, ge=0.0, le=60.0)
    jitter_seconds: float = Field(default=0.050, ge=0.0, le=5.0)


class SilverMergeTimeoutSettings(BaseSettings):
    """Timeout and retry policy for Delta merge execution in Silver."""

    model_config = SettingsConfigDict(frozen=True)

    profile: Literal["default", "unit", "e2e"] = Field(default="default")
    execution_timeout_seconds: float = Field(default=45.0, ge=1.0, le=600.0)
    unit_execution_timeout_seconds: float = Field(default=15.0, ge=1.0, le=600.0)
    e2e_execution_timeout_seconds: float = Field(default=90.0, ge=1.0, le=600.0)
    plain_write_process_isolation: bool = Field(default=False)
    retry_enabled: bool = Field(default=True)
    adaptive_backoff: bool = Field(default=True)
    max_retries: int = Field(default=1, ge=0, le=10)
    base_delay_seconds: float = Field(default=0.200, ge=0.0, le=30.0)
    max_delay_seconds: float = Field(default=2.0, ge=0.0, le=60.0)
    jitter_seconds: float = Field(default=0.050, ge=0.0, le=5.0)
