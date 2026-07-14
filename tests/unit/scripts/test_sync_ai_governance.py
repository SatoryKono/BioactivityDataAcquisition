"""Unit tests for AI governance sync script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ai import sync_ai_governance

pytestmark = pytest.mark.unit


def _seed_skills_mirror_fixture(root: Path) -> None:
    contract_path = root / sync_ai_governance.SKILLS_MIRROR_CONTRACT_PATH
    contract_path.parent.mkdir(parents=True)
    contract_path.write_text(
        json.dumps(
            {
                "schema_version": 1,
                "roots": {
                    "canonical": ".codex/skills",
                    "devin": ".devin/skills",
                    "docs_mirror": "docs/00-project/ai/skills/local",
                    "reference_overlay": "docs/00-project/ai/skills/_references/local",
                },
                "entrypoint": "SKILL.md",
                "catalog": "SKILLS-CATALOG.md",
                "codex_devin": {
                    "optional_presence_globs": [
                        "*/agents/openai.yaml",
                        "*/references/**",
                    ],
                    "allowed_content_variant_globs": [
                        "*/SKILL.md",
                        "*/agents/openai.yaml",
                    ],
                    "required_identical_when_shared_globs": ["*/references/**"],
                },
            }
        )
        + "\n",
        encoding="utf-8",
    )
    overlay = root / "docs/00-project/ai/skills/_references/local"
    overlay.mkdir(parents=True)

    catalog = "# Catalog\n\n- [demo](demo/SKILL.md)\n"
    for runtime, body in (
        (".codex", "# Codex demo\n"),
        (".devin", "# Devin demo\n"),
    ):
        skills = root / runtime / "skills"
        skill = skills / "demo"
        references = skill / "references"
        references.mkdir(parents=True)
        (skill / "SKILL.md").write_text(body, encoding="utf-8")
        (references / "shared.md").write_text("shared\n", encoding="utf-8")
        (skills / "SKILLS-CATALOG.md").write_text(catalog, encoding="utf-8")

    assert sync_ai_governance.sync_skill_mirrors(root, check_only=False) == []


def test_normalize_codex_agents_strips_mirror_header(tmp_path: Path) -> None:
    agents = tmp_path / ".codex" / "agents"
    agents.mkdir(parents=True)
    path = agents / "demo.md"
    path.write_text(
        "> Mirror status: mirror\n"
        "> Edit runtime first.\n"
        "______________________________________________________________________\n\n"
        "# Demo\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.normalize_codex_agents(tmp_path, check_only=False)
    assert issues == []
    text = path.read_text(encoding="utf-8")
    assert "Mirror status" not in text
    assert "NORMATIVE_SOURCES.md" in text


def test_normalize_codex_agents_preserves_role_memory_requirements(
    tmp_path: Path,
) -> None:
    agents = tmp_path / ".codex" / "agents"
    agents.mkdir(parents=True)
    path = agents / "py-test-swarm.md"
    path.write_text(
        "\n".join(
            [
                "## Canonical Sources",
                "",
                "Read before planning or editing:",
                "",
                "- `docs/00-project/NORMATIVE_SOURCES.md`",
                "- `AGENTS.md`",
                "",
                "# py-test-swarm",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.normalize_codex_agents(tmp_path, check_only=False)

    assert issues == []
    assert "docs/00-project/ai/memory/memory-py-test-swarm.md" in path.read_text(
        encoding="utf-8"
    )


def test_inject_docs_agent_sources_adds_block(tmp_path: Path) -> None:
    agents = tmp_path / "docs/00-project/ai/agents/agents"
    agents.mkdir(parents=True)
    path = agents / "demo.md"
    path.write_text(
        "> Mirror status: mirror\n"
        "______________________________________________________________________\n\n"
        "name: demo\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.inject_docs_agent_sources(tmp_path, check_only=False)
    assert issues == []
    assert "## Canonical Sources" in path.read_text(encoding="utf-8")


def test_normalize_codex_skills_adds_all_governance_tokens(tmp_path: Path) -> None:
    skills = tmp_path / ".codex" / "skills" / "suggest-users"
    skills.mkdir(parents=True)
    path = skills / "SKILL.md"
    path.write_text(
        "\n".join(
            [
                "# Suggest Users",
                "",
                "## Source Of Truth",
                "",
                "- Root runtime contract: `../../../AGENTS.md`",
                "- Project rules: `../../../docs/00-project/RULES.md`",
                "",
                "## Workflow",
                "",
                "1. Suggest reviewers.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.normalize_codex_skills(tmp_path, check_only=False)

    assert issues == []
    text = path.read_text(encoding="utf-8")
    assert "../../../docs/01-requirements/REQUIREMENTS.md" in text
    assert "../../../docs/02-architecture/decisions" in text
    assert "../../../docs/00-project/NORMATIVE_SOURCES.md" in text


def test_sync_docs_skill_mirrors_adds_runtime_header_and_tokens(
    tmp_path: Path,
) -> None:
    skills = tmp_path / "docs/00-project/ai/skills/local/public/architecture-guardian"
    skills.mkdir(parents=True)
    path = skills / "SKILL.md"
    path.write_text(
        "\n".join(
            [
                "---",
                'name: "architecture-guardian"',
                "---",
                "",
                "# Architecture Guardian",
                "",
                "## Workflow",
                "",
                "1. Check architecture.",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    issues = sync_ai_governance.sync_docs_skill_mirrors(tmp_path, check_only=False)

    assert issues == []
    text = path.read_text(encoding="utf-8")
    assert text.startswith("> Mirror status:")
    assert "not a canonical runtime surface" in "\n".join(text.splitlines()[:40])
    assert ".codex/skills/public/architecture-guardian/SKILL.md" in "\n".join(
        text.splitlines()[:40]
    )
    assert "AI_RUNTIME_MIRROR_OWNERSHIP.md" in "\n".join(text.splitlines()[:40])
    assert "../../../../../../AGENTS.md" in text
    assert "../../../../NORMATIVE_SOURCES.md" in text

    before = text
    assert sync_ai_governance.sync_docs_skill_mirrors(tmp_path, check_only=False) == []
    assert path.read_text(encoding="utf-8") == before


def test_skills_mirror_reports_missing_devin_entrypoint(tmp_path: Path) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    (tmp_path / ".devin/skills/demo/SKILL.md").unlink()

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)

    assert "Devin missing skill entrypoint: demo/SKILL.md" in issues


def test_skills_mirror_reports_unexpected_devin_entrypoint(tmp_path: Path) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    unexpected = tmp_path / ".devin/skills/unexpected/SKILL.md"
    unexpected.parent.mkdir(parents=True)
    unexpected.write_text("# Unexpected\n", encoding="utf-8")

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)

    assert "Devin unexpected skill entrypoint: unexpected/SKILL.md" in issues


def test_skills_mirror_reports_stale_catalog_membership(tmp_path: Path) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    (tmp_path / ".devin/skills/SKILLS-CATALOG.md").write_text(
        "# Stale catalog\n", encoding="utf-8"
    )

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)

    assert "Devin catalog missing entry: demo/SKILL.md" in issues


def test_skills_mirror_reports_required_identical_reference_drift(
    tmp_path: Path,
) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    (tmp_path / ".devin/skills/demo/references/shared.md").write_text(
        "drifted\n", encoding="utf-8"
    )

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)

    assert (
        "Codex/Devin required-identical mismatch: demo/references/shared.md" in issues
    )


def test_skills_mirror_check_reports_docs_drift_without_writing(
    tmp_path: Path,
) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    mirror = tmp_path / "docs/00-project/ai/skills/local/demo/SKILL.md"
    mirror.write_text("manual drift\n", encoding="utf-8")
    before = mirror.read_bytes()

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)
    exit_code = sync_ai_governance.main(
        ["--root", str(tmp_path), "--only", "skill-mirrors", "--check"]
    )

    assert "Docs skill mirror mismatch: demo/SKILL.md" in issues
    assert exit_code == 1
    assert mirror.read_bytes() == before
