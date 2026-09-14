"""RHAI nine-domain audit cards must exist and match REGISTRY.yaml (#10416)."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from scripts.ai.prompts.registry import load_registry

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
RHAI_PATH = ROOT / "scripts" / "ai" / "grok" / "workflows" / "nine-domain-audit.rhai"
GENERATOR_PATH = ROOT / "scripts" / "ai" / "generate_project_domain_audit_workflow.py"
PROMPTS_PREFIX = "docs/00-project/ai/prompts/"

_RHAI_DOMAIN = re.compile(
    r"id:\s*\"(?P<id>[^\"]+)\".*?"
    r"prompt_id:\s*\"(?P<prompt_id>[^\"]+)\".*?"
    r"card_path:\s*\"(?P<card_path>[^\"]+)\"",
    re.DOTALL,
)
_STRING_LIST = re.compile(r"let (?P<name>all_prompts|all_prompt_ids) = \[(?P<body>.*?)\];", re.DOTALL)


def _parse_string_list(source: str, name: str) -> list[str]:
    for match in _STRING_LIST.finditer(source):
        if match.group("name") == name:
            return re.findall(r"\"([^\"]+)\"", match.group("body"))
    raise AssertionError(f"missing let {name} in {GENERATOR_PATH}")


def test_nine_domain_rhai_card_paths_match_registry() -> None:
    source = RHAI_PATH.read_text(encoding="utf-8")
    domains = list(_RHAI_DOMAIN.finditer(source))
    assert len(domains) == 9, [match.group("id") for match in domains]
    registry = {entry.id: entry for entry in load_registry()}
    for match in domains:
        prompt_id = match.group("prompt_id")
        card_path = match.group("card_path").replace("\\", "/")
        assert (ROOT / card_path).is_file(), card_path
        entry = registry[prompt_id]
        expected = PROMPTS_PREFIX + entry.path.replace("\\", "/")
        assert card_path == expected, (match.group("id"), card_path, expected)


def test_domain_audit_generator_cards_match_registry() -> None:
    source = GENERATOR_PATH.read_text(encoding="utf-8")
    prompts = _parse_string_list(source, "all_prompts")
    prompt_ids = _parse_string_list(source, "all_prompt_ids")
    assert len(prompts) == len(prompt_ids) == 9
    registry = {entry.id: entry for entry in load_registry()}
    for prompt_id, card_path in zip(prompt_ids, prompts, strict=True):
        posix = card_path.replace("\\", "/")
        assert (ROOT / posix).is_file(), posix
        entry = registry[prompt_id]
        expected = PROMPTS_PREFIX + entry.path.replace("\\", "/")
        assert posix == expected, (prompt_id, posix, expected)
    rhai_ids = [
        match.group("prompt_id")
        for match in _RHAI_DOMAIN.finditer(RHAI_PATH.read_text(encoding="utf-8"))
    ]
    assert prompt_ids == rhai_ids
