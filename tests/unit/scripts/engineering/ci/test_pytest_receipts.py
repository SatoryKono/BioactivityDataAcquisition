"""Receipt semantics for marker selection, phases, passes, and failures."""

from __future__ import annotations

import json
import os
import stat
import subprocess
import sys
from pathlib import Path

import pytest

from scripts.engineering.ci.pytest_receipts import (
    ReceiptPlugin,
    _is_run_output,
    _normalize_repo_path,
    _phases_finished,
    dedupe_receipts,
    redact_secrets,
    terminal_outcome,
    write_receipt_file,
)

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[5]
PLUGIN = "scripts.engineering.ci.pytest_receipts"
RUNNER = REPO / "scripts" / "engineering" / "ci" / "run_pytest_resilient.py"


def _unlock(path: Path) -> None:
    if not path.exists():
        return
    for item in path.rglob("*"):
        if item.is_file():
            item.chmod(stat.S_IWRITE | stat.S_IREAD)


@pytest.fixture
def receipts(tmp_path: Path):
    path = tmp_path / "receipts"
    yield path
    _unlock(path)


def _pytest(
    test_file: Path,
    receipt_dir: Path,
    *extra: str,
    env: dict[str, str] | None = None,
    cwd: Path | None = None,
    repo_root: Path | None = None,
) -> subprocess.CompletedProcess[str]:
    child_env = os.environ.copy() if env is None else env.copy()
    inherited = [
        part for part in child_env.get("PYTHONPATH", "").split(os.pathsep) if part
    ]
    if str(REPO) not in inherited:
        inherited.insert(0, str(REPO))
    child_env["PYTHONPATH"] = os.pathsep.join(inherited)
    command = [
        sys.executable,
        "-m",
        "pytest",
        str(test_file),
        "-o",
        "addopts=",
        "--noconftest",
        "-p",
        PLUGIN,
        "-p",
        "no:cacheprovider",
        "-q",
        "--tb=short",
        f"--receipt-dir={receipt_dir}",
        "--receipt-run-id=run1",
        "--receipt-attempt=1",
        "--receipt-pass=direct",
        f"--receipt-repo-root={repo_root or REPO}",
        *extra,
    ]
    return subprocess.run(
        command,
        cwd=cwd or test_file.parent,
        env=child_env,
        capture_output=True,
        text=True,
        check=False,
    )


def _load(
    receipt_dir: Path,
    *,
    attempt: str = "1",
    pass_name: str = "direct",
    worker: str = "master",
    run_id: str = "run1",
) -> dict[str, object]:
    path = receipt_dir / run_id / attempt / pass_name / worker / "receipt.json"
    _unlock(path.parent)
    return json.loads(path.read_text(encoding="utf-8"))


def _terminals(payload: dict[str, object]) -> dict[str, str]:
    results = payload["results"]
    assert isinstance(results, dict)
    return {
        str(nodeid): str(item["terminal"])
        for nodeid, item in results.items()
        if isinstance(item, dict)
    }


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def test_failure_continues_and_keeps_collection(receipts: Path, tmp_path: Path) -> None:
    test_file = tmp_path / "test_continue.py"
    _write(
        test_file,
        "def test_fail():\n    assert False\n\ndef test_pass():\n    assert True\n",
    )
    completed = _pytest(test_file, receipts)
    assert completed.returncode == 1
    payload = _load(receipts)
    assert payload["completeness"] == "complete"
    assert payload["early_stop"] is False
    assert payload["exit_code"] == 1
    collection = payload["collection"]
    assert isinstance(collection, dict)
    assert collection["selected"] == 2
    assert collection["status"] == "observed"
    terminals = _terminals(payload)
    assert sorted(terminals.values()) == ["failed", "passed"]


def test_exitfirst_is_incomplete(receipts: Path, tmp_path: Path) -> None:
    test_file = tmp_path / "test_exitfirst.py"
    _write(
        test_file,
        "def test_fail():\n    assert False\n\ndef test_later():\n    assert True\n",
    )
    completed = _pytest(test_file, receipts, "-x")
    assert completed.returncode == 1
    payload = _load(receipts)
    collection = payload["collection"]
    assert isinstance(collection, dict)
    assert collection["selected"] == 2
    assert payload["early_stop"] is True
    assert payload["completeness"] == "incomplete"
    assert len(_terminals(payload)) == 1


def test_maxfail_is_incomplete(receipts: Path, tmp_path: Path) -> None:
    test_file = tmp_path / "test_maxfail.py"
    _write(
        test_file,
        "def test_fail():\n    assert False\n\ndef test_later():\n    assert True\n",
    )
    completed = _pytest(test_file, receipts, "--maxfail=1")
    assert completed.returncode == 1
    payload = _load(receipts)
    assert payload["completeness"] == "incomplete"
    assert payload["early_stop"] is True


def test_selected_nodeids_follow_marker_deselection(
    receipts: Path, tmp_path: Path
) -> None:
    test_file = tmp_path / "test_marks.py"
    _write(
        test_file,
        "import pytest\n\n"
        "def test_keep():\n    assert True\n\n"
        "@pytest.mark.slow\n"
        "def test_drop():\n    assert True\n",
    )
    completed = _pytest(test_file, receipts, "-m", "not slow")
    assert completed.returncode == 0
    payload = _load(receipts)
    collection = payload["collection"]
    assert isinstance(collection, dict)
    selected = collection["selected_nodeids"]
    assert isinstance(selected, list)
    assert collection["selected"] == 1
    assert collection["deselected"] == 1
    assert any(nodeid.endswith("test_keep") for nodeid in selected)
    assert not any(str(nodeid).endswith("test_drop") for nodeid in selected)
    assert list(_terminals(payload)) == selected


def test_teardown_failure_is_not_a_pass(receipts: Path, tmp_path: Path) -> None:
    test_file = tmp_path / "test_teardown.py"
    _write(
        test_file,
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def boom():\n"
        "    yield\n"
        "    raise RuntimeError('teardown failed')\n\n"
        "def test_body(boom):\n"
        "    assert True\n",
    )
    completed = _pytest(test_file, receipts)
    assert completed.returncode == 1
    assert _terminals(_load(receipts))
    assert set(_terminals(_load(receipts)).values()) == {"teardown_error"}


def test_setup_skip_and_xfail_stay_distinct(receipts: Path, tmp_path: Path) -> None:
    test_file = tmp_path / "test_phases.py"
    _write(
        test_file,
        "import pytest\n\n"
        "@pytest.fixture\n"
        "def broken():\n"
        "    raise RuntimeError('setup failed')\n\n"
        "def test_setup(broken):\n"
        "    assert True\n\n"
        "@pytest.mark.skipif(True, reason='exercise skipped receipt outcome')\n"
        "def test_skip():\n"
        "    assert False\n\n"
        "@pytest.mark.xfail\n"
        "def test_xfail():\n"
        "    assert False\n",
    )
    completed = _pytest(test_file, receipts)
    assert completed.returncode == 1
    values = set(_terminals(_load(receipts)).values())
    assert values == {"setup_error", "skipped", "xfailed"}


def test_collection_error_is_unknown(receipts: Path, tmp_path: Path) -> None:
    test_file = tmp_path / "test_collect.py"
    _write(test_file, "import definitely_missing_mod_12070\n")
    completed = _pytest(test_file, receipts)
    assert completed.returncode != 0
    payload = _load(receipts)
    assert payload["completeness"] == "unknown"
    collection = payload["collection"]
    assert isinstance(collection, dict)
    assert collection["status"] == "error"
    assert collection["errors"]
    assert payload["results"] == {}


def test_secrets_are_excluded(receipts: Path, tmp_path: Path) -> None:
    test_file = tmp_path / "test_secret.py"
    _write(test_file, "def test_ok():\n    assert True\n")
    env = os.environ.copy()
    env["SECRET_TOKEN"] = "super-secret-value"
    env["GITHUB_RUN_ID"] = "456"
    completed = _pytest(test_file, receipts, env=env)
    assert completed.returncode == 0
    raw = json.dumps(_load(receipts))
    assert "super-secret-value" not in raw
    assert "SECRET_TOKEN" not in raw
    payload = _load(receipts)
    environment = payload["environment"]
    assert isinstance(environment, dict)
    assert environment.get("GITHUB_RUN_ID") == "456"


def test_sha_mismatch_fails(receipts: Path, tmp_path: Path) -> None:
    test_file = tmp_path / "test_sha.py"
    _write(test_file, "def test_ok():\n    assert True\n")
    completed = _pytest(test_file, receipts, "--receipt-expected-sha=fake_sha123")
    assert completed.returncode != 0
    assert "Checkout SHA mismatch! Expected fake_sha123" in completed.stderr
    payload = _load(receipts, worker="runner")
    assert payload["role"] == "runner"
    assert payload["terminal_kind"] == "sha_mismatch"
    assert payload["completeness"] == "unknown"
    assert payload["collection"] == {"status": "unknown"}
    assert payload["results"] is None
    assert "fake_sha123" in str(payload["observed_error"])


def test_xdist_workers_do_not_double_count(receipts: Path, tmp_path: Path) -> None:
    pytest.importorskip("xdist")
    test_file = tmp_path / "test_dist.py"
    _write(
        test_file,
        "def test_one():\n    assert True\n\ndef test_two():\n    assert True\n",
    )
    completed = _pytest(test_file, receipts, "-n", "2", "--dist", "load")
    assert completed.returncode == 0, completed.stderr
    files = list(receipts.rglob("receipt.json"))
    assert files
    payloads = []
    for path in files:
        _unlock(path.parent)
        payloads.append(json.loads(path.read_text(encoding="utf-8")))
    assert all(item["role"] == "worker" for item in payloads)
    assert all(item["worker"] != "master" for item in payloads)
    assert all(item["completeness"] == "complete" for item in payloads)
    nodeids = [nodeid for item in payloads for nodeid in item["results"]]
    assert len(nodeids) == len(set(nodeids)) == 2
    for item in payloads:
        collection = item["collection"]
        assert isinstance(collection, dict)
        assert collection["selected"] == len(item["results"])


def test_dist_without_workers_still_writes_receipt(
    receipts: Path, tmp_path: Path
) -> None:
    pytest.importorskip("xdist")
    test_file = tmp_path / "test_dist_flag.py"
    _write(test_file, "def test_one():\n    assert True\n")
    completed = _pytest(test_file, receipts, "--dist", "load")
    assert completed.returncode == 0, completed.stderr
    payload = _load(receipts)
    assert payload["worker"] == "master"
    assert payload["completeness"] == "complete"


def test_timeout_writes_runner_record_without_fake_collection(
    receipts: Path, tmp_path: Path
) -> None:
    test_file = tmp_path / "test_sleep.py"
    _write(test_file, "import time\n\ndef test_sleep():\n    time.sleep(30)\n")
    reports = tmp_path / "reports"
    command = [
        sys.executable,
        str(RUNNER),
        "--target",
        str(test_file),
        "--reports-dir",
        str(reports),
        "--receipt-dir",
        str(receipts),
        "--receipt-run-id",
        "runT",
        "--receipt-attempt",
        "1",
        "--parallel-marker",
        "not slow",
        "--parallel-addopts",
        "-q --tb=line -p no:xdist -p no:cacheprovider",
        "--fallback-addopts",
        "-q --tb=line -p no:xdist -p no:cacheprovider",
        "--parallel-timeout-seconds",
        "1",
        "--fallback-timeout-seconds",
        "1",
        "--skip-serial-pass",
    ]
    completed = subprocess.run(
        command,
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode != 0
    for pass_name in ("parallel", "fallback"):
        path = receipts / "runT" / "1" / pass_name / "runner" / "receipt.json"
        assert path.is_file(), completed.stderr
        _unlock(path.parent)
        payload = json.loads(path.read_text(encoding="utf-8"))
        assert payload["role"] == "runner"
        assert payload["terminal_kind"] == "timeout"
        assert payload["completeness"] == "unknown"
        assert payload["collection"] == {"status": "unknown"}
        assert payload["results"] is None
        assert "timed out" in str(payload["observed_error"])
        assert pass_name in str(payload["observed_error"])


def test_runner_from_other_cwd_keeps_pythonpath(receipts: Path, tmp_path: Path) -> None:
    sentinel = tmp_path / "sentinel"
    sentinel.mkdir()
    outside = tmp_path / "outside"
    outside.mkdir()
    test_file = outside / "test_cwd.py"
    _write(
        test_file,
        "def test_ok():\n    assert True\n",
    )
    env = os.environ.copy()
    env["PYTHONPATH"] = str(sentinel)
    env["SECRET_TOKEN"] = "cwd-secret-value"
    reports = tmp_path / "reports"
    command = [
        sys.executable,
        str(RUNNER),
        "--target",
        str(test_file),
        "--reports-dir",
        str(reports),
        "--receipt-dir",
        str(receipts),
        "--receipt-run-id",
        "runC",
        "--receipt-attempt",
        "2",
        "--parallel-marker",
        "not slow",
        "--parallel-addopts",
        "-q --tb=line -p no:xdist -p no:cacheprovider",
        "--skip-serial-pass",
        "--parallel-timeout-seconds",
        "120",
    ]
    completed = subprocess.run(
        command,
        cwd=outside,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    payload = _load(receipts, attempt="2", run_id="runC", pass_name="parallel")
    raw = json.dumps(payload)
    assert "cwd-secret-value" not in raw
    assert payload["pass"] == "parallel"
    assert payload["attempt"] == "2"


def test_distinct_passes_and_attempts_dedupe(receipts: Path) -> None:
    base = {
        "run_id": "run1",
        "attempt": "1",
        "pass": "parallel",
        "role": "worker",
        "worker": "master",
        "results": {},
    }
    other_pass = dict(base, **{"pass": "serial"})
    other_attempt = dict(base, attempt="2")
    duplicate = dict(base)
    merged = dedupe_receipts([base, duplicate, other_pass, other_attempt])
    assert len(merged) == 3
    conflict = dict(base, results={"a": "failed"})
    with pytest.raises(ValueError, match="conflicting receipts"):
        dedupe_receipts([base, conflict])


def test_receipt_write_is_immutable(tmp_path: Path) -> None:
    first = {"run_id": "a", "value": 1}
    path = write_receipt_file(tmp_path / "one", first)
    write_receipt_file(tmp_path / "one", {"run_id": "a", "value": 2})
    _unlock(path.parent)
    assert json.loads(path.read_text(encoding="utf-8"))["value"] == 1


def test_terminal_outcome_matrix() -> None:
    assert (
        terminal_outcome({"setup": "passed", "call": "passed", "teardown": "passed"})
        == "passed"
    )
    assert terminal_outcome({"setup": "passed", "call": "passed"}) == "error"
    assert (
        terminal_outcome({"setup": "passed", "call": "passed", "teardown": "error"})
        == "teardown_error"
    )
    assert terminal_outcome({"setup": "error"}) == "setup_error"
    assert terminal_outcome({"call": "xfailed"}) == "xfailed"


def test_partial_phases_are_incomplete() -> None:
    plugin = object.__new__(ReceiptPlugin)
    plugin.collection_observed = True
    plugin.collection_errors = []
    plugin.selected_nodeids = ["t"]
    plugin.results = {"t": {"setup": "passed", "call": "passed", "teardown": None}}
    assert plugin._completeness(False) == "incomplete"
    plugin.results = {"t": {"setup": "passed", "call": "passed", "teardown": "passed"}}
    assert plugin._completeness(False) == "complete"
    plugin.results = {"t": {"setup": "skipped", "call": None, "teardown": None}}
    assert _phases_finished(plugin.results["t"])
    assert plugin._completeness(False) == "complete"


def test_redact_secrets_covers_auth_and_urls() -> None:
    text = redact_secrets(
        "neo4j-secret postgres://user:pw@localhost/db",
        {
            "NEO4J_AUTH": "neo4j-secret",
            "DATABASE_URL": "postgres://user:pw@localhost/db",
        },
    )
    assert "neo4j-secret" not in text
    assert "postgres://user:pw@localhost/db" not in text
    assert "[REDACTED]" in text


def test_hidden_receipt_dir_and_tracked_reports_stay_distinct(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    receipt_dir = repo / ".receipts"
    receipt_dir.mkdir(parents=True)
    assert _normalize_repo_path("./.receipts/receipt.json") == ".receipts/receipt.json"
    assert _is_run_output(".receipts/run/receipt.json", "??", receipt_dir, repo)
    assert not _is_run_output("reports/quality/input.json", " M", receipt_dir, repo)
    assert _is_run_output("reports/noise.txt", "??", receipt_dir, repo)


def test_dirty_sources_are_not_a_clean_head(receipts: Path, tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo, check=True)
    source = repo / "src"
    source.mkdir()
    _write(source / "example.py", "VALUE = 1\n")
    tracked_report = repo / "reports" / "quality"
    tracked_report.mkdir(parents=True)
    _write(tracked_report / "input.json", "{}\n")
    _write(repo / "test_ok.py", "def test_ok():\n    assert True\n")
    subprocess.run(["git", "add", "."], cwd=repo, check=True)
    subprocess.run(
        [
            "git",
            "-c",
            "user.email=receipt@example.com",
            "-c",
            "user.name=receipt",
            "commit",
            "-m",
            "init",
        ],
        cwd=repo,
        check=True,
    )
    _write(source / "example.py", "VALUE = 2\n")
    _write(tracked_report / "input.json", '{"changed": true}\n')
    _write(repo / "reports" / "noise.txt", "output\n")
    completed = _pytest(
        repo / "test_ok.py",
        receipts,
        repo_root=repo,
    )
    assert completed.returncode == 0, completed.stderr
    payload = _load(receipts)
    source_state = payload["source"]
    assert isinstance(source_state, dict)
    assert source_state["clean"] is False
    dirty = source_state["measured_dirty_paths"]
    assert isinstance(dirty, list)
    assert any(str(path).endswith("src/example.py") for path in dirty)
    assert any(str(path).endswith("reports/quality/input.json") for path in dirty)
    assert not any(str(path).endswith("reports/noise.txt") for path in dirty)
    assert source_state["head"] != "unknown"
