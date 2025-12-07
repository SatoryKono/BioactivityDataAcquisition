"""Загрузчик глобальных конфигураций по умолчанию."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from bioetl.domain.configs import (
    DefaultsConfig,
    HashingDefaultsConfig,
    NetworkDefaultsConfig,
    NormalizationDefaultsConfig,
    SourceDefaultsConfig,
    SourcesDefaultsConfig,
)
from bioetl.infrastructure.config.env import resolve_env_placeholders
from bioetl.infrastructure.config.sources import get_configs_root, get_yaml


class DefaultsConfigError(Exception):
    """Базовая ошибка загрузки дефолтных конфигов."""


class DefaultsFileNotFoundError(DefaultsConfigError):
    """Файл конфигурации не найден."""

    def __init__(self, path: Path) -> None:
        super().__init__(f"Defaults config file not found: {path}")
        self.path = path


class DefaultsValidationError(DefaultsConfigError):
    """Ошибка валидации конфигурации."""

    def __init__(self, path: Path, message: str) -> None:
        super().__init__(f"{path}: {message}")
        self.path = path


def load_defaults_config(*, base_dir: str | Path | None = None) -> DefaultsConfig:
    """Читает и валидирует глобальные конфигурации по умолчанию."""

    root = get_configs_root(base_dir).resolve()
    return _load_defaults_cached(root)


@lru_cache(maxsize=None)
def _load_defaults_cached(root: Path) -> DefaultsConfig:
    hashing_cfg = _load_section(
        root / "hashing.yaml", model=HashingDefaultsConfig, key="hashing"
    )
    normalization_cfg = _load_section(
        root / "normalization.yaml",
        model=NormalizationDefaultsConfig,
        key="normalization",
    )
    network_cfg, sources_defaults = _load_defaults_directory(root / "defaults")

    return DefaultsConfig(
        hashing=hashing_cfg,
        normalization=normalization_cfg,
        network=network_cfg,
        sources=sources_defaults,
    )


def _load_section(path: Path, *, model: type[Any], key: str) -> Any:
    if not path.exists():
        raise DefaultsFileNotFoundError(path)

    data = _read_yaml(path)
    if key not in data:
        raise DefaultsValidationError(path, f"Missing root key '{key}'")

    resolved = resolve_env_placeholders(data)
    try:
        return model.model_validate(resolved)
    except ValidationError as exc:
        raise DefaultsValidationError(path, exc.__str__()) from exc


def _load_defaults_directory(directory: Path) -> tuple[NetworkDefaultsConfig | None, dict[str, SourceDefaultsConfig]]:
    if not directory.exists():
        raise DefaultsFileNotFoundError(directory)

    network_cfg: NetworkDefaultsConfig | None = None
    sources: dict[str, SourceDefaultsConfig] = {}

    for path in sorted(directory.glob("*.yaml")):
        data = resolve_env_placeholders(_read_yaml(path))

        if "http" in data:
            network_cfg = _validate_model(
                path, data, model=NetworkDefaultsConfig, current=network_cfg
            )
        if "sources" in data:
            parsed_sources = _validate_model(path, data, model=SourcesDefaultsConfig)
            sources.update(parsed_sources.sources)

    return network_cfg, sources


def _validate_model(
    path: Path, data: Any, *, model: type[Any], current: Any | None = None
) -> Any:
    try:
        validated = model.model_validate(data)
    except ValidationError as exc:
        raise DefaultsValidationError(path, exc.__str__()) from exc

    if current is None:
        return validated
    return validated


def _read_yaml(path: Path) -> dict[str, Any]:
    try:
        return get_yaml(path)
    except FileNotFoundError as exc:
        raise DefaultsFileNotFoundError(path) from exc


__all__ = [
    "DefaultsConfigError",
    "DefaultsFileNotFoundError",
    "DefaultsValidationError",
    "load_defaults_config",
]
