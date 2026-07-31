"""Tests for approved multi-runtime skill synchronization."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.ai import runtime_skill_sync

pytestmark = pytest.mark.unit


def _fixture(root: Path) -> None:
    contract = root / "scripts/ai/codex/skills-mirror-contract.json"
    contract.parent.mkdir(parents=True)
    contract.write_text(
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
                    "optional_presence_globs": ["*/agents/openai.yaml"],
                    "allowed_content_variant_globs": ["*/SKILL.md"],
                    "required_identical_when_shared_globs": ["*/references/**"],
                },
            }
        ),
        encoding="utf-8",
    )
    for runtime, skill_text, ref_text in (
        (".codex", "codex\n", "canonical\n"),
        (".devin", "devin adaptation\n", "stale\n"),
    ):
        skill = root / runtime / "skills/demo"
        (skill / "references").mkdir(parents=True)
        (skill / "SKILL.md").write_text(skill_text, encoding="utf-8")
        (skill / "references/shared.md").write_text(ref_text, encoding="utf-8")
        (root / runtime / "skills/SKILLS-CATALOG.md").write_text(
            "[demo](demo/SKILL.md)\n", encoding="utf-8"
        )
    (root / "docs/00-project/ai/skills/_references/local").mkdir(parents=True)


def test_sync_devin_preserves_runtime_variant_and_updates_reference(
    tmp_path: Path,
) -> None:
    _fixture(tmp_path)
    drift, contract = runtime_skill_sync._devin_drift(tmp_path)
    assert drift == [
        {"runtime": "devin", "change": "modified", "path": "demo/references/shared.md"}
    ]

    synced = runtime_skill_sync._sync_devin(tmp_path, contract)

    assert synced == ["demo/references/shared.md"]
    assert (
        tmp_path / ".devin/skills/demo/SKILL.md"
    ).read_text() == "devin adaptation\n"
    assert (
        tmp_path / ".devin/skills/demo/references/shared.md"
    ).read_text() == "canonical\n"


def test_sync_devin_copies_missing_required_file(tmp_path: Path) -> None:
    _fixture(tmp_path)
    source = tmp_path / ".codex/skills/demo/references/new.md"
    source.write_text("new\n", encoding="utf-8")
    _, contract = runtime_skill_sync._devin_drift(tmp_path)

    runtime_skill_sync._sync_devin(tmp_path, contract)

    assert (tmp_path / ".devin/skills/demo/references/new.md").read_text() == "new\n"
