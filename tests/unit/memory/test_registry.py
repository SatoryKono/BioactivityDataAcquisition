"""Tests for the machine-readable AI memory surface registry."""

from __future__ import annotations

from copy import deepcopy

import pytest

from memory.registry import load_memory_registry, validate_memory_registry

pytestmark = pytest.mark.unit


def test_repository_memory_registry_is_valid_and_deterministic() -> None:
    registry = load_memory_registry()

    assert registry["schema_version"] == 1
    assert validate_memory_registry(registry) == []
    memory_ids = [surface["memory_id"] for surface in registry["surfaces"]]
    assert memory_ids == list(dict.fromkeys(memory_ids))


def test_registry_rejects_missing_owner_and_duplicate_id() -> None:
    registry = load_memory_registry()
    invalid = deepcopy(registry)
    invalid["surfaces"][0]["owner"] = ""
    invalid["surfaces"][1]["memory_id"] = invalid["surfaces"][0]["memory_id"]

    messages = [issue.message for issue in validate_memory_registry(invalid)]

    assert "owner must be a non-empty string" in messages
    assert any(message.startswith("duplicate memory_id:") for message in messages)


def test_registry_requires_mirror_source_and_marks_unproven_usage() -> None:
    registry = load_memory_registry()
    invalid = deepcopy(registry)
    mirror_idx = next(
        i
        for i, surface in enumerate(invalid["surfaces"])
        if surface.get("canonicality") == "mirror"
    )
    invalid["surfaces"][mirror_idx]["source_of_truth"] = None
    invalid["surfaces"][mirror_idx]["runtime_usage_proven"] = False
    invalid["surfaces"][mirror_idx]["status"] = "WARN"

    messages = [issue.message for issue in validate_memory_registry(invalid)]

    assert "mirror must declare source_of_truth" in messages
    assert "unproven runtime usage must have NOT_PROVEN status" in messages
