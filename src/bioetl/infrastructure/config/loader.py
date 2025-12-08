"""Загрузчик конфигураций пайплайнов."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bioetl.domain.configs import PipelineConfig
from bioetl.domain.errors import ConfigError, ConfigValidationError
from bioetl.domain.transform.merge import apply_deep_merge
from bioetl.infrastructure.config.provider_registry_loader import (
    ProviderNotConfiguredError,
    ProviderRegistryError,
    ensure_provider_known,
)
from bioetl.infrastructure.config.sources import (
    get_yaml_for_pipeline,
    get_yaml_from_path,
)


class ConfigFileNotFoundError(ConfigError):
    """Файл конфигурации не найден."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Config file not found: {path}")
        self.path = path


class UnknownProviderError(ConfigError):
    """Неизвестный провайдер."""

    def __init__(self, provider: str) -> None:
        super().__init__(f"Unknown provider: {provider}")
        self.provider = provider


def get_pipeline_config(
    pipeline_id: str,
    *,
    profile: str | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
    base_dir: str | Path | None = None,
) -> PipelineConfig:
    """Загружает конфигурацию пайплайна по идентификатору."""

    try:
        config_path, raw_config = get_yaml_for_pipeline(
            pipeline_id,
            profile=profile,
            base_dir=base_dir,
        )
    except FileNotFoundError as exc:
        path_str = str(exc).rsplit(": ", maxsplit=1)[-1]
        raise ConfigFileNotFoundError(Path(path_str)) from exc

    return _build_config(
        raw_config,
        config_path=config_path,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
    )


def get_pipeline_config_from_path(
    config_path: str | Path,
    *,
    profile: str | None = None,
    profiles_root: str | Path | None = None,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
) -> PipelineConfig:
    """Загружает конфигурацию пайплайна из файла."""

    try:
        path, raw_config = get_yaml_from_path(
            config_path,
            profile=profile,
            profiles_root=profiles_root,
        )
    except FileNotFoundError as exc:
        path_str = str(exc).rsplit(": ", maxsplit=1)[-1]
        raise ConfigFileNotFoundError(Path(path_str)) from exc

    return _build_config(
        raw_config,
        config_path=path,
        cli_overrides=cli_overrides,
        env_overrides=env_overrides,
    )


def _build_config(
    raw_config: dict[str, Any],
    *,
    config_path: Path,
    cli_overrides: dict[str, Any] | None = None,
    env_overrides: dict[str, Any] | None = None,
) -> PipelineConfig:
    """Собирает PipelineConfig из сырых данных с применением overrides."""

    merged = dict(raw_config)

    # Применяем overrides в порядке приоритета: env → CLI
    if env_overrides:
        merged = apply_deep_merge(merged, env_overrides)
    if cli_overrides:
        merged = apply_deep_merge(merged, cli_overrides)

    _ensure_input_path_exists(merged, config_path=config_path)

    provider_id = merged.get("provider")
    if isinstance(provider_id, str):
        _ensure_provider_registered(provider_id)

    try:
        return PipelineConfig.model_validate(merged)
    except ValidationError as exc:
        raise ConfigValidationError(
            f"Validation failed for {config_path}: {exc}"
        ) from exc


def _ensure_provider_registered(provider_id: str) -> None:
    """Проверяет наличие провайдера в реестре до валидации схемы."""

    try:
        ensure_provider_known(provider_id)
    except ProviderNotConfiguredError as exc:
        raise UnknownProviderError(provider_id) from exc
    except ProviderRegistryError as exc:
        raise ConfigError(
            f"Failed to verify provider '{provider_id}' against registry: {exc}"
        ) from exc


def _ensure_input_path_exists(
    merged_config: dict[str, Any],
    *,
    config_path: Path,
) -> None:
    """Проверяет существование локального входного файла для режимов CSV/ID."""

    input_mode = merged_config.get("input_mode")
    if input_mode not in {"csv", "id_only"}:
        return

    raw_input_path = merged_config.get("input_path")
    if not raw_input_path:
        return

    candidate = Path(str(raw_input_path)).expanduser()
    if not candidate.exists():
        raise ConfigValidationError(
            (
                f"Input path '{raw_input_path}' referenced by {config_path} does not "
                f"exist; required for input_mode '{input_mode}'."
            )
        )


__all__ = [
    "ConfigFileNotFoundError",
    "UnknownProviderError",
    "get_pipeline_config",
    "get_pipeline_config_from_path",
]
