# mypy: disable-error-code="misc"
"""YAML-backed pydantic-settings source for application settings."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml
from pydantic.fields import FieldInfo
from pydantic_settings import PydanticBaseSettingsSource

from bioetl.domain.types import JsonDict


class YamlSettingsSource(PydanticBaseSettingsSource):
    """A settings source that loads variables from a YAML file."""

    def get_field_value(
        self, field: FieldInfo, field_name: str
    ) -> tuple[Any, str, bool]:  # Any: YAML config has heterogeneous values
        """Get value of a field from YAML file."""
        encoding = self.config.get("env_file_encoding")
        try:
            with Path("config.yaml").open(encoding=encoding) as f:
                file_content = yaml.safe_load(f)
        except FileNotFoundError:
            return None, field_name, False

        if not isinstance(file_content, dict):
            return None, field_name, False

        field_value = file_content.get(field_name)
        return field_value, field_name, False

    def prepare_field_value(
        self,
        field_name: str,
        field: FieldInfo,
        value: Any,  # Any: dynamic config value from env/yaml
        value_is_complex: bool,
    ) -> Any:  # Any: dynamic config value passed to pydantic
        """Prepare value of a field."""
        return value

    def __call__(self) -> JsonDict:  # Any: YAML config has heterogeneous values
        data: JsonDict = {}  # Any: YAML config has heterogeneous values

        for field_name, field in self.settings_cls.model_fields.items():
            field_value, field_key, value_is_complex = self.get_field_value(
                field, field_name
            )
            if field_value is not None:
                field_value = self.prepare_field_value(
                    field_name, field, field_value, value_is_complex
                )
                data[field_key] = field_value

        return data
