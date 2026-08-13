from __future__ import annotations

import json
import stat
import sys
from pathlib import Path

import pytest

from scripts.ai.codex import profile_config

pytestmark = pytest.mark.unit


def _write_sample(codex_home: Path) -> None:
    codex_home.mkdir()
    (codex_home / "config.toml").write_text(
        'model = "old"\n'
        'model_reasoning_effort = "max"\n\n'
        "[mcp_servers.sample]\n"
        'bearer_token = "must-not-leak"\n',
        encoding="utf-8",
    )
    (codex_home / "fast.config.toml").write_text(
        'model = "old-fast"\nmodel_reasoning_effort = "low"\n',
        encoding="utf-8",
    )
    (codex_home / "deep.config.toml").write_text(
        'model = "old-deep"\nmodel_reasoning_effort = "xhigh"\n',
        encoding="utf-8",
    )


def test_apply_profiles_is_private_backed_up_and_restorable(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    _write_sample(codex_home)
    original = (codex_home / "config.toml").read_text(encoding="utf-8")
    backup = codex_home / "backups" / "profile-test"

    result = profile_config.apply_profiles(codex_home, backup)

    assert result["backup"]["verified"] is True
    assert result["all_profiles_match"] is True
    assert result["agents_max_threads_changed"] is False
    if sys.platform != "win32":
        assert stat.S_IMODE(backup.stat().st_mode) == 0o700
        assert all(
            stat.S_IMODE((codex_home / filename).stat().st_mode) == 0o600
            for filename, _profile in profile_config.PROFILE_FILES.values()
        )
    assert "must-not-leak" in (codex_home / "config.toml").read_text(encoding="utf-8")

    restored = profile_config.restore_profiles(codex_home, backup)

    assert restored == {
        "restored_files": 3,
        "removed_new_files": 1,
        "checksums_verified": True,
        "env_files_touched": False,
    }
    assert (codex_home / "config.toml").read_text(encoding="utf-8") == original
    assert not (codex_home / "balanced.config.toml").exists()


def test_audit_emits_only_allowlisted_profile_fields(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    _write_sample(codex_home)

    rendered = json.dumps(profile_config.audit_profiles(codex_home))

    assert "must-not-leak" not in rendered
    assert str(tmp_path) not in rendered
    assert '"credentials_emitted": false' in rendered
    assert '"env_files_touched": false' in rendered


def test_backup_must_stay_under_codex_home(tmp_path: Path) -> None:
    codex_home = tmp_path / ".codex"
    _write_sample(codex_home)

    with pytest.raises(ValueError, match="under the Codex backups"):
        profile_config.create_backup(codex_home, tmp_path / "outside")
