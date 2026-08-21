from __future__ import annotations

import json
import os
import stat
import time
from pathlib import Path

import pytest

from scripts.ai.codex import local_state_audit

pytestmark = pytest.mark.unit


def _seed_home(tmp_path: Path) -> Path:
    home = tmp_path / ".codex"
    rules = home / "rules"
    sessions = home / "sessions"
    rules.mkdir(parents=True)
    sessions.mkdir()
    os.chmod(home, 0o755)
    os.chmod(rules, 0o755)
    os.chmod(sessions, 0o755)
    rule_file = rules / "default.rules"
    rule_file.write_text(
        "# sample\n"
        'prefix_rule(pattern=["git", "status"], decision="allow")\n'
        'prefix_rule(pattern=["bash", "-lc"], decision="allow")\n'
        'prefix_rule(pattern=["curl", "api_key=fake-test-value"], decision="allow")\n',
        encoding="utf-8",
    )
    os.chmod(rule_file, 0o644)
    session = sessions / "rollout-00000000-0000-0000-0000-000000000001.jsonl"
    session.write_text('{"sample": true}\n', encoding="utf-8")
    os.chmod(session, 0o644)
    return home


def test_audit_reports_aggregate_categories_without_sensitive_content(
    tmp_path: Path,
) -> None:
    home = _seed_home(tmp_path)
    profile = home / "balanced.config.toml"
    profile.write_text('model = "fixture"\n', encoding="utf-8")
    os.chmod(profile, 0o644)

    report = local_state_audit.collect_audit(home, retention_days=90)
    rendered = json.dumps(report)

    assert report["rules"]["rules"] == 3
    assert report["rules"]["dispositions"]["KEEP"] == 1
    assert report["rules"]["dispositions"]["REMOVE"] == 1
    assert report["rules"]["dispositions"]["SECRET_REVIEW"] == 1
    assert report["permissions"]["unsafe_files"] >= 3
    assert "fake-test-value" not in rendered
    assert "default.rules" not in rendered
    assert report["privacy"] == {
        "rule_content_emitted": False,
        "session_content_read": False,
        "credentials_emitted": False,
        "user_paths_emitted": False,
        "env_files_touched": False,
    }


def test_remediation_backup_and_restore_on_non_sensitive_sample(
    tmp_path: Path,
) -> None:
    home = _seed_home(tmp_path)
    original = (home / "rules/default.rules").read_text(encoding="utf-8")
    backup = home / "backups/codex-opt-sample"

    result = local_state_audit.apply_remediation(home, backup)

    assert result["backup"]["verified"] is True
    assert result["rules"]["before"] == 3
    assert result["rules"]["after"] == 1
    if os.name != "nt":
        assert result["permissions"]["unsafe_after"] == 0
        assert stat.S_IMODE(home.stat().st_mode) == 0o700
        assert stat.S_IMODE((home / "sessions").stat().st_mode) == 0o700
        assert (
            stat.S_IMODE((home / "sessions").iterdir().__next__().stat().st_mode)
            == 0o600
        )

    restored = local_state_audit.restore_backup(home, backup)

    assert restored["checksums_verified"] is True
    assert (home / "rules/default.rules").read_text(encoding="utf-8") == original
    if os.name != "nt":
        assert stat.S_IMODE(home.stat().st_mode) == 0o755
        assert stat.S_IMODE((home / "rules/default.rules").stat().st_mode) == 0o644


def test_retention_inventory_uses_metadata_only_and_classifies_age(
    tmp_path: Path,
) -> None:
    home = _seed_home(tmp_path)
    sessions = home / "sessions"
    old = sessions / "rollout-00000000-0000-0000-0000-000000000002.jsonl"
    old.write_text("old sample\n", encoding="utf-8")
    now = time.time()
    os.utime(old, (now - 100 * 86_400, now - 100 * 86_400))

    report = local_state_audit.audit_retention(home, retention_days=90, now=now)
    rendered = json.dumps(report)

    assert report["groups"]["KEEP"]["count"] == 1
    assert report["groups"]["ARCHIVE"]["count"] == 1
    assert report["session_content_read"] is False
    assert report["deletion_performed"] is False
    assert "old sample" not in rendered
    assert old.name not in rendered


def test_backup_rejects_target_outside_private_codex_backup_root(
    tmp_path: Path,
) -> None:
    home = _seed_home(tmp_path)

    with pytest.raises(ValueError, match="under the Codex backups directory"):
        local_state_audit.create_backup(home, tmp_path / "unsafe-backup")


def test_restore_rejects_backup_outside_private_codex_backup_root(
    tmp_path: Path,
) -> None:
    home = _seed_home(tmp_path)

    with pytest.raises(ValueError, match="under the Codex backups directory"):
        local_state_audit.restore_backup(home, tmp_path / "unsafe-backup")


@pytest.mark.parametrize(
    "candidate",
    (
        "/tmp/job.py",
        "/var/tmp/job.py",
        r"C:\\Users\\runner\\AppData\\Local\\Temp\\job.py",
    ),
)
def test_rule_classifier_rejects_temporary_path_tokens(candidate: str) -> None:
    assert local_state_audit._rule_class(["python", candidate], "allow") == (
        "REMOVE",
        "temporary_path",
    )
