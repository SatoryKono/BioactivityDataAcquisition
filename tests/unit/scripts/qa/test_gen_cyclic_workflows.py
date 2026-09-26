"""Regression tests for the cyclic Grok workflow-card generator."""

from __future__ import annotations

import hashlib

import pytest

from scripts.engineering.qa import _gen_cyclic_workflows as generator

pytestmark = pytest.mark.unit

EXPECTED_CARD_COUNT = 26
EXPECTED_RENDER_DIGEST = (
    "1505e01cbc707e48cfecc47d37127418645468c002d347443f0bcb72464684e8"
)


def _render_digest() -> str:
    payload = "".join(
        name
        + "\0"
        + generator.render(
            name,
            prompt_id,
            description,
            generator.normalize_defaults(defaults),
        )
        + "\0"
        for prompt_id, name, description, defaults in generator.CARDS
    ).encode()
    return hashlib.sha256(payload).hexdigest()


def test_card_constants_cover_only_exact_semantic_values() -> None:
    repository_values = [
        defaults["REPO"]
        for _prompt_id, _name, _description, defaults in generator.CARDS
        if "REPO" in defaults
    ]
    dashboard_scopes = [
        defaults["SCOPE"]
        for _prompt_id, _name, _description, defaults in generator.CARDS
        if defaults.get("SCOPE") == generator.DASHBOARD_SCOPE
    ]
    test_scopes = [
        defaults["SCOPE"]
        for _prompt_id, _name, _description, defaults in generator.CARDS
        if defaults.get("SCOPE") == generator.TEST_SCOPE
    ]

    assert len(generator.CARDS) == EXPECTED_CARD_COUNT
    assert repository_values == [generator.REPOSITORY_SLUG] * 23
    assert dashboard_scopes == [generator.DASHBOARD_SCOPE] * 6
    assert test_scopes == [generator.TEST_SCOPE] * 3
    assert any(
        defaults.get("SCOPE") == "src/bioetl/ tests/architecture/"
        for _prompt_id, _name, _description, defaults in generator.CARDS
    )


def test_normalize_defaults_preserves_input_and_key_order() -> None:
    defaults = {
        "ALLOW_PUSH": "false",
        "ALLOW_MERGE": "true",
        "CUSTOM": "kept",
    }
    before = dict(defaults)

    normalized = generator.normalize_defaults(defaults)

    assert defaults == before
    assert list(normalized)[:3] == list(before)
    assert normalized["ALLOW_PUSH"] == "true"
    assert normalized["ALLOW_MERGE"] == "false"
    assert normalized["CUSTOM"] == "kept"
    assert normalized["MODE"] == "full"
    assert normalized["MONITORING"] == "true"
    assert normalized["ALLOW_ISSUE_WRITE"] == "true"
    assert normalized["ALLOW_CLOSE"] == "true"


def test_rendered_workflow_cards_remain_byte_stable() -> None:
    assert _render_digest() == EXPECTED_RENDER_DIGEST
