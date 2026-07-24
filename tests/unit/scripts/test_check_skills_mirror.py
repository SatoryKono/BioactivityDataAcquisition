"""Repository-backed test for the Codex/Devin skill mirror contract."""

from __future__ import annotations

from pathlib import Path

import pytest

from scripts.ai import sync_ai_governance


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]
ROOT = Path(__file__).resolve().parents[3]


@pytest.mark.timeout(180)
def test_repository_skill_parity_contract_passes() -> None:
    """Exercise canonical runtime parity without a nested Python subprocess."""
    contract = sync_ai_governance._load_skills_mirror_contract(ROOT)
    paths = sync_ai_governance._contract_paths(ROOT, contract)
    issues = sync_ai_governance._validate_codex_devin_parity(paths, contract)

    assert issues == []
