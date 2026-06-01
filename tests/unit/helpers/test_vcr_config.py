from __future__ import annotations

import pytest

from tests.helpers.vcr_config import build_base_vcr_config, is_vcr_recording_mode


pytestmark = pytest.mark.unit

def test_is_vcr_recording_mode_uses_env(monkeypatch) -> None:
    monkeypatch.setenv("VCR_RECORD_MODE", "new_episodes")
    monkeypatch.setattr("sys.argv", ["pytest"])

    assert is_vcr_recording_mode() is True


def test_is_vcr_recording_mode_detects_cli_flag(monkeypatch) -> None:
    monkeypatch.delenv("VCR_RECORD_MODE", raising=False)
    monkeypatch.setattr(
        "sys.argv",
        ["pytest", "tests/e2e/test_pubchem_compound_e2e.py", "--vcr-record=all"],
    )

    assert is_vcr_recording_mode() is True


def test_is_vcr_recording_mode_defaults_to_replay(monkeypatch) -> None:
    monkeypatch.delenv("VCR_RECORD_MODE", raising=False)
    monkeypatch.setattr("sys.argv", ["pytest"])

    assert is_vcr_recording_mode() is False


def test_build_base_vcr_config_defaults_to_replay_only(monkeypatch) -> None:
    monkeypatch.delenv("VCR_RECORD_MODE", raising=False)

    assert build_base_vcr_config()["record_mode"] == "none"
