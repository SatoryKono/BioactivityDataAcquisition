"""LA-15 dashboard hygiene: slug backlinks, empty states, numbering, latency."""

from __future__ import annotations

import pytest
from pathlib import Path

pytestmark = pytest.mark.unit

from scripts.ops.observability.grafana.apply_phase25_srs_prr_budget import (
    _CHECKPOINT_EMPTY_ROWS,
    _OV_EXCL,
    _OV_RECON,
    _assert_donor_jsonata_balanced,
)
from scripts.ops.observability.grafana.dashboard_context_links import (
    DASHBOARD_TITLES,
    PATH_BY_UID,
    grafana_dashboard_slug,
)

_ROOT = Path(__file__).resolve().parents[5]
_ACTIVE_SURFACES = (
    _ROOT / "grafana" / "dashboards",
    _ROOT / "scripts" / "ops" / "observability" / "grafana",
)


def test_donor_jsonata_stays_balanced() -> None:
    _assert_donor_jsonata_balanced()


def test_empty_states_name_a_reason() -> None:
    for expression in (_CHECKPOINT_EMPTY_ROWS, _OV_EXCL, _OV_RECON):
        assert "не применимо" in expression
        assert "нет записей" in expression
        assert "нет данных" in expression
    assert "selected_run_id != null" in _CHECKPOINT_EMPTY_ROWS
    assert "$append($listed" in _CHECKPOINT_EMPTY_ROWS
    assert "no Run ID selected" in _CHECKPOINT_EMPTY_ROWS
    assert "checkpoint anchors were not recorded" in _CHECKPOINT_EMPTY_ROWS
    assert "checkpoint comparison returned no rows" in _CHECKPOINT_EMPTY_ROWS
    assert "excluded UNKNOWN" in _OV_EXCL
    assert "FK comparison rows were not returned" in _OV_RECON


def test_canonical_titles_are_numbered_one_through_five() -> None:
    expected = {
        "bioetl-run-explorer-v1": ("1. Run Explorer", "1-run-explorer"),
        "bioetl-control-plane-v1": ("2. Replay Readiness", "2-replay-readiness"),
        "bioetl-overview-v2": ("3. Run Overview", "3-run-overview"),
        "bioetl-dq-v2": ("4. Data Quality", "4-data-quality"),
        "bioetl-incident-v1": ("5. Incident Workspace", "5-incident-workspace"),
    }
    assert set(DASHBOARD_TITLES) == set(expected)
    for uid, (title, slug) in expected.items():
        assert DASHBOARD_TITLES[uid] == title
        assert grafana_dashboard_slug(title) == slug
        assert PATH_BY_UID[uid] == slug
        assert not title.startswith("6.")


def test_active_surfaces_do_not_link_the_residual_replay_slug() -> None:
    """Isolated 100000 and the retired 1-trust slug are not navigation targets."""
    needles = ("bioetl-isolated-replay-100000", "/1-trust", "/6-incident-workspace")
    offenders: list[str] = []
    for surface in _ACTIVE_SURFACES:
        for path in surface.rglob("*"):
            if path.suffix not in {".py", ".json", ".yaml", ".yml", ".md"}:
                continue
            text = path.read_text(encoding="utf-8")
            for needle in needles:
                if needle in text:
                    offenders.append(f"{path.relative_to(_ROOT)}:{needle}")
    assert offenders == []
