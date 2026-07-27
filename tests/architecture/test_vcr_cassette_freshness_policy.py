"""VCR cassette freshness / LFS preflight policy guard (#6645)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

pytestmark = pytest.mark.architecture

_REPO = Path(__file__).resolve().parents[2]
_POLICY = _REPO / "configs/quality/vcr_cassette_freshness_policy.yaml"
_VCR_HELPER = _REPO / "tests/helpers/vcr_config.py"


def test_vcr_cassette_freshness_policy_is_complete() -> None:
    payload = yaml.safe_load(_POLICY.read_text(encoding="utf-8"))
    assert payload["lfs_pointer_preflight"]["enabled"] is True
    assert payload["lfs_pointer_preflight"]["reason_code"] == "vcr_lfs_pointer"
    assert (
        "unit-fast"
        in payload["lfs_pointer_preflight"]["forbid_live_network_fallback_in"]
    )
    assert (_REPO / payload["cassette_root"]).is_dir()
    helper_source = _VCR_HELPER.read_text(encoding="utf-8")
    assert "is_git_lfs_pointer" in helper_source or "lfs" in helper_source.lower()
