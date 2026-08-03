# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
        "api_url: https://config.example\ntimeout_seconds: 45\noptional_name:\n",
        encoding="utf-8",
    )

    data = YamlSettingsSource(_ExampleSettings)()

    assert data == {
        "api_url": "https://config.example",
        "timeout_seconds": 45,
    }
