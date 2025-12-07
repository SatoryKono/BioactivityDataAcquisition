from __future__ import annotations

from pathlib import Path

from pydantic import ValidationError
import pytest
import yaml

from bioetl.domain.configs.pipeline import PipelineConfig


def _load_yaml(path: Path) -> dict:
    with path.open("r", encoding="utf-8") as fp:
        return yaml.safe_load(fp) or {}


def test_pipeline_configs_validate(configs_root: Path) -> None:
    violations: list[str] = []
    for config_file in configs_root.glob("pipelines/*/*.yaml"):
        data = _load_yaml(config_file)
        try:
            PipelineConfig(**data)
        except ValidationError as exc:
            violations.append(f"{config_file.as_posix()}: {exc}")

    if violations:
        pytest.fail("Невалидные pipeline-конфиги:\n" + "\n".join(violations))


def test_misc_configs_parse(configs_root: Path) -> None:
    errors: list[str] = []
    for path in configs_root.rglob("*.yaml"):
        if "/pipelines/" in path.as_posix():
            continue
        try:
            loaded = _load_yaml(path)
            if not isinstance(loaded, dict):
                errors.append(
                    f"{path.as_posix()}: ожидается словарь, получено {type(loaded)}"
                )
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{path.as_posix()}: {exc}")

    if errors:
        pytest.fail("Ошибки разбора YAML конфигов:\n" + "\n".join(errors))
