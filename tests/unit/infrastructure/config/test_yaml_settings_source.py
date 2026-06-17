"""Tests for YAML-backed application settings source."""

from __future__ import annotations

from pathlib import Path

import pytest
from pydantic.fields import FieldInfo
from pydantic_settings import BaseSettings, SettingsConfigDict

from bioetl.infrastructure.config._yaml_settings_source import YamlSettingsSource


pytestmark = pytest.mark.unit


class _ExampleSettings(BaseSettings):
    model_config = SettingsConfigDict(env_file_encoding="utf-8")

    api_url: str = "https://default.example"
    timeout_seconds: int = 30
    optional_name: str | None = None


def _field(name: str) -> FieldInfo:
    return _ExampleSettings.model_fields[name]


def test_get_field_value_reads_mapping_payload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "api_url: https://config.example\n",
        encoding="utf-8",
    )

    value, key, is_complex = YamlSettingsSource(_ExampleSettings).get_field_value(
        _field("api_url"),
        "api_url",
    )

    assert value == "https://config.example"
    assert key == "api_url"
    assert is_complex is False


def test_get_field_value_returns_none_when_config_file_is_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.chdir(tmp_path)

    value, key, is_complex = YamlSettingsSource(_ExampleSettings).get_field_value(
        _field("api_url"),
        "api_url",
    )

    assert value is None
    assert key == "api_url"
    assert is_complex is False


@pytest.mark.parametrize("payload", ["- not-a-mapping\n", "null\n"])
def test_get_field_value_ignores_non_mapping_yaml(
    payload: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(payload, encoding="utf-8")

    value, key, is_complex = YamlSettingsSource(_ExampleSettings).get_field_value(
        _field("api_url"),
        "api_url",
    )

    assert value is None
    assert key == "api_url"
    assert is_complex is False


def test_call_returns_present_yaml_values_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / "config.yaml").write_text(
        "api_url: https://config.example\n"
        "timeout_seconds: 45\n"
        "optional_name:\n",
        encoding="utf-8",
    )

    data = YamlSettingsSource(_ExampleSettings)()

    assert data == {
        "api_url": "https://config.example",
        "timeout_seconds": 45,
    }
