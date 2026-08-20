# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Unit tests for AI governance sync script."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ai.sync import governance as sync_ai_governance

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


def test_normalize_codex_agents_does_not_inject_retired_role_memory(
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
    assert "memory-py-test-swarm.md" not in path.read_text(encoding="utf-8")


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


def test_inject_docs_agent_sources_syncs_canonical_runtime_body(
    tmp_path: Path,
) -> None:
    canonical = tmp_path / ".codex/agents/demo.md"
    canonical.parent.mkdir(parents=True)
    canonical.write_text("# Demo\n\ncanonical body\n", encoding="utf-8")
    mirror = tmp_path / "docs/00-project/ai/agents/agents/demo.md"
    mirror.parent.mkdir(parents=True)
    mirror.write_text("stale body\n", encoding="utf-8")

    issues = sync_ai_governance.inject_docs_agent_sources(tmp_path, check_only=False)

    assert issues == []
    text = mirror.read_text(encoding="utf-8")
    assert "not a canonical runtime surface" in text
    assert ".codex/agents/demo.md" in text
    assert text.endswith("# Demo\n\ncanonical body\n")


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
                "## Source Of Truth",
                "",
                "- Root runtime contract: `../../../AGENTS.md`",
                "- Project rules: `../../../docs/00-project/RULES.md`",
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
    assert "- Root runtime contract: `../../../AGENTS.md`" not in text.splitlines()
    assert (
        "- Project rules: `../../../docs/00-project/RULES.md`" not in text.splitlines()
    )
    assert (
        "- Post-change validation: `../../../agents/policy/POST_CHANGE_VALIDATION.md`"
        "\n\n## Workflow"
    ) in text

    before = text
    assert sync_ai_governance.sync_docs_skill_mirrors(tmp_path, check_only=False) == []
    assert path.read_text(encoding="utf-8") == before


def test_thin_exact_duplicate_license_clones_collapses_identical_bodies(
    tmp_path: Path,
) -> None:
    skill_a = tmp_path / "a"
    skill_b = tmp_path / "b"
    skill_a.mkdir()
    skill_b.mkdir()
    body = "Apache-2.0 sample license body\n"
    (skill_a / "LICENSE.txt").write_text(body, encoding="utf-8")
    (skill_b / "LICENSE.txt").write_text(body, encoding="utf-8")

    thinned = sync_ai_governance.thin_exact_duplicate_license_clones(tmp_path)

    assert thinned == 2
    store = list((tmp_path / "_licenses").glob("license-text-*.txt"))
    assert len(store) == 1
    assert store[0].read_text(encoding="utf-8") == body
    pointer = (skill_a / "LICENSE.txt").read_text(encoding="utf-8")
    assert pointer.startswith("# License text (thin mirror)")
    assert "_licenses/" in pointer
    assert (
        (skill_b / "LICENSE.txt")
        .read_text(encoding="utf-8")
        .startswith("# License text (thin mirror)")
    )


def test_skills_mirror_reports_missing_devin_entrypoint(tmp_path: Path) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    (tmp_path / ".devin/skills/demo/SKILL.md").unlink()

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)

    assert "Devin missing skill entrypoint: demo/SKILL.md" in issues


def test_skills_mirror_reports_missing_root_without_traceback(tmp_path: Path) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    devin_root = tmp_path / ".devin/skills"
    for path in sorted(devin_root.rglob("*"), reverse=True):
        if path.is_file():
            path.unlink()
        else:
            path.rmdir()
    devin_root.rmdir()

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)

    assert issues == [f"Devin skills root missing: {devin_root.resolve()}"]


def test_skills_mirror_rejects_contract_path_traversal(tmp_path: Path) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    contract_path = tmp_path / sync_ai_governance.SKILLS_MIRROR_CONTRACT_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["roots"]["docs_mirror"] = "../outside"
    contract_path.write_text(json.dumps(contract) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="repository-relative without '\\.\\.'"):
        sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=False)

    assert not (tmp_path.parent / "outside").exists()


def test_skills_mirror_rejects_destructive_root_overlap(tmp_path: Path) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    contract_path = tmp_path / sync_ai_governance.SKILLS_MIRROR_CONTRACT_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["roots"]["docs_mirror"] = ".codex"
    contract_path.write_text(json.dumps(contract) + "\n", encoding="utf-8")

    with pytest.raises(ValueError, match="docs_mirror must not overlap canonical"):
        sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=False)

    assert (tmp_path / ".codex/skills/demo/SKILL.md").is_file()


def test_skills_mirror_reports_unexpected_devin_entrypoint(tmp_path: Path) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    unexpected = tmp_path / ".devin/skills/unexpected/SKILL.md"
    unexpected.parent.mkdir(parents=True)
    unexpected.write_text("# Unexpected\n", encoding="utf-8")

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)

    assert "Devin unexpected skill entrypoint: unexpected/SKILL.md" in issues


def test_skills_mirror_accepts_optional_devin_entrypoint_file_glob(
    tmp_path: Path,
) -> None:
    _seed_skills_mirror_fixture(tmp_path)
    contract_path = tmp_path / sync_ai_governance.SKILLS_MIRROR_CONTRACT_PATH
    contract = json.loads(contract_path.read_text(encoding="utf-8"))
    contract["codex_devin"]["optional_presence_globs"] = [
        "*/agents/openai.yaml",
        "*/references/**",
        "coderabbit-audit/*",
    ]
    contract["codex_devin"]["allowed_content_variant_globs"].append(
        "coderabbit-audit/*"
    )
    contract_path.write_text(json.dumps(contract) + "\n", encoding="utf-8")
    optional = tmp_path / ".devin/skills/coderabbit-audit/SKILL.md"
    optional.parent.mkdir(parents=True)
    optional.write_text("# Optional Devin skill\n", encoding="utf-8")

    issues = sync_ai_governance.sync_skill_mirrors(tmp_path, check_only=True)

    assert not any("coderabbit-audit" in issue for issue in issues)


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


def test_main_defaults_to_check_only(tmp_path: Path) -> None:
    """Bare CLI must not write Codex agent files (#9119)."""
    agents = tmp_path / ".codex" / "agents"
    agents.mkdir(parents=True)
    target = agents / "py-audit-bot.md"
    original = "# Agent\n\nBody\n"
    target.write_text(original, encoding="utf-8")

    exit_code = sync_ai_governance.main(
        ["--root", str(tmp_path), "--only", "codex-agents"]
    )

    assert exit_code == 1
    assert target.read_text(encoding="utf-8") == original
