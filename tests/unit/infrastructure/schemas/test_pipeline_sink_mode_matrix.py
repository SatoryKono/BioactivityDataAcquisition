from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from pydantic import ValidationError as PydanticValidationError

from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

pytestmark = pytest.mark.unit

# layer, mode, should_pass
_LAYER_MODE_CASES: tuple[tuple[str, str | None, bool], ...] = (
    ("bronze", "append", True),
    ("bronze", None, True),
    ("bronze", "merge", False),
    ("bronze", "overwrite", False),
    ("bronze", "scd2", False),
    ("bronze", "UNKNOWN", False),
    ("bronze", "", False),
    ("silver", "append", True),
    ("silver", "merge", True),
    ("silver", None, True),
    ("silver", "overwrite", False),
    ("silver", "scd2", False),
    ("silver", "delete", False),
    ("silver", "UNKNOWN", False),
    ("silver", "", False),
    ("gold", "append", True),
    ("gold", "overwrite", True),
    ("gold", "scd2", True),
    ("gold", None, True),
    ("gold", "merge", False),
    ("gold", "UNKNOWN", False),
    ("gold", "", False),
    ("bronze", "APPEND", False),
    ("silver", "Merge", False),
    ("gold", "Scd2", False),
)


def _pipeline_schema() -> dict[str, Any]:
    """Load the generated pipeline JSON schema next to this checkout."""
    anchor = Path(__file__).resolve()
    schema_path = anchor.parents[4].joinpath("configs", "_schema", "pipeline.json")
    payload = json.loads(schema_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        message = "pipeline.json must be a JSON object"
        raise TypeError(message)
    return cast(dict[str, Any], payload)


_SCHEMA = _pipeline_schema()


def _payload(layer: str, mode: str | None, *, include_mode: bool) -> dict[str, Any]:
    sink_layer: dict[str, Any] = {
        "enabled": True,
        "sort_by": ["entity_id"],
    }
    if include_mode:
        sink_layer["mode"] = mode
    return {
        "pipeline_name": "demo_item",
        "provider": "demo",
        "entity_type": "item",
        "business_primary_keys": ["id"],
        "technical_primary_key": "entity_id",
        "sink": {layer: sink_layer},
    }


@pytest.mark.parametrize(("layer", "mode", "should_pass"), _LAYER_MODE_CASES)
def test_pipeline_sink_mode_pydantic_validation(
    layer: str,
    mode: str | None,
    should_pass: bool,
) -> None:
    payload = _payload(layer, mode, include_mode=True)
    if should_pass:
        PipelineYamlConfig.model_validate(payload)
        return
    with pytest.raises(PydanticValidationError, match="Invalid mode|Input should be"):
        PipelineYamlConfig.model_validate(payload)


@pytest.mark.parametrize(("layer", "mode", "should_pass"), _LAYER_MODE_CASES)
def test_pipeline_sink_mode_jsonschema_validation(
    layer: str,
    mode: str | None,
    should_pass: bool,
) -> None:
    payload = _payload(layer, mode, include_mode=True)
    if should_pass:
        validate(instance=payload, schema=_SCHEMA)
        return
    with pytest.raises(JsonSchemaValidationError):
        validate(instance=payload, schema=_SCHEMA)


def test_unknown_layer_rejected() -> None:
    payload = _payload("platinum", "append", include_mode=True)
    with pytest.raises(PydanticValidationError, match="Unknown sink layer"):
        PipelineYamlConfig.model_validate(payload)
    with pytest.raises(JsonSchemaValidationError):
        validate(instance=payload, schema=_SCHEMA)


def test_disabled_sink_invalid_mode_rejected() -> None:
    payload = _payload("silver", "invalid_mode", include_mode=True)
    payload["sink"]["silver"]["enabled"] = False
    with pytest.raises(PydanticValidationError, match="Invalid mode"):
        PipelineYamlConfig.model_validate(payload)
    with pytest.raises(JsonSchemaValidationError):
        validate(instance=payload, schema=_SCHEMA)


def test_omitted_mode_preserves_default() -> None:
    payload = _payload("silver", None, include_mode=False)
    config = PipelineYamlConfig.model_validate(payload)
    assert config.sink["silver"].mode is None
    validate(instance=payload, schema=_SCHEMA)
