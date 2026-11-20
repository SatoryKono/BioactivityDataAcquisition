"""Secret scanning must cover source files independently of Git ignore state."""

from __future__ import annotations

import json
import os
from pathlib import Path
import random
import string
import subprocess
import sys
from types import SimpleNamespace

import pytest

from tests.architecture import test_antipatterns as owner

pytestmark = pytest.mark.unit


def _source_case(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, *, tracked: bool
) -> tuple[Path, Path, str]:
    """Prepare a real scanner with isolated Git metadata and synthetic input."""
    root = tmp_path / "source-scan"
    (root / "src").mkdir(parents=True)
    # A synthetic high-entropy assignment, never an account credential.
    generator = random.Random(13056)
    value = "".join(generator.choices(string.ascii_letters + string.digits, k=64))
    source = root / "src" / "module with spaces.py"
    source.write_text(f"password = {value!r}\n", encoding="utf-8")
    (root / ".gitignore").write_text("src/\n", encoding="utf-8")
    config = root / "empty-gitconfig"
    config.write_text("", encoding="utf-8")
    environment = {
        key: data for key, data in os.environ.items() if not key.startswith("GIT_")
    }
    environment.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=str(config))
    subprocess.run(
        ["git", "init", str(root)], env=environment, check=True, capture_output=True
    )
    if tracked:
        subprocess.run(
            ["git", "-C", str(root), "add", "--force", "--", str(source)],
            env=environment,
            check=True,
            capture_output=True,
        )
    baseline = json.loads((owner.REPO_ROOT / ".secrets.baseline").read_text())
    baseline["results"] = {}
    original = json.dumps(baseline, indent=2) + "\n"
    (root / ".secrets.baseline").write_text(original, encoding="utf-8")
    scratch = root / "scan-state"
    scratch.mkdir()
    monkeypatch.setattr(owner, "REPO_ROOT", root)

    def run(command: list[str], **options: object):
        assert command[:3] == [sys.executable, "-m", "detect_secrets"]
        return subprocess.run(command, env=environment, **options)

    monkeypatch.setattr(owner, "subprocess", SimpleNamespace(run=run))
    return source, scratch, value


@pytest.mark.parametrize("tracked", [False, True])
def test_source_secret_is_rejected_without_mutating_committed_baseline(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, tracked: bool
) -> None:
    """An ignored source secret is as actionable as a tracked source secret."""
    source, scratch, value = _source_case(tmp_path, monkeypatch, tracked=tracked)
    baseline = source.parent.parent / ".secrets.baseline"
    original = baseline.read_bytes()

    with pytest.raises(AssertionError, match="New secret findings") as error:
        owner.test_no_hardcoded_secrets(scratch)
    assert "src/module with spaces.py" in str(error.value)
    assert value not in str(error.value)
    assert baseline.read_bytes() == original


def test_same_temporary_baseline_path_requires_a_fresh_scan(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A previous success cannot hide a new ignored-source secret."""
    source, scratch, value = _source_case(tmp_path, monkeypatch, tracked=False)
    baseline = source.parent.parent / ".secrets.baseline"
    original = baseline.read_bytes()
    source.write_text("safe = 1\n", encoding="utf-8")
    owner.test_no_hardcoded_secrets(scratch)
    source.write_text(f"password = {value!r}\n", encoding="utf-8")

    with pytest.raises(AssertionError, match="New secret findings") as error:
        owner.test_no_hardcoded_secrets(scratch)
    assert value not in str(error.value)
    assert baseline.read_bytes() == original
