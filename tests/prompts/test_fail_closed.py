"""P0 #11690/#11695 + P2 #11692 — fail-closed card defaults and README parity."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts.ai.prompts.check import (
    check_hygiene,
    check_readme_scenarios,
    fail_closed_violations,
)
from scripts.ai.prompts.registry import load_card

pytestmark = pytest.mark.unit

_PROBE_FRONTMATTER = """---
id: {card_id}
version: 0.1.0
status: active
class: operator-paste
owner: BioETL Team
params:
{params_yaml}
includes: []
related_ssot:
- AGENTS.md
---
"""


def _write_card(tmp_path: Path, name: str, params_yaml: str, body: str) -> Path:
    target = tmp_path / name
    target.write_text(
        _PROBE_FRONTMATTER.format(card_id="prompt.test.probe", params_yaml=params_yaml)
        + "\n"
        + body,
        encoding="utf-8",
    )
    return target


def test_fail_closed_violations_catch_frontmatter_and_table_true(
    tmp_path: Path,
) -> None:
    body = (
        "## Params\n\n| Param | Default |\n| --- | --- |\n"
        "| `ALLOW_PUSH` | `true` |\n"
    )
    card = load_card(
        _write_card(tmp_path, "probe.md", "- SCOPE\n- ALLOW_PUSH = true", body)
    )
    violations = fail_closed_violations(card)
    assert any("frontmatter" in v and "ALLOW_PUSH" in v for v in violations)
    assert any("Params table" in v and "ALLOW_PUSH" in v for v in violations)


def test_fail_closed_violations_clean_on_bare_names_and_false(
    tmp_path: Path,
) -> None:
    body = (
        "## Params\n\n| Param | Default |\n| --- | --- |\n"
        "| `ALLOW_PUSH` | `false` |\n"
        "| `MODE` | `audit` |\n"
    )
    card = load_card(
        _write_card(tmp_path, "clean.md", "- SCOPE\n- ALLOW_PUSH", body)
    )
    assert fail_closed_violations(card) == []


def test_hygiene_has_no_fail_closed_or_include_errors() -> None:
    report = check_hygiene()
    gated = {
        "fail_closed_default",
        "fragment_double_include",
        "rendered_size",
    }
    bad = [e for e in report.errors if e.code in gated]
    assert bad == [], "; ".join(f"{e.code}: {e.message}" for e in bad)


def test_readme_scenarios_match_registry() -> None:
    report = check_readme_scenarios()
    assert report.ok, "; ".join(
        f"{e.code}: {e.message}" for e in report.errors
    )


def _write_registry(tmp_path: Path, scenarios: list[dict[str, str]]) -> Path:
    target = tmp_path / "REGISTRY.yaml"
    target.write_text(
        yaml.safe_dump({"scenarios": scenarios}, allow_unicode=True),
        encoding="utf-8",
    )
    return target


def _scenario(scenario_id: str, prompt: str) -> dict[str, str]:
    return {
        "id": scenario_id,
        "scenario": f"Scenario {scenario_id}",
        "role": "any",
        "prompt": prompt,
        "schema": "_schema/prompt.schema.json",
    }


_README_TABLE = """# Probes

| Scenario | Prompt id | Card |
| --- | --- | --- |
| demo | `prompt.demo.one` | [one](library/demo/one.md) |
"""


def test_readme_scenarios_tmp_match(tmp_path: Path) -> None:
    registry = _write_registry(tmp_path, [_scenario("demo", "prompt.demo.one")])
    readme = tmp_path / "README.md"
    readme.write_text(_README_TABLE, encoding="utf-8")
    report = check_readme_scenarios(registry_path=registry, readme_path=readme)
    assert report.ok


def test_readme_scenarios_tmp_drift(tmp_path: Path) -> None:
    registry = _write_registry(tmp_path, [_scenario("demo", "prompt.demo.two")])
    readme = tmp_path / "README.md"
    readme.write_text(_README_TABLE, encoding="utf-8")
    report = check_readme_scenarios(registry_path=registry, readme_path=readme)
    assert any(e.code == "readme_prompt_drift" for e in report.errors)


def test_readme_scenarios_tmp_missing_row(tmp_path: Path) -> None:
    registry = _write_registry(
        tmp_path,
        [_scenario("demo", "prompt.demo.one"), _scenario("extra", "prompt.demo.x")],
    )
    readme = tmp_path / "README.md"
    readme.write_text(_README_TABLE, encoding="utf-8")
    report = check_readme_scenarios(registry_path=registry, readme_path=readme)
    codes = {e.code for e in report.errors}
    assert "readme_scenario_missing" in codes
