"""Hook discovery must not execute repository-controlled code."""

from __future__ import annotations

import json
import io
from pathlib import Path
import subprocess

import pytest

from scripts.ai.codex import hook_inventory as inventory

pytestmark = pytest.mark.unit


def test_launcher_and_stale_metadata_do_not_establish_version(tmp_path: Path) -> None:
    """A launcher plus a package version cannot attest the selected binary."""
    launcher = tmp_path / "codex.cmd"
    launcher.write_text("exit /b 99", encoding="utf-8")
    (tmp_path / "package.json").write_text('{"version":"999.0"}', encoding="utf-8")
    result = inventory.runtime_inventory(tmp_path, "codex", str(launcher))
    assert result["version"] is None
    assert result["capability_status"] == "NOT_PROVEN"
    assert not result["enabled_by_diagnostic"]


def test_configured_hook_is_not_execution_proof(tmp_path: Path) -> None:
    """Observed event definitions remain unexecuted and version-unqualified."""
    path = tmp_path / ".devin/hooks.v1.json"
    path.parent.mkdir()
    path.write_text(json.dumps({"PreToolUse": [{"hooks": [{"command": "never-run"}]}]}))
    result = inventory.runtime_inventory(tmp_path, "devin", None)
    assert result["configured_events"] == ["PreToolUse"]
    assert result["version_status"] == "MISSING"
    assert result["execution"] == "NOT_PROVEN"


def test_invalid_config_is_error_without_contents(tmp_path: Path) -> None:
    """Parser failures must not expose secret-bearing input contents."""
    config = tmp_path / ".junie/config.json"
    config.parent.mkdir()
    config.write_text("secret-invalid-content")
    result = inventory.runtime_inventory(tmp_path, "junie", None)
    assert result["config_status"] == "ERROR"
    assert "secret-invalid-content" not in json.dumps(result)


def test_git_query_failure_is_not_pass(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Unavailable metadata cannot be promoted to a successful discovery."""

    def fail(*args: object, **kwargs: object) -> str:
        raise subprocess.TimeoutExpired("git", 3)

    monkeypatch.setattr(inventory, "_git", fail)
    assert inventory.git_inventory(tmp_path)["status"] == "ERROR"


def test_collect_never_executes_runtime(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Commands resolved from PATH are data, never executable probes."""
    monkeypatch.setattr(inventory.shutil, "which", lambda name: "/untrusted/" + name)
    monkeypatch.setattr(inventory, "git_inventory", lambda root: {"status": "OBSERVED"})

    def forbidden(*args: object, **kwargs: object) -> None:
        pytest.fail("runtime or hook execution attempted")

    monkeypatch.setattr(inventory.subprocess, "run", forbidden)
    result = inventory.collect(tmp_path)
    assert result["status"] == "NOT_PROVEN"
    assert len(result["runtimes"]) == 4


def test_effective_git_directory_is_used(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Sample hooks in an effective directory are not installed hooks."""
    hooks = tmp_path / "shared-hooks"
    hooks.mkdir()
    (hooks / "pre-commit.sample").write_text("sample")
    monkeypatch.setattr(inventory, "_git", lambda *args: str(hooks))
    result = inventory.git_inventory(tmp_path)
    assert result["directory"] == str(hooks.resolve())
    assert not any(hook["discoverable"] for hook in result["hooks"])


@pytest.mark.parametrize(
    "runtime,suffix,text",
    [
        (
            "codex",
            "toml",
            '[[hooks.Stop]]\n[[hooks.Stop.hooks]]\ntype="command"\ncommand="never-run"\n',
        ),
        ("devin", "json", '{"hooks":{"Stop":[{"hooks":[{"command":"never-run"}]}]}}'),
    ],
)
def test_inline_only_events_retain_origin(
    tmp_path: Path, runtime: str, suffix: str, text: str
) -> None:
    """Inline events must remain visible without a standalone hooks file."""
    path = tmp_path / f".{runtime}/config.{suffix}"
    path.parent.mkdir()
    path.write_text(text)
    result = inventory.runtime_inventory(tmp_path, runtime, None)
    assert result["configured_events"] == ["Stop"]
    assert result["event_sources"] == {"Stop": [str(path)]}
    assert result["execution"] == "NOT_PROVEN"


def test_jsonc_is_discovered_without_claiming_plugins_absent(tmp_path: Path) -> None:
    """Unsupported JSONC is fingerprinted and reported as incomplete evidence."""
    path = tmp_path / "opencode.jsonc"
    path.write_text('{ // comment\n"plugins":["never-install"]\n}')
    result = inventory.runtime_inventory(tmp_path, "opencode", None)
    assert result["config_status"] == "INCOMPLETE"
    assert result["plugins_configured"] is None
    item = result["additional_configurations"][0]
    assert item["present"] and item["sha256"]
    assert item["parse_status"] == "UNSUPPORTED"


def test_inline_and_file_events_keep_both_origins(tmp_path: Path) -> None:
    """Standalone discovery must not replace inline definitions of an event."""
    folder = tmp_path / ".devin"
    folder.mkdir()
    inline = folder / "config.json"
    standalone = folder / "hooks.v1.json"
    inline.write_text('{"hooks":{"Stop":[]}}')
    standalone.write_text('{"Stop":[],"PreToolUse":[]}')
    result = inventory.runtime_inventory(tmp_path, "devin", None)
    assert result["configured_events"] == ["PreToolUse", "Stop"]
    assert result["event_sources"]["Stop"] == sorted([str(inline), str(standalone)])


def test_bad_primary_config_does_not_hide_jsonc(tmp_path: Path) -> None:
    """An invalid primary format must not hide another discovered source."""
    (tmp_path / "opencode.json").write_text("invalid")
    (tmp_path / "opencode.jsonc").write_text("{}")
    result = inventory.runtime_inventory(tmp_path, "opencode", None)
    assert result["config_status"] == "ERROR"
    assert result["additional_configurations"][0]["present"]


def test_read_limit_applies_to_stream_not_prior_stat(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """A concurrently grown file must not cause an unbounded allocation."""
    sizes = []

    class Stream(io.BytesIO):
        def read(self, size: int = -1) -> bytes:
            """Record the requested maximum instead of serving an entire file."""
            sizes.append(size)
            return super().read(size)

    monkeypatch.setattr(
        Path, "open", lambda *args, **kwargs: Stream(b"x" * (inventory.MAX_BYTES + 10))
    )
    with pytest.raises(ValueError, match="size limit"):
        inventory._read_bytes(tmp_path / "growing.json")
    assert sizes == [inventory.MAX_BYTES + 1]


@pytest.mark.parametrize("broken", ["config.json", "hooks.v1.json"])
def test_independent_devin_sources_survive_other_source_failure(
    tmp_path: Path, broken: str
) -> None:
    """A malformed source cannot hide events from the other valid file."""
    folder = tmp_path / ".devin"
    folder.mkdir()
    inline, standalone = folder / "config.json", folder / "hooks.v1.json"
    inline.write_text('{"hooks":{"Stop":[]}}')
    standalone.write_text('{"PreToolUse":[]}')
    (folder / broken).write_text("invalid-private-parser-input")
    result = inventory.runtime_inventory(tmp_path, "devin", None)
    event, valid = (
        ("PreToolUse", standalone) if broken == "config.json" else ("Stop", inline)
    )
    assert result["configured_events"] == [event]
    assert result["event_sources"] == {event: [str(valid)]}
    assert result["source_parse_status"][str(folder / broken)] == "ERROR"
    assert result["source_parse_status"][str(valid)] == "OBSERVED"
    assert result["config_status"] == "ERROR"
    assert result["execution"] == "NOT_PROVEN"
    assert "invalid-private-parser-input" not in json.dumps(result)
