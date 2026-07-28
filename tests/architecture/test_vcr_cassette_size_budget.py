"""Guard VCR cassette growth (T-TEST-005 / #6776)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_BUDGET = _REPO / "configs/quality/vcr_cassette_size_budget.yaml"
_VCR_ROOT = _REPO / "tests/fixtures/vcr"


def _load_budget() -> dict[str, object]:
    payload = yaml.safe_load(_BUDGET.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


@pytest.mark.architecture
def test_vcr_cassette_size_budget_blocks_new_oversized_cassettes() -> None:
    """New cassettes must stay under the budget unless explicitly allowlisted."""
    budget = _load_budget()
    policy = budget["policy"]
    assert isinstance(policy, dict)
    max_bytes = int(policy["max_new_cassette_bytes"])
    allowlist = {
        str(entry["path"]).replace("\\", "/")
        for entry in policy.get("allowlist_oversized", [])
        if isinstance(entry, dict) and "path" in entry
    }

    oversized: list[str] = []
    for cassette in sorted(_VCR_ROOT.rglob("*.yaml")):
        rel = cassette.relative_to(_REPO).as_posix()
        size = cassette.stat().st_size
        if size > max_bytes and rel not in allowlist:
            oversized.append(f"{rel} ({size} bytes)")

    assert not oversized, (
        "Oversized VCR cassettes without allowlist entry "
        f"(budget={max_bytes} bytes):\n" + "\n".join(oversized)
    )


@pytest.mark.architecture
def test_vcr_allowlist_paths_exist() -> None:
    """Allowlisted oversized cassettes must still exist until re-record."""
    budget = _load_budget()
    policy = budget["policy"]
    assert isinstance(policy, dict)
    missing: list[str] = []
    for entry in policy.get("allowlist_oversized", []):
        if not isinstance(entry, dict):
            continue
        rel = str(entry["path"])
        if not (_REPO / rel).is_file():
            missing.append(rel)
    assert not missing, f"Allowlisted cassettes missing: {missing}"
