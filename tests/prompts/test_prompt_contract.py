"""Contract tests for the 15 Prompt Library scenarios (epic #10081 / #10082)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ai.prompts.registry import (
    PROMPTS_ROOT,
    SCHEMA_PATH,
    find_entry,
    load_card,
    load_registry,
    load_scenarios,
)

pytestmark = pytest.mark.unit

SCENARIOS = load_scenarios()


def _jsonschema_validate(instance: dict) -> list[str]:
    try:
        from jsonschema import Draft202012Validator  # type: ignore[import-untyped]
    except ImportError:
        pytest.skip("jsonschema not available")
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    return [
        e.message
        for e in sorted(validator.iter_errors(instance), key=lambda e: list(e.path))
    ]


@pytest.mark.parametrize("scenario", SCENARIOS, ids=lambda item: str(item["id"]))
def test_scenario_prompt_contract(scenario: dict) -> None:
    assert len(SCENARIOS) == 15
    assert scenario["scenario"]
    assert scenario["role"]
    assert scenario["schema"] == "_schema/prompt.schema.json" or str(
        scenario["schema"]
    ).startswith("_schema/")
    assert scenario.get("inputs")
    assert scenario.get("outputs")
    prompt_id = str(scenario["prompt"])
    entry = find_entry(load_registry(), prompt_id)
    card = load_card(entry.absolute_path)
    errors = _jsonschema_validate(card.raw_frontmatter)
    assert not errors, f"{prompt_id}: {errors}"
    declared = {str(name).upper() for name in card.params}
    for raw in scenario["inputs"]:
        name = str(raw).upper()
        assert name in declared, f"{prompt_id} missing param {name}"
    assert card.summary or entry.summary
    assert "{{" in card.body or card.params, f"{prompt_id} has no params/tokens"
