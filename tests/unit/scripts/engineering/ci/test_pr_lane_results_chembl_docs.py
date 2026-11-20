"""Provider reference changes keep their documentation and Molecule contracts."""

from pathlib import Path

import pytest

from scripts.engineering.ci.pr_lane_results import build_shadow_compare

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "path",
    [
        "docs/04-reference/providers/chembl/molecule.md",
        "docs/05-operations/runbooks/chembl_molecule-phase-recovery.md",
    ],
)
def test_chembl_molecule_reference_selects_owned_contracts(path: str) -> None:
    root = Path(__file__).resolve().parents[5]
    report = build_shadow_compare([path], repo_root=root)
    assert report["activation"] == "not_applied"
    assert report["covers_full_suite"] is False
    assert {
        "tests/architecture/test_documentation_sync.py",
        "tests/architecture/test_documentation_cleanup_inventory.py",
        "tests/e2e/test_chembl_molecule_e2e.py",
        "tests/e2e/test_chembl_molecule_cached_e2e.py",
    } <= set(report["selected"])


@pytest.mark.parametrize(
    "path",
    [
        "docs/04-reference/providers/unknown/unknown.md",
        "docs/05-operations/runbooks/unknown-recovery.md",
    ],
)
def test_unknown_provider_reference_still_fails_closed(path: str) -> None:
    root = Path(__file__).resolve().parents[5]
    with pytest.raises(ValueError, match="unmapped paths"):
        build_shadow_compare([path], repo_root=root)
