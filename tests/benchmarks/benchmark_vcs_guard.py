"""Stop pytest-benchmark VCS probes without inventing a measured revision.

``pytest-benchmark`` 5.2.3 and 5.3.0 call ``get_tag()`` from
``pytest_addoption``, before conftest hooks. That path calls
``get_commit_info`` → ``git describe`` / ``git show`` / ``git rev-parse`` and
``get_project_name`` → ``git rev-parse`` / ``git config`` (and the Mercurial
equivalents). Load this module with ``-p`` *before* ``-p benchmark`` so the
replacement is installed before the plugin module is imported.

The replacement does not shell out. Source revision is the checkout HEAD read
from the gitdir. Dirty state stays ``unknown``. The measured run id is a
process UUID, not a commit.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import uuid
from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
_UUID_RE = re.compile(r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$")
_VCS_EXECUTABLES = frozenset({"git", "git.exe", "hg", "hg.exe"})
_SCHEMA_VERSION = 1
_CALLER_ENV = "BIOETL_BENCHMARK_CALLER"

_INSTALLED = False
_INSTALLED_BEFORE_PLUGIN = False
_BLOCKED_PROBES: list[str] = []
_RUN_ID = str(uuid.uuid4())
_ClockNow = Callable[[], datetime]
_clock_now: _ClockNow | None = None
_started_at: str | None = None


class BenchmarkMeasurementContractError(Exception):
    """Measurement JSON failed the caller contract."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


class _BlockedBenchmarkVcsProbe(OSError):
    """Raised instead of executing a pytest-benchmark git/hg command."""


@dataclass(frozen=True)
class SourceRevision:
    """Checkout identity read without a VCS subprocess."""

    revision: str
    revision_method: str
    branch: str
    dirty_state: str = "unknown"

    @property
    def blocked(self) -> bool:
        return self.revision_method != "gitdir_head_file"


def _command_tokens(command: object) -> list[str]:
    if isinstance(command, str):
        return command.split()
    if isinstance(command, (list, tuple)):
        return [str(part) for part in command]
    return [str(command)]


def _is_unwanted_vcs_probe(command: object) -> bool:
    tokens = _command_tokens(command)
    if not tokens:
        return False
    executable = tokens[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
    return executable in _VCS_EXECUTABLES


def _note_blocked_probe(command: object) -> None:
    tokens = _command_tokens(command)
    label = " ".join(tokens[:4])
    if len(_BLOCKED_PROBES) < 8:
        _BLOCKED_PROBES.append(label)


def _refuse_vcs_probe(command: object) -> None:
    if _is_unwanted_vcs_probe(command):
        _note_blocked_probe(command)
        raise _BlockedBenchmarkVcsProbe(command)


def _safe_resolve(path: Path) -> Path | None:
    """Resolve *path* or return None when the walk cannot finish.

    Python 3.12 ``Path.resolve()`` raises ``RuntimeError`` for a symlink loop.
    That is a blocked gitdir read, not a signal to shell out to Git.
    """

    try:
        return path.resolve()
    except (OSError, RuntimeError):
        return None


def _resolve_gitdir(start: Path, *, allow_parent_search: bool) -> Path | None:
    current = _safe_resolve(start)
    if current is None:
        return None
    candidates = (current,) if not allow_parent_search else (current, *current.parents)
    for candidate in candidates:
        git_entry = candidate / ".git"
        if git_entry.is_dir():
            return git_entry
        if not git_entry.is_file():
            continue
        line = git_entry.read_text(encoding="utf-8").strip()
        prefix = "gitdir:"
        if not line.lower().startswith(prefix):
            return None
        raw = line.split(":", 1)[1].strip()
        gitdir = Path(raw)
        if not gitdir.is_absolute():
            resolved = _safe_resolve(git_entry.parent / gitdir)
            if resolved is None:
                return None
            gitdir = resolved
        return gitdir
    return None


def _packed_ref(gitdir: Path, ref: str) -> str | None:
    packed = gitdir / "packed-refs"
    if not packed.is_file():
        return None
    for line in packed.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or stripped.startswith("^"):
            continue
        sha, _separator, name = stripped.partition(" ")
        sha = sha.strip().lower()
        if name == ref and _SHA_RE.fullmatch(sha):
            return sha
    return None


class _CorruptLooseRef(Exception):
    """An existing loose ref is present but is not a SHA or symbolic ref."""


def _sha_at(gitdir: Path, ref: str, *, depth: int = 0) -> str | None:
    if depth > 2 or not ref or ref.startswith(("/", "\\")) or ".." in Path(ref).parts:
        return None
    ref_path = gitdir / ref
    if ref_path.is_file():
        value = ref_path.read_text(encoding="utf-8").strip()
        if value.lower().startswith("ref:"):
            target = value.split(":", 1)[1].strip()
            if not target or target == ref:
                raise _CorruptLooseRef
            return _sha_at(gitdir, target, depth=depth + 1)
        lowered = value.lower()
        if _SHA_RE.fullmatch(lowered):
            return lowered
        raise _CorruptLooseRef
    return _packed_ref(gitdir, ref)


def _common_gitdir(gitdir: Path) -> Path | None:
    common_file = gitdir / "commondir"
    if not common_file.is_file():
        return None
    raw = common_file.read_text(encoding="utf-8").strip()
    common = Path(raw)
    if not common.is_absolute():
        resolved = _safe_resolve(gitdir / common)
        if resolved is None:
            return None
        common = resolved
    return common


def read_source_revision(
    start: Path | None = None,
    *,
    allow_parent_search: bool = True,
) -> SourceRevision:
    """Read HEAD for ``start`` from git files.

    Failure returns ``revision='unknown'`` and ``revision_method='blocked'``.
    Dirty state is always ``unknown``: this reader does not run ``git status``.
    """

    root = Path.cwd() if start is None else start
    try:
        gitdir = _resolve_gitdir(root, allow_parent_search=allow_parent_search)
        if gitdir is None or not (gitdir / "HEAD").is_file():
            return SourceRevision("unknown", "blocked", "(unknown)")
        head_text = (gitdir / "HEAD").read_text(encoding="utf-8").strip()
        search_dirs = [gitdir]
        common = _common_gitdir(gitdir)
        if common is not None:
            search_dirs.append(common)
        if head_text.lower().startswith("ref:"):
            ref = head_text.split(":", 1)[1].strip()
            for directory in search_dirs:
                sha = _sha_at(directory, ref)
                if sha is not None:
                    return SourceRevision(sha, "gitdir_head_file", ref)
            return SourceRevision("unknown", "blocked", ref or "(unknown)")
        sha = head_text.lower()
        if _SHA_RE.fullmatch(sha):
            return SourceRevision(sha, "gitdir_head_file", "(detached head)")
    except (OSError, RuntimeError, UnicodeError, _CorruptLooseRef):
        return SourceRevision("unknown", "blocked", "(unknown)")
    return SourceRevision("unknown", "blocked", "(unknown)")


def _safe_commit_info(project_name: str | None = None) -> dict[str, Any]:
    source = read_source_revision(Path.cwd())
    project = project_name or Path.cwd().name
    payload: dict[str, Any] = {
        "id": source.revision,
        "time": None,
        "author_time": None,
        "dirty": None,
        "project": project,
        "branch": source.branch,
        "bioetl_revision_method": source.revision_method,
        "bioetl_dirty_state": source.dirty_state,
        "bioetl_run_id": _RUN_ID,
    }
    if source.blocked:
        payload["error"] = "blocked: gitdir HEAD unavailable without a VCS probe"
    return payload


def _safe_project_name(*_args: object, **_kwargs: object) -> str:
    return Path.cwd().name


def _safe_tag(project_name: str | None = None) -> str:
    info = _safe_commit_info(project_name)
    return f"{info['id']}_{_RUN_ID}"


def _wrap_output(original: Any) -> Any:
    def _wrapped(command: object, *args: object, **kwargs: object) -> Any:
        _refuse_vcs_probe(command)
        return original(command, *args, **kwargs)

    return _wrapped


def install_benchmark_vcs_guard() -> None:
    """Patch pytest-benchmark VCS seams once, before those seams run."""

    global _INSTALLED, _INSTALLED_BEFORE_PLUGIN
    if _INSTALLED:
        return
    try:
        import pytest_benchmark.utils as utils
    except ImportError:
        _INSTALLED = True
        _INSTALLED_BEFORE_PLUGIN = "pytest_benchmark.plugin" not in sys.modules
        return

    _INSTALLED_BEFORE_PLUGIN = "pytest_benchmark.plugin" not in sys.modules
    utils.get_commit_info = _safe_commit_info
    utils.get_project_name = _safe_project_name
    utils.get_tag = _safe_tag
    utils.subprocess_output = _wrap_output(utils.subprocess_output)
    utils.check_output = _wrap_output(utils.check_output)
    plugin = sys.modules.get("pytest_benchmark.plugin")
    if plugin is not None:
        plugin.get_commit_info = _safe_commit_info
        plugin.get_tag = _safe_tag
    _INSTALLED = True


def guard_status() -> dict[str, Any]:
    return {
        "schema_version": _SCHEMA_VERSION,
        "installed_before_plugin": _INSTALLED_BEFORE_PLUGIN,
        "blocked_probe_attempts": len(_BLOCKED_PROBES),
        "blocked_probes": list(_BLOCKED_PROBES),
    }


def _provenance_block() -> dict[str, Any]:
    source = read_source_revision(Path.cwd())
    return {
        "schema_version": _SCHEMA_VERSION,
        "revision": source.revision,
        "revision_method": source.revision_method,
        "dirty_state": source.dirty_state,
        "branch": source.branch,
    }


def bind_measurement_clock(now: _ClockNow | None) -> None:
    """Select the run clock and clear any stamp captured earlier."""

    global _clock_now, _started_at
    _clock_now = now
    _started_at = None


def _system_utc_now() -> datetime:
    from bioetl.infrastructure.time.system_clock import current_utc_time

    return current_utc_time()


def measurement_started_at() -> str:
    """Freeze the measurement timestamp on the first call of this run."""

    global _started_at
    if _started_at is None:
        moment = (_clock_now or _system_utc_now)()
        if moment.tzinfo is None:
            raise BenchmarkMeasurementContractError(
                "blocked_provenance",
                "measurement clock returned a naive datetime",
            )
        _started_at = moment.astimezone(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    return _started_at


def _run_block() -> dict[str, Any]:
    caller = os.environ.get(_CALLER_ENV, "").strip() or "unspecified"
    return {
        "schema_version": _SCHEMA_VERSION,
        "id": _RUN_ID,
        "started_at": measurement_started_at(),
        "kind": "pytest-benchmark",
        "caller": caller,
    }


def pytest_configure(config: pytest.Config) -> None:
    """Capture the run timestamp when this guard is actually loaded."""

    del config
    measurement_started_at()


@pytest.hookimpl(tryfirst=True)
def pytest_benchmark_generate_commit_info(config: pytest.Config) -> dict[str, Any]:
    """Replace plugin commit info before session finish shells out."""

    del config
    return _safe_commit_info()


def pytest_benchmark_update_json(
    config: pytest.Config,
    benchmarks: list[object],
    output_json: dict[str, Any],
) -> None:
    """Attach source revision and measured-run identity to the JSON payload."""

    del config, benchmarks
    source = _provenance_block()
    run = _run_block()
    commit_info = output_json.get("commit_info")
    if isinstance(commit_info, dict):
        commit_info["id"] = source["revision"]
        commit_info["dirty"] = None
        commit_info["bioetl_revision_method"] = source["revision_method"]
        commit_info["bioetl_dirty_state"] = source["dirty_state"]
        commit_info["bioetl_run_id"] = run["id"]
    output_json["bioetl_source"] = source
    output_json["bioetl_run"] = run
    output_json["bioetl_vcs_guard"] = guard_status()


def _require_mapping(value: object, code: str, label: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise BenchmarkMeasurementContractError(code, f"{label} is missing")
    return value


def validate_benchmark_measurement_json(
    path: Path,
    *,
    search_from: Path | None = None,
) -> dict[str, Any]:
    """Fail closed unless the JSON has real rounds and matching source SHA."""

    if not path.is_file():
        raise BenchmarkMeasurementContractError(
            "missing_output",
            f"measurement JSON is missing: {path}",
        )
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise BenchmarkMeasurementContractError(
            "invalid_json",
            f"measurement JSON is not valid JSON: {exc}",
        ) from exc
    if not isinstance(payload, dict):
        raise BenchmarkMeasurementContractError(
            "invalid_json", "JSON root is not an object"
        )

    benchmarks = payload.get("benchmarks")
    if not isinstance(benchmarks, list) or not benchmarks:
        raise BenchmarkMeasurementContractError(
            "no_measurements",
            "benchmarks must be a non-empty list",
        )
    for index, bench in enumerate(benchmarks):
        if not isinstance(bench, dict):
            raise BenchmarkMeasurementContractError(
                "no_measurements",
                f"benchmarks[{index}] is not an object",
            )
        stats = bench.get("stats")
        rounds = stats.get("rounds") if isinstance(stats, dict) else None
        if type(rounds) is not int or rounds < 1:
            raise BenchmarkMeasurementContractError(
                "no_measurements",
                f"benchmarks[{index}].stats.rounds must be an integer >= 1",
            )

    source = _require_mapping(
        payload.get("bioetl_source"), "blocked_provenance", "bioetl_source"
    )
    run = _require_mapping(
        payload.get("bioetl_run"), "blocked_provenance", "bioetl_run"
    )
    guard = _require_mapping(
        payload.get("bioetl_vcs_guard"),
        "blocked_provenance",
        "bioetl_vcs_guard",
    )
    schema_version = source.get("schema_version")
    if type(schema_version) is not int or schema_version != _SCHEMA_VERSION:
        raise BenchmarkMeasurementContractError(
            "blocked_provenance",
            "bioetl_source.schema_version is not 1",
        )
    if source.get("dirty_state") != "unknown":
        raise BenchmarkMeasurementContractError(
            "false_dirty_state",
            "dirty_state must stay unknown unless a non-probe check measured it",
        )
    revision = source.get("revision")
    if not isinstance(revision, str) or revision in {
        "",
        "unversioned",
        "bioetl-benchmark",
    }:
        raise BenchmarkMeasurementContractError(
            "blocked_provenance",
            "source revision is missing or synthetic",
        )
    commit_info = _require_mapping(
        payload.get("commit_info"),
        "blocked_provenance",
        "commit_info",
    )
    if commit_info.get("dirty") is not None:
        raise BenchmarkMeasurementContractError(
            "false_dirty_state",
            "commit_info.dirty must be null; a boolean would claim a dirty check",
        )
    if commit_info.get("id") != revision:
        raise BenchmarkMeasurementContractError(
            "blocked_provenance",
            "commit_info.id does not match bioetl_source.revision",
        )
    run_id = run.get("id")
    if not isinstance(run_id, str) or _UUID_RE.fullmatch(run_id) is None:
        raise BenchmarkMeasurementContractError(
            "blocked_provenance", "bioetl_run.id is not a UUID"
        )
    if run_id == revision:
        raise BenchmarkMeasurementContractError(
            "blocked_provenance",
            "run id must not be reused as the source revision",
        )
    if run.get("kind") != "pytest-benchmark":
        raise BenchmarkMeasurementContractError(
            "blocked_provenance", "bioetl_run.kind is wrong"
        )
    caller = run.get("caller")
    if (
        not isinstance(caller, str)
        or caller.strip() in {"", "unspecified"}
        or _SHA_RE.fullmatch(caller)
    ):
        raise BenchmarkMeasurementContractError(
            "blocked_provenance",
            "bioetl_run.caller must name the run, not a commit or unspecified",
        )
    if guard.get("installed_before_plugin") is not True:
        raise BenchmarkMeasurementContractError(
            "late_guard",
            "VCS guard was installed after pytest-benchmark import",
        )
    if (
        type(guard.get("blocked_probe_attempts")) is not int
        or guard.get("blocked_probe_attempts") != 0
    ):
        raise BenchmarkMeasurementContractError(
            "vcs_probe",
            "pytest-benchmark reached a VCS probe seam",
        )
    if (
        source.get("revision_method") != "gitdir_head_file"
        or _SHA_RE.fullmatch(revision) is None
    ):
        raise BenchmarkMeasurementContractError(
            "blocked_provenance",
            "source revision is blocked or not a full git SHA",
        )
    expected = read_source_revision(Path.cwd() if search_from is None else search_from)
    if expected.revision != revision or expected.revision_method != "gitdir_head_file":
        raise BenchmarkMeasurementContractError(
            "provenance_mismatch",
            "recorded source revision does not match the checkout gitdir HEAD",
        )
    return payload


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validate-measurement-json", type=Path, required=True)
    parser.add_argument("--search-from", type=Path, default=None)
    args = parser.parse_args(argv)
    try:
        validate_benchmark_measurement_json(
            args.validate_measurement_json,
            search_from=args.search_from,
        )
    except BenchmarkMeasurementContractError as exc:
        sys.stderr.write(f"{exc.code}: {exc}\n")
        return 1
    sys.stdout.write("benchmark measurement JSON passed\n")
    return 0


install_benchmark_vcs_guard()


if __name__ == "__main__":
    raise SystemExit(main())
