"""Guardrails against stale config/runtime references in agent/docs artifacts."""

from __future__ import annotations

from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]

TARGET_FILES = (
    Path(".codex/agents/py-config-bot.md"),
    Path("docs/00-project/ai/agents/agents/py-config-bot.md"),
    Path("docs/00-project/ai/memory/memory-py-config-bot.md"),
    Path(".codex/agents/py-audit-bot.md"),
    Path(".codex/agents/py-doc-bot.md"),
    Path(".codex/agents/py-plan-bot.md"),
    Path("docs/00-project/ai/memory/memory-py-plan-bot.md"),
    Path("docs/02-architecture/diagrams/views/46-yaml-config-resolution-full.mermaid"),
    Path("docs/02-architecture/diagrams/foundation/46-yaml-config-resolution.mmd"),
    Path("docs/02-architecture/diagrams/architecture/11-configuration-system.mmd"),
    Path(
        "docs/02-architecture/diagrams/descriptions/architecture/11-configuration-system.md"
    ),
    Path("docs/02-architecture/diagrams/architecture/11a-config-loading.mmd"),
    Path(
        "docs/02-architecture/diagrams/descriptions/architecture/11a-config-loading.md"
    ),
)

OBSOLETE_PATTERNS = (
    "configs/pipelines/",
    "configs/dq/",
    "configs/filter/",
    "configs/sources/",
    "configs/quality/entities/",
    "configs/filters/entities/",
    "configs/filters/*.yaml",
    "configs/field_groups/*.yaml",
    "FieldGroupLoader",
)

RUNTIME_FACT_TARGET_FILES = (
    Path(".codex/agents/ORCHESTRATION.md"),
    Path(".codex/agents/py-audit-bot.md"),
    Path(".codex/agents/py-config-bot.md"),
    Path(".codex/agents/py-doc-bot.md"),
    Path(".codex/agents/py-plan-bot.md"),
    Path("docs/00-project/ai/agents/agents/ORCHESTRATION.md"),
    Path("docs/00-project/ai/agents/agents/py-audit-bot.md"),
    Path("docs/00-project/ai/agents/agents/py-config-bot.md"),
    Path("docs/00-project/ai/agents/agents/py-doc-bot.md"),
    Path("docs/00-project/ai/agents/agents/py-plan-bot.md"),
    Path("docs/00-project/ai/memory/memory-py-config-bot.md"),
    Path("docs/00-project/ai/memory/memory-py-doc-bot.md"),
    Path("docs/00-project/ai/memory/memory-py-plan-bot.md"),
)

OBSOLETE_RUNTIME_FACT_PATTERNS = (
    "40 ADR",
    "ADR-001..ADR-040",
    "IUPHAR",
    "Open Targets",
    "docs/00-map.md",
    "docs/04-reference/glossary.md",
)


@pytest.mark.parametrize("relative_path", TARGET_FILES)
def test_agent_and_doc_artifacts_do_not_reference_obsolete_config_topology(
    relative_path: Path,
) -> None:
    text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    violations = [pattern for pattern in OBSOLETE_PATTERNS if pattern in text]
    assert not violations, (
        f"{relative_path} contains obsolete config-topology references: {violations}"
    )


@pytest.mark.parametrize("relative_path", RUNTIME_FACT_TARGET_FILES)
def test_agent_and_doc_artifacts_do_not_reference_obsolete_runtime_facts(
    relative_path: Path,
) -> None:
    text = (PROJECT_ROOT / relative_path).read_text(encoding="utf-8")
    violations = [
        pattern for pattern in OBSOLETE_RUNTIME_FACT_PATTERNS if pattern in text
    ]
    assert not violations, (
        f"{relative_path} contains obsolete runtime facts or paths: {violations}"
    )
