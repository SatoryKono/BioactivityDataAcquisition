"""Unit tests for Prompt Library CLI (epic #8513)."""

from __future__ import annotations


import pytest

from scripts.ai.prompts.check import check_hygiene, check_registry
from scripts.ai.prompts.registry import (
    PROMPTS_ROOT,
    find_entry,
    load_card,
    load_registry,
    parse_frontmatter,
)
from scripts.ai.prompts.render import render_by_id, substitute_params
from scripts.ai.prompts.__main__ import main as prompts_main

pytestmark = pytest.mark.unit


def test_registry_loads_and_ids_unique() -> None:
    entries = load_registry()
    assert entries, "REGISTRY.yaml must have entries"
    ids = [e.id for e in entries]
    assert len(ids) == len(set(ids))
    # minimum skeleton from #8514
    assert any(e.id == "prompt.closeout.grok" for e in entries)
    assert any(e.class_ == "fragment" for e in entries)
    assert sum(1 for e in entries if e.class_ == "operator-paste") >= 4


def test_registry_paths_exist() -> None:
    for entry in load_registry():
        assert entry.absolute_path.is_file(), entry.path


def test_parse_frontmatter() -> None:
    text = "---\nid: prompt.example.demo\nversion: 1.0.0\n---\n\n# Body\n"
    meta, body = parse_frontmatter(text)
    assert meta["id"] == "prompt.example.demo"
    assert body.strip().startswith("# Body")


def test_load_card_closeout() -> None:
    entry = find_entry(load_registry(), "prompt.closeout.grok")
    card = load_card(entry.absolute_path)
    assert card.id == "prompt.closeout.grok"
    assert "debt-budget-ban.md" in " ".join(card.includes)
    assert card.related_ssot
    assert "Done table" in card.body or "Done table" in card.body.title()


def test_render_includes_fragments() -> None:
    text = render_by_id("prompt.audit.grok-cycle")
    assert "prompt-id: prompt.audit.grok-cycle" in text
    assert "Git / safety" in text or "git" in text.lower()
    assert "Tech-debt" in text or "tech-debt" in text.lower() or "ЗАПРЕЩЕНО" in text
    assert "Env guardrail" in text or ".env" in text


def test_substitute_params_missing_raises() -> None:
    with pytest.raises(ValueError, match="missing required param"):
        substitute_params("hello {{SCOPE}}", {})


def test_substitute_params_ok() -> None:
    assert substitute_params("x={{SCOPE}}", {"SCOPE": "a/b"}) == "x=a/b"


def test_check_registry_ok() -> None:
    report = check_registry()
    assert report.ok, format_errors(report)


def test_check_hygiene_ok() -> None:
    report = check_hygiene()
    assert report.ok, format_errors(report)


def test_cli_list(capsys: pytest.CaptureFixture[str]) -> None:
    code = prompts_main(["list", "--class", "operator-paste"])
    assert code == 0
    out = capsys.readouterr().out
    assert "prompt.closeout.grok" in out


def test_cli_show(capsys: pytest.CaptureFixture[str]) -> None:
    code = prompts_main(["show", "prompt.closeout.grok"])
    assert code == 0
    out = capsys.readouterr().out
    assert "id: prompt.closeout.grok" in out


def test_cli_render(capsys: pytest.CaptureFixture[str]) -> None:
    code = prompts_main(
        ["render", "prompt.tests.fix-retest", "--param", "SCOPE=tests/unit"]
    )
    assert code == 0
    out = capsys.readouterr().out
    assert "prompt-id: prompt.tests.fix-retest" in out


def test_cli_check_registry(capsys: pytest.CaptureFixture[str]) -> None:
    code = prompts_main(["check-registry"])
    assert code == 0
    out = capsys.readouterr().out
    assert "OK" in out or "stats" in out


def test_cli_unknown_id() -> None:
    code = prompts_main(["show", "prompt.does.not.exist"])
    assert code != 0


def format_errors(report: object) -> str:
    errors = getattr(report, "errors", [])
    return "; ".join(f"{e.code}: {e.message}" for e in errors)


def test_prompts_root_layout() -> None:
    assert (PROMPTS_ROOT / "REGISTRY.yaml").is_file()
    assert (PROMPTS_ROOT / "fragments" / "git-safety.md").is_file()
    assert (PROMPTS_ROOT / "library" / "closeout" / "grok-closeout.md").is_file()
    assert (PROMPTS_ROOT / "archive" / "mirrors").is_dir()
