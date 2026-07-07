"""Regression guards for #6038 governance and contract taxonomy drift."""

from __future__ import annotations

from pathlib import Path
import re

import pytest
import yaml


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _markdown_section(text: str, heading_prefix: str) -> str:
    lines = text.splitlines()
    for index, line in enumerate(lines):
        if line.startswith(heading_prefix):
            section_lines: list[str] = []
            for candidate in lines[index + 1 :]:
                if candidate.startswith("#") and not candidate.startswith(
                    heading_prefix
                ):
                    break
                section_lines.append(candidate)
            return "\n".join(section_lines)
    raise AssertionError(f"Missing markdown section starting with {heading_prefix!r}")


def _mkdocs_block(name: str) -> str:
    match = re.search(
        rf"^{re.escape(name)}:\s*\|\n(?P<body>(?:    .+\n)+)",
        _read("mkdocs.yml"),
        flags=re.MULTILINE,
    )
    assert match is not None, f"mkdocs.yml missing {name} block"
    return match.group("body")


def test_issue_6038_ai_runtime_precedence_delegates_to_agents() -> None:
    """NORMATIVE_SOURCES must not carry a stale AI runtime precedence copy."""
    section = _markdown_section(
        _read("docs/00-project/NORMATIVE_SOURCES.md"),
        "## Precedence",
    )
    agents_section = _markdown_section(_read("AGENTS.md"), "## Canonical Precedence")

    assert "AGENTS.md" in section
    assert "параллельный нумерованный список precedence" in section
    assert "matching runtime profiles/skills" in section
    assert "1. [RULES.md]" not in section
    assert "runtime profiles and skills" in agents_section
    assert "`docs/00-project/NORMATIVE_SOURCES.md`" in agents_section


def test_issue_6038_debt_budget_rule_has_no_adr_escape_hatch() -> None:
    """Active governance docs must not suggest debt-budget increases are allowed."""
    rules_section = _markdown_section(
        _read("docs/00-project/RULES.md"),
        "### 1.1.4.",
    )
    agents_text = _read("AGENTS.md")

    assert "scorecard budgets" in rules_section
    assert "exemption limits" in rules_section
    assert "hotspot thresholds" in rules_section
    assert "ADR-утверж" not in rules_section
    assert "ADR approval" not in rules_section
    assert "увеличение бюджетов запрещено" in agents_text


def test_issue_6038_contract_docs_separate_entity_contracts_and_error_catalog() -> None:
    """Entity data contracts and the error catalog must be distinct doc concepts."""
    error_catalog = yaml.safe_load(
        (ROOT / "configs/contracts/errors/error_catalog.yaml").read_text(
            encoding="utf-8"
        )
    )
    assert error_catalog["schema_version"] == "error-catalog-v1"

    active_docs = {
        "docs/02-architecture/current-state-inventory.md": _read(
            "docs/02-architecture/current-state-inventory.md"
        ),
        "docs/04-reference/contracts/data-contracts-current.md": _read(
            "docs/04-reference/contracts/data-contracts-current.md"
        ),
        "docs/04-reference/contracts/dq-contracts.md": _read(
            "docs/04-reference/contracts/dq-contracts.md"
        ),
        "docs/04-reference/contracts/gold-schemas.md": _read(
            "docs/04-reference/contracts/gold-schemas.md"
        ),
        "docs/03-guides/dq-configuration.md": _read(
            "docs/03-guides/dq-configuration.md"
        ),
        "docs/02-architecture/current-state-diagrams.md": _read(
            "docs/02-architecture/current-state-diagrams.md"
        ),
    }

    current_state = active_docs["docs/02-architecture/current-state-inventory.md"]
    data_contracts = active_docs[
        "docs/04-reference/contracts/data-contracts-current.md"
    ]

    assert "| Entity data contracts | 27 |" in current_state
    assert "| Error catalog | 1 |" in current_state
    assert "27 active YAML entity data contracts" in data_contracts
    assert "not counted in the 27 entity data contracts" in data_contracts
    for path, text in active_docs.items():
        assert "configs/contracts/**/*.yaml" not in text, path


def test_issue_6038_ai_readme_repo_only_metadata_matches_mkdocs() -> None:
    """The top-level AI README must be repo-only/internal and excluded from nav."""
    readme = _read("docs/00-project/ai/README.md")
    assert (
        "Status: internal (repo-only entrypoint; excluded from MkDocs nav/publication)"
        in readme
    )
    assert "Class: internal" in readme

    for block_name in ("exclude_docs", "not_in_nav"):
        assert "00-project/ai/README.md" in _mkdocs_block(block_name)
