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
        """Store the contract code and message."""
        super().__init__(message)
        self.code = code


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    """Bridge pytest's public nodeid to pytest-benchmark 5.3's removed alias.

    pytest 9.2 removed ``Function._nodeid`` while pytest-benchmark 5.3.0
    still reads it. The benchmark guard is loaded before that plugin, so add
    the compatibility alias during collection when the plugin needs it.
    """
    for item in items:
        if not hasattr(item, "_nodeid"):
            item._nodeid = item.nodeid


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
        """Return whether the revision was not read from a gitdir HEAD file."""
        return self.revision_method != "gitdir_head_file"


def _command_tokens(command: object) -> list[str]:
    """Split a subprocess command into string tokens."""
    if isinstance(command, str):
        return command.split()
    if isinstance(command, (list, tuple)):
        return [str(part) for part in command]
    return [str(command)]


def _is_unwanted_vcs_probe(command: object) -> bool:
    """Return whether the command starts with git or hg."""
    tokens = _command_tokens(command)
    if not tokens:
        return False
    executable = tokens[0].replace("\\", "/").rsplit("/", 1)[-1].lower()
    return executable in _VCS_EXECUTABLES


def _note_blocked_probe(command: object) -> None:
    """Remember a short label for a refused VCS probe."""
    tokens = _command_tokens(command)
    label = " ".join(tokens[:4])
    if len(_BLOCKED_PROBES) < 8:
        _BLOCKED_PROBES.append(label)


def _refuse_vcs_probe(command: object) -> None:
    """Raise when pytest-benchmark tries to run git or hg."""
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
    """Find the git directory from a checkout or a linked worktree file."""
    current = _safe_resolve(start)
    if current is None:
        return None
    candidates = (current,) if not allow_parent_search else (current, *current.parents)
    for candidate in candidates:
        git_entry = candidate / ".git"
        if git_entry.is_dir():
            return git_entry
        if not git_entry.is_file():
            if git_entry.is_symlink() or git_entry.exists():
                return None
            continue
        line = git_entry.read_text(encoding="utf-8").rstrip("\r\n")
        prefix = "gitdir:"
        if not line.startswith(prefix + " "):
            return None
        raw = line.split(":", 1)[1].strip()
        if not raw or "\n" in raw or "\x00" in raw:
            return None
        gitdir = Path(raw)
        if not gitdir.is_absolute():
            resolved = _safe_resolve(git_entry.parent / gitdir)
            if resolved is None:
                return None
            gitdir = resolved
        return gitdir
    return None


def _packed_ref(gitdir: Path, ref: str) -> str | None:
    """Return the SHA recorded for a ref in packed-refs."""
    packed = gitdir / "packed-refs"
    if not packed.exists() and not packed.is_symlink():
        return None
    found = None
    names: set[str] = set()
    can_peel = False
    for line in packed.read_text(encoding="utf-8").splitlines():
        if line.startswith("#"):
            continue
        if line.startswith("^"):
            if not can_peel or not _SHA_RE.fullmatch(line[1:].lower()):
                raise _CorruptLooseRef
            can_peel = False
            continue
        sha, separator, name = line.partition(" ")
        if (
            not separator
            or not _SHA_RE.fullmatch(sha.lower())
            or not _valid_ref(name)
            or name in names
        ):
            raise _CorruptLooseRef
        names.add(name)
        can_peel = True
        if name == ref:
            found = sha.lower()
    return found


class _CorruptLooseRef(Exception):
    """An existing loose ref is present but is not a SHA or symbolic ref."""


def _valid_ref(ref: str) -> bool:
    """Accept canonical ref paths without Git-forbidden components."""
    return (
        ref.startswith("refs/")
        and not any(
            char.isspace() or ord(char) < 32 or ord(char) == 127 for char in ref
        )
        and not any(
            token in ref for token in ("..", "@{", "\\", "~", "^", ":", "?", "*", "[")
        )
        and all(
            part and not part.startswith(".") and not part.endswith((".", ".lock"))
            for part in ref.split("/")
        )
    )


def _sha_at(gitdir: Path, ref: str, *, depth: int = 0) -> str | None:
    """Read loose refs, refusing damaged entries before consulting packed refs."""
    if depth > 2 or not _valid_ref(ref):
        raise _CorruptLooseRef
    ref_path = gitdir
    for part in ref.split("/"):
        ref_path = ref_path / part
        if ref_path.is_symlink():
            # A dangling or cyclic loose entry must never expose a stale packed ref.
            ref_path.resolve(strict=True)
    if ref_path.exists() or ref_path.is_symlink():
        value = ref_path.read_text(encoding="utf-8").rstrip("\r\n")
        if value.startswith("ref: "):
            target = value[5:]
            if target == ref:
                raise _CorruptLooseRef
            return _sha_at(gitdir, target, depth=depth + 1)
        lowered = value.lower()
        if _SHA_RE.fullmatch(lowered):
            return lowered
        raise _CorruptLooseRef
    return _packed_ref(gitdir, ref)


def _common_gitdir(gitdir: Path) -> Path | None:
    """Resolve the commondir file of a linked worktree git directory."""
    common_file = gitdir / "commondir"
    if not common_file.exists() and not common_file.is_symlink():
        backlink = gitdir / "gitdir"
        if backlink.exists() or backlink.is_symlink():
            raise _CorruptLooseRef
        return None
    raw = common_file.read_text(encoding="utf-8").strip()
    if not raw or "\n" in raw or "\x00" in raw:
        raise _CorruptLooseRef
    common = Path(raw)
    if not common.is_absolute():
        resolved = _safe_resolve(gitdir / common)
        if resolved is None:
            raise _CorruptLooseRef
        common = resolved
    if not common.is_dir():
        raise _CorruptLooseRef
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
        head_text = (gitdir / "HEAD").read_text(encoding="utf-8").rstrip("\r\n")
        common = _common_gitdir(gitdir)
        if head_text.startswith("ref: "):
            ref = head_text[5:]
            private = ref.startswith(
                ("refs/bisect/", "refs/worktree/", "refs/rewritten/")
            )
            directory = gitdir if private or common is None else common
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
    """Build commit info from the gitdir reader without a VCS subprocess."""
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
    """Return the current directory name as the project label."""
    return Path.cwd().name


def _safe_tag(project_name: str | None = None) -> str:
    """Return a tag that pairs the source revision with this process run id."""
    info = _safe_commit_info(project_name)
    return f"{info['id']}_{_RUN_ID}"


def _wrap_output(original: Any) -> Any:
    """Wrap a subprocess helper so git and hg probes are refused first."""

    def _wrapped(command: object, *args: object, **kwargs: object) -> Any:
        """Refuse a VCS probe, otherwise call the original subprocess helper."""
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
    """Return whether the guard loaded before the plugin and which probes were refused."""
    return {
        "schema_version": _SCHEMA_VERSION,
        "installed_before_plugin": _INSTALLED_BEFORE_PLUGIN,
        "blocked_probe_attempts": len(_BLOCKED_PROBES),
        "blocked_probes": list(_BLOCKED_PROBES),
    }


def _provenance_block() -> dict[str, Any]:
    """Return the source-revision object stored in measurement JSON."""
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
    """Return the current UTC time from the project clock."""
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
    """Return the UUID, start time, kind, and caller of this measurement."""
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
    dataset = os.environ.get("BIOETL_BENCHMARK_DATASET", "").strip()
    if not dataset:
        raise BenchmarkMeasurementContractError(
            "blocked_provenance",
            "BIOETL_BENCHMARK_DATASET must identify the input fixtures",
        )
    output_json["bioetl_measurement"] = {
        "dataset": dataset,
        "environment": "github-actions"
        if os.environ.get("GITHUB_ACTIONS") == "true"
        else "local",
    }


def _require_mapping(value: object, code: str, label: str) -> dict[str, Any]:
    """Return a JSON object or fail the named contract code."""
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
    """Validate a measurement JSON path and return a process status."""
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
