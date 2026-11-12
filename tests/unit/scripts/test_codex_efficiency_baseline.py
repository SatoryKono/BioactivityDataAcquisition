from __future__ import annotations

import json
import subprocess
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.ai.codex import efficiency_baseline

pytestmark = pytest.mark.unit


def test_collect_baseline_is_bounded_and_secret_free(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(argv: list[str], **kwargs: object) -> SimpleNamespace:
        calls.append((argv, kwargs))
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(efficiency_baseline.time, "monotonic", lambda: 1.0)

    report = efficiency_baseline.collect_baseline(
        root=tmp_path,
        runs=3,
        timeout_seconds=5,
    )

    assert report["schema_version"] == "bioetl-codex-efficiency-baseline-v1"
    assert report["policy"] == {
        "runs": 3,
        "timeout_seconds": 5,
        "captures_subprocess_output": False,
        "starts_optional_services": False,
    }
    assert len(calls) == 15
    assert all(kwargs["timeout"] == 5 for _, kwargs in calls)
    assert all(kwargs["stdout"] is subprocess.DEVNULL for _, kwargs in calls)
    assert all(kwargs["stderr"] is subprocess.DEVNULL for _, kwargs in calls)
    expected_mcp_suffix = ["mcp-static"]
    assert all(
        argv[-len(expected_mcp_suffix) :] == expected_mcp_suffix
        for argv, _ in calls[-3:]
    )
    rendered = json.dumps(report)
    assert "OPENAI_API_KEY" not in rendered
    assert "GITHUB_TOKEN" not in rendered


def test_run_probe_reports_timeout_without_output(monkeypatch, tmp_path: Path) -> None:
    def fake_run(*args: object, **kwargs: object) -> None:
        raise subprocess.TimeoutExpired(["codex"], timeout=1)

    monkeypatch.setattr(subprocess, "run", fake_run)
    report = efficiency_baseline._run_probe(
        "probe",
        ["codex", "--version"],
        root=tmp_path,
        timeout_seconds=1,
    )

    assert report["status"] == "timed_out"
    assert report["returncode"] is None


def test_offline_snapshot_excludes_secrets_and_never_calls_probes(
    monkeypatch, tmp_path
):
    sha = "a" * 40
    objects = {"1" * 40: b"private prompt marker\r\n", "2" * 40: b"shared\n"}
    records = [
        ("100644", "1" * 40, ".codex/skills/demo/SKILL.md"),
        ("100644", "2" * 40, "AGENTS.md"),
        ("100644", "3" * 40, ".codex/skills/demo/.env.example"),
        ("100644", "4" * 40, ".codex/skills/.env/private.md"),
        ("100644", "5" * 40, ".codex/skills/demo/image.png"),
        ("120000", "6" * 40, ".codex/skills/demo/link.md"),
    ]
    calls = []

    def git(root, *args, data=None):
        calls.append(args[0])
        if args[0] == "rev-parse":
            return (sha + "\n").encode()
        if args[0] == "ls-tree":
            return b"".join(
                f"{mode} blob {oid}\t{path}\0".encode() for mode, oid, path in records
            )
        assert args == ("cat-file", "--batch")
        requested = data.decode().splitlines()
        assert set(requested) == objects.keys()
        return b"".join(
            f"{oid} blob {len(objects[oid])}\n".encode() + objects[oid] + b"\n"
            for oid in requested
        )

    monkeypatch.setattr(efficiency_baseline, "_local_git", git)
    monkeypatch.setattr(
        efficiency_baseline, "_probe_commands", lambda *_: pytest.fail("No probes")
    )
    report = efficiency_baseline.compare_instructions(tmp_path, sha, sha)
    assert report["changes"] == []
    assert report["baseline"]["groups"]["codex"] == {
        "files": 1,
        "bytes_lf": 22,
        "lines": 1,
    }
    assert report["after"] == report["baseline"]
    assert set(calls) == {"rev-parse", "ls-tree", "cat-file"}
    assert set(report["runtime_metrics"].values()) == {"NOT_MEASURED"}
    assert "private prompt marker" not in json.dumps(report)
    assert str(tmp_path) not in json.dumps(report)


def test_offline_lf_normalization_and_change_metadata(monkeypatch, tmp_path):
    baseline, after = "a" * 40, "b" * 40
    state = {}

    def git(root, *args, data=None):
        if args[0] == "rev-parse":
            state["sha"] = args[-1].split("^")[0]
            return (state["sha"] + "\n").encode()
        if args[0] == "ls-tree":
            return f"100644 blob {'1' * 40}\t.devin/skills/demo/SKILL.md\0".encode()
        blob = b"same\r\n" if state["sha"] == baseline else b"same\n"
        return f"{'1' * 40} blob {len(blob)}\n".encode() + blob + b"\n"

    monkeypatch.setattr(efficiency_baseline, "_local_git", git)
    report = efficiency_baseline.compare_instructions(tmp_path, baseline, after)
    assert report["changes"] == []
    assert report["baseline"]["groups"] == report["after"]["groups"]


@pytest.mark.parametrize("ref", ["HEAD", "--help", "a\n--force", "a" * 39])
def test_offline_rejects_nonimmutable_refs_before_git(monkeypatch, tmp_path, ref):
    monkeypatch.setattr(
        efficiency_baseline, "_local_git", lambda *_a, **_k: pytest.fail("No Git")
    )
    with pytest.raises(ValueError, match="full local commit SHA"):
        efficiency_baseline.instruction_snapshot(tmp_path, ref)


@pytest.mark.parametrize(
    "path",
    [
        ".env",
        ".env.example",
        ".ENV/receipt.json",
        ".env:stream",
        ".env /receipt.json",
        ".envrc",
        ".ENV-private.md",
        ".environment/receipt.json",
    ],
)
def test_report_output_guard_creates_no_environment_files(tmp_path, path):
    with pytest.raises(ValueError, match="environment"):
        efficiency_baseline._check_output_target(tmp_path / path)
    assert list(tmp_path.iterdir()) == []


def test_git_metadata_environment_is_local_and_bounded(monkeypatch, tmp_path):
    monkeypatch.setenv("GIT_WORK_TREE", "synthetic-redirect")
    calls = []

    def run(argv, **kwargs):
        calls.append((argv, kwargs))
        return SimpleNamespace(stdout=b"metadata")

    monkeypatch.setattr(subprocess, "run", run)
    assert efficiency_baseline._local_git(tmp_path, "rev-parse", "HEAD") == b"metadata"
    argv, kwargs = calls[0]
    assert argv[:4] == ["git", "-c", "gc.auto=0", "-C"]
    assert "GIT_WORK_TREE" not in kwargs["env"]
    assert kwargs["env"]["GIT_NO_LAZY_FETCH"] == "1"
    assert kwargs["env"]["GIT_NO_REPLACE_OBJECTS"] == "1"
    assert kwargs["timeout"] == 30 and kwargs["stderr"] is subprocess.DEVNULL


def test_offline_cli_does_not_fall_back_to_probes(monkeypatch, tmp_path, capsys):
    import sys

    monkeypatch.setattr(
        sys, "argv", ["baseline", "--instruction-refs", "a" * 40, "b" * 40]
    )
    monkeypatch.setattr(
        efficiency_baseline, "collect_baseline", lambda **_: pytest.fail("No probes")
    )
    monkeypatch.setattr(
        efficiency_baseline, "compare_instructions", lambda *_: {"offline": True}
    )
    assert efficiency_baseline.main() == 0
    assert json.loads(capsys.readouterr().out) == {"offline": True}


def test_offline_missing_objects_fail_without_probe_fallback(monkeypatch):
    import sys

    monkeypatch.setattr(
        sys, "argv", ["baseline", "--instruction-refs", "a" * 40, "b" * 40]
    )
    monkeypatch.setattr(
        efficiency_baseline, "collect_baseline", lambda **_: pytest.fail("No probes")
    )

    def missing(*_):
        raise subprocess.CalledProcessError(1, ["git"])

    monkeypatch.setattr(efficiency_baseline, "compare_instructions", missing)
    with pytest.raises(SystemExit, match="no fetch or probe"):
        efficiency_baseline.main()


def test_real_local_head_metadata_is_deterministic():
    root = efficiency_baseline._repo_root()
    sha = subprocess.check_output(
        ["git", "-C", str(root), "rev-parse", "HEAD"], text=True
    ).strip()
    report = efficiency_baseline.compare_instructions(root, sha, sha)
    assert report["changes"] == []
    assert all(group["files"] > 0 for group in report["baseline"]["groups"].values())
    assert report == efficiency_baseline.compare_instructions(root, sha, sha)


def test_comparison_records_added_removed_and_modified_metadata(monkeypatch, tmp_path):
    snapshots = {
        "before": {
            "commit": "a" * 40,
            "groups": {},
            "files": {"removed": {"bytes_lf": 1}, "modified": {"sha256_lf": "old"}},
        },
        "after": {
            "commit": "b" * 40,
            "groups": {},
            "files": {"added": {"bytes_lf": 2}, "modified": {"sha256_lf": "new"}},
        },
    }
    monkeypatch.setattr(
        efficiency_baseline, "instruction_snapshot", lambda _r, ref: snapshots[ref]
    )
    report = efficiency_baseline.compare_instructions(tmp_path, "before", "after")
    assert [entry["path"] for entry in report["changes"]] == [
        "added",
        "modified",
        "removed",
    ]
    assert report["changes"][0]["before"] is None
    assert report["changes"][1]["after"] == {"sha256_lf": "new"}
    assert report["changes"][2]["after"] is None


def test_incomplete_batch_objects_fail_closed(monkeypatch, tmp_path):
    monkeypatch.setattr(
        efficiency_baseline,
        "_local_git",
        lambda *_a, **_k: f"{'1' * 40} blob 10\nshort".encode(),
    )
    with pytest.raises(ValueError, match="Incomplete"):
        efficiency_baseline._batch_blobs(tmp_path, [("AGENTS.md", "1" * 40, "shared")])


def test_cli_rejects_env_output_before_any_probe(monkeypatch, tmp_path):
    import sys

    monkeypatch.setattr(
        sys, "argv", ["baseline", "--output", str(tmp_path / ".env.example")]
    )
    monkeypatch.setattr(
        efficiency_baseline, "collect_baseline", lambda **_: pytest.fail("No probe")
    )
    with pytest.raises(ValueError, match="environment"):
        efficiency_baseline.main()
    assert not (tmp_path / ".env.example").exists()


def test_committed_static_comparison_binds_generator_and_marks_live_metrics_missing():
    import hashlib

    root = efficiency_baseline._repo_root()
    report = json.loads(
        (
            root / "docs/reports/generated/skill-efficiency-source-comparison.json"
        ).read_text(encoding="utf-8")
    )
    code = Path(efficiency_baseline.__file__).read_bytes().replace(b"\r\n", b"\n")
    assert report["generator_sha256_lf"] == hashlib.sha256(code).hexdigest()
    assert report["policy"]["agents_or_probes_started"] is False
    assert report["policy"]["raw_contents_retained"] is False
    assert set(report["runtime_metrics"].values()) == {"NOT_MEASURED"}
    assert report["baseline"]["commit"] != report["after"]["commit"]


@pytest.mark.parametrize("part", [".envrc", ".ENV-private.md", ".environment"])
def test_instruction_scope_excludes_all_environment_prefixed_paths(part):
    path = f".codex/skills/{part}/source.md"
    assert efficiency_baseline._instruction_group(path) is None


@pytest.mark.parametrize("share", [".envrc", ".ENV-private"])
def test_environment_unc_share_is_rejected_before_resolution(share):
    from pathlib import PureWindowsPath
    from unittest.mock import Mock

    absolute = PureWindowsPath(f"//synthetic-host/{share}/report.json")
    resolve = Mock(side_effect=AssertionError("No network path resolution"))
    path = SimpleNamespace(absolute=lambda: absolute, resolve=resolve)
    with pytest.raises(ValueError, match="environment"):
        efficiency_baseline._check_output_target(path)
    resolve.assert_not_called()


@pytest.mark.parametrize(
    "resolved_share,denied", [("reports", False), (".ENV-private", True)]
)
def test_output_checks_resolved_unc_share_without_blocking_safe_paths(
    resolved_share, denied
):
    from pathlib import PureWindowsPath
    from unittest.mock import Mock

    resolve = Mock(
        return_value=PureWindowsPath(f"//synthetic-host/{resolved_share}/report.json")
    )
    path = SimpleNamespace(
        absolute=lambda: PureWindowsPath("//synthetic-host/reports/report.json"),
        resolve=resolve,
    )
    if denied:
        with pytest.raises(ValueError, match="environment"):
            efficiency_baseline._check_output_target(path)
    else:
        assert efficiency_baseline._check_output_target(path) is None
    resolve.assert_called_once_with()
