"""Unit tests for deterministic layer-aware sink contracts."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from jsonschema import ValidationError as JsonSchemaValidationError
from jsonschema import validate
from pydantic import ValidationError as PydanticValidationError

from bioetl.infrastructure.schemas.pipeline_config import PipelineYamlConfig

pytestmark = pytest.mark.unit

def _get_schema() -> dict[str, object]:
    schema_path = Path(__file__).resolve().parents[4] / "configs" / "_schema" / "pipeline.json"

    with open(schema_path, encoding="utf-8") as f:
        return json.load(f)

SCHEMA = _get_schema()

def _base_payload() -> dict[str, object]:
    return {
        "pipeline_name": "demo_item",
        "provider": "demo",
        "entity_type": "item",
        "business_primary_keys": ["id"],
        "technical_primary_key": "entity_id",
    }

# Parameters: layer, mode, should_pass
MATRIX = [
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
]

MIXED_CASE_MATRIX = [
    ("bronze", "APPEND", False),
    ("silver", "Merge", False),
    ("gold", "Scd2", False),
]

@pytest.mark.parametrize("layer, mode, should_pass", MATRIX + MIXED_CASE_MATRIX)
def test_pipeline_sink_mode_pydantic_validation(layer: str, mode: str | None, should_pass: bool) -> None:
    payload = _base_payload()
    payload["sink"] = {
        layer: {
            "enabled": True,
            "sort_by": ["entity_id"],
        }
    }
    # Need to strictly preserve None instead of omitting, to test explicit None logic
    payload["sink"][layer]["mode"] = mode

    if should_pass:
        PipelineYamlConfig.model_validate(payload)
    else:
        with pytest.raises(PydanticValidationError) as exc:
            PipelineYamlConfig.model_validate(payload)
        assert "Invalid mode" in str(exc.value) or "Input should be" in str(exc.value)

@pytest.mark.parametrize("layer, mode, should_pass", MATRIX + MIXED_CASE_MATRIX)
def test_pipeline_sink_mode_jsonschema_validation(layer: str, mode: str | None, should_pass: bool) -> None:
    payload = _base_payload()
    payload["sink"] = {
        layer: {
            "enabled": True,
            "sort_by": ["entity_id"],
        }
    }
    payload["sink"][layer]["mode"] = mode

    if should_pass:
        validate(instance=payload, schema=SCHEMA)
    else:
        with pytest.raises(JsonSchemaValidationError):
            validate(instance=payload, schema=SCHEMA)

def test_unknown_layer_rejected() -> None:
    payload = _base_payload()
    payload["sink"] = {
        "platinum": {
            "enabled": True,
            "mode": "append",
            "sort_by": ["entity_id"],
        }
    }
    with pytest.raises(PydanticValidationError) as exc:
        PipelineYamlConfig.model_validate(payload)
    assert "Unknown sink layer" in str(exc.value)

    with pytest.raises(JsonSchemaValidationError):
        validate(instance=payload, schema=SCHEMA)

def test_disabled_sink_invalid_mode_rejected() -> None:
    payload = _base_payload()
    payload["sink"] = {
        "silver": {
            "enabled": False,
            "mode": "invalid_mode",
            "sort_by": ["entity_id"],
        }
    }
    with pytest.raises(PydanticValidationError) as exc:
        PipelineYamlConfig.model_validate(payload)
    assert "Invalid mode" in str(exc.value)

    with pytest.raises(JsonSchemaValidationError):
        validate(instance=payload, schema=SCHEMA)

def test_omitted_mode_preserves_default() -> None:
    payload = _base_payload()
    payload["sink"] = {
        "silver": {
            "enabled": True,
            "sort_by": ["entity_id"],
        }
    }
    config = PipelineYamlConfig.model_validate(payload)
    assert config.sink["silver"].mode is None
    validate(instance=payload, schema=SCHEMA)
