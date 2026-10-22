"""Fail-closed before/after checks for the quality-move manifest contract.

CLI paths are confined with ``scripts.engineering.common.repo_paths`` before
any read, write, or git invocation. Absolute paths outside this repository are
accepted only as explicit operator or pytest destinations.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from scripts.engineering.common.repo_paths import (
    confined_io_path,
    ensure_safe_cli_argv,
    read_bytes_confined,
    read_text_confined,
    write_text_confined,
)

_REQUIRED_COLUMNS = frozenset(
    {
        "source_path",
        "target_path",
        "blob_sha",
        "base_commit",
        "snapshot_relation_prior",
        "evidence_status",
        "required_changes",
        "acceptance",
    }
)
_DECISION_FIELDS = (
    "path",
    "literal",
    "context",
    "purpose",
    "owner",
    "reviewed_content_sha256",
    "review_by",
)
_BLOB_SHA = re.compile(r"[0-9a-f]{40}")
_REVIEW_DATE = re.compile(r"\d{4}-\d{2}-\d{2}")
_IMPORT_LINE = re.compile(r"(?m)^[ \t]*(?:from|import)[ \t]+([A-Za-z_][\w.]*)")
_GIT_LOCATION_VARS = {
    "GIT_COMMON_DIR",
    "GIT_DIR",
    "GIT_INDEX_FILE",
    "GIT_NAMESPACE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_WORK_TREE",
}
_GIT_TIMEOUT_SECONDS = 60
_Row = dict[str, str]


def _read_external_text(path: str) -> str:
    return read_text_confined(path, allow_external_absolute=True)


def _under_repo(repo: Path, relative: str) -> Path:
    return confined_io_path(relative, root=repo)


def _is_file(path: Path, *, root: Path) -> bool:
    confined = confined_io_path(path, root=root)
    return confined.is_file()  # NOSONAR - path rebuilt under root


def _sha256(path: Path, *, root: Path) -> str:
    payload = read_bytes_confined(path, root=root)
    return hashlib.sha256(payload).hexdigest()


def _git_env() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items() if key not in _GIT_LOCATION_VARS
    }


def _git_stdout(repo: Path, args: list[str]) -> str:
    command = ensure_safe_cli_argv(["git", *args])
    try:
        completed = (
            subprocess.run(  # NOSONAR - argv via ensure_safe_cli_argv  # nosec B603
                command,
                cwd=repo,
                capture_output=True,
                text=True,
                check=False,
                env=_git_env(),
                timeout=_GIT_TIMEOUT_SECONDS,
            )
        )
    except subprocess.TimeoutExpired as exc:
        raise RuntimeError("git command timed out") from exc
    if completed.returncode != 0:
        detail = completed.stderr.strip() or "git command failed"
        raise RuntimeError(detail)
    return completed.stdout.strip()


def _manifest_table(text: str) -> tuple[list[_Row] | None, str | None]:
    reader = csv.DictReader(io.StringIO(text))
    if reader.fieldnames is None:
        return None, "Empty manifest"
    columns = set(reader.fieldnames)
    if not _REQUIRED_COLUMNS.issubset(columns):
        return None, f"Missing columns. Expected at least {_REQUIRED_COLUMNS}"
    rows = list(reader)
    if len(rows) != 30:
        return None, f"Expected exactly 30 rows, found {len(rows)}"
    return rows, None


def _cell_error(row: _Row) -> str | None:
    if None in row:
        return "Manifest row has extra cells"
    for column in sorted(_REQUIRED_COLUMNS):
        value = row.get(column)
        if not isinstance(value, str) or not value.strip():
            return f"Manifest row missing {column}"
    return None


def _normalized_rel(repo: Path, relative: str, prefix: str) -> str:
    path = _under_repo(repo, relative)
    normalized = path.relative_to(repo).as_posix()
    if not normalized.startswith(prefix):
        raise ValueError(normalized)
    return normalized


def _duplicate_or_prefix_error(
    repo: Path, row: _Row, sources: set[str], targets: set[str]
) -> str | None:
    cell_error = _cell_error(row)
    if cell_error:
        return cell_error
    source = row["source_path"]
    target = row["target_path"]
    if source in sources:
        return f"Duplicate source_path: {source}"
    if target in targets:
        return f"Duplicate target_path: {target}"
    try:
        _normalized_rel(repo, source, "src/")
        _normalized_rel(repo, target, "scripts/")
    except ValueError:
        return "Path traversal detected in manifest rows"
    sources.add(source)
    targets.add(target)
    return None


def _row_identity_error(repo: Path, rows: list[_Row]) -> str | None:
    sources: set[str] = set()
    targets: set[str] = set()
    for row in rows:
        error = _duplicate_or_prefix_error(repo, row, sources, targets)
        if error:
            return error
    return None


def _blob_error(repo: Path, row: _Row) -> str | None:
    source = row["source_path"]
    expected = row["blob_sha"]
    commit = row["base_commit"]
    if _BLOB_SHA.fullmatch(expected) is None:
        return f"blob_sha must be 40 hex characters: {source}"
    if _BLOB_SHA.fullmatch(commit) is None:
        return f"base_commit must be 40 hex characters: {source}"
    try:
        normalized = _normalized_rel(repo, source, "src/")
    except ValueError:
        return f"Path traversal detected in {source}"
    spec = f"{commit}:{normalized}"
    try:
        actual = _git_stdout(repo, ["rev-parse", spec])
    except (RuntimeError, ValueError) as exc:
        return f"blob_sha lookup failed for {source}: {exc}"
    if actual != expected:
        return f"blob_sha mismatch for {source}"
    return None


def verify_manifest(manifest_path: str, repo: Path) -> dict[str, object]:
    """Validate the 30-row move manifest against blobs at ``base_commit``."""
    try:
        text = _read_external_text(manifest_path)
    except (OSError, ValueError) as exc:
        return {"status": "ERROR", "reason": f"Could not read manifest: {exc}"}
    rows, error = _manifest_table(text)
    if error or rows is None:
        return {"status": "ERROR", "reason": error or "Empty manifest"}
    identity_error = _row_identity_error(repo, rows)
    if identity_error:
        return {"status": "ERROR", "reason": identity_error}
    for row in rows:
        blob_error = _blob_error(repo, row)
        if blob_error:
            return {"status": "ERROR", "reason": blob_error}
    return {"status": "PASS", "rows": rows}


def _decision_field_error(item: dict[str, object]) -> str | None:
    for field in _DECISION_FIELDS:
        if field not in item:
            return f"Decision missing field {field}"
    literal = str(item.get("literal", ""))
    if literal in {"scripts", "src"}:
        return "Blanket excludes of src or scripts are not allowed"
    if item.get("exception_allowed") and item.get("executable_import"):
        return "Executable old imports cannot be excepted"
    if "verify_quality_move" in literal:
        return "Cannot exclude scanner constants"
    return None


def _review_date_error(item: dict[str, object]) -> str | None:
    raw = str(item.get("review_by", ""))
    if _REVIEW_DATE.fullmatch(raw) is None:
        return None
    reviewed = datetime.strptime(raw, "%Y-%m-%d").date()
    if reviewed < datetime.now(UTC).date():
        return f"Decision review_by is expired: {raw}"
    return None


def _decision_hash_error(repo: Path, item: dict[str, object]) -> str | None:
    relative = str(item["path"])
    removed = item.get("status") == "removed" or item.get("decision") == "removed"
    try:
        path = _under_repo(repo, relative)
    except ValueError:
        return "Path traversal detected in decision path"
    if not _is_file(path, root=repo):
        if removed:
            return None
        return f"Decision path is missing: {relative}"
    try:
        actual = _sha256(path, root=repo)
    except (OSError, ValueError) as exc:
        return f"Could not read decision path {relative}: {exc}"
    if actual != str(item["reviewed_content_sha256"]):
        return f"Hash mismatch for {relative}"
    return None


def _decision_items(payload: object) -> list[object] | str:
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict):
        nested = payload.get("decisions")
        if isinstance(nested, list):
            return nested
    return "Decisions payload must be a list or an object with decisions"


def verify_decisions(decisions_path: str, repo: Path) -> dict[str, object]:
    """Reject blanket excludes, scanner constants, and stale content hashes."""
    try:
        payload = json.loads(_read_external_text(decisions_path))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return {"status": "ERROR", "reason": f"Could not read decisions: {exc}"}
    items = _decision_items(payload)
    if isinstance(items, str):
        return {"status": "ERROR", "reason": items}
    for item in items:
        if not isinstance(item, dict):
            return {"status": "ERROR", "reason": "Decision entry must be an object"}
        field_error = _decision_field_error(item)
        if field_error:
            return {"status": "ERROR", "reason": field_error}
        date_error = _review_date_error(item)
        if date_error:
            return {"status": "ERROR", "reason": date_error}
        hash_error = _decision_hash_error(repo, item)
        if hash_error:
            return {"status": "ERROR", "reason": hash_error}
    return {"status": "PASS"}


def _repo_identity(repo: Path) -> tuple[str, str, bool]:
    try:
        commit = _git_stdout(repo, ["rev-parse", "HEAD"])
        tree = _git_stdout(repo, ["rev-parse", "HEAD^{tree}"])
        dirty = bool(_git_stdout(repo, ["status", "--porcelain"]))
    except (RuntimeError, ValueError):
        return "unknown", "unknown", True
    return commit, tree, dirty


def _input_hashes(
    manifest_path: str, decisions_path: str, evidence_path: str
) -> dict[str, str]:
    hashed: dict[str, str] = {}
    for name, path in (
        ("manifest", manifest_path),
        ("decisions", decisions_path),
        ("evidence", evidence_path),
    ):
        try:
            payload = read_bytes_confined(path, allow_external_absolute=True)
        except (OSError, ValueError):
            hashed[name] = ""
            continue
        hashed[name] = hashlib.sha256(payload).hexdigest()
    return hashed


def write_evidence(
    out_dir: Path,
    status: str,
    repo: Path,
    *,
    phase: str,
    manifest_path: str,
    decisions_path: str,
    evidence_path: str,
) -> None:
    """Persist ``execution_evidence.json`` and ``verify.log`` for this run."""
    commit, tree, dirty = _repo_identity(repo)
    log_path = out_dir / "verify.log"
    evidence = {
        "argv": sys.argv,
        "cwd": os.getcwd(),
        "interpreter": sys.executable,
        "tool": "verify_quality_move",
        "plugin_versions": {},
        "phase": phase,
        "input_hashes": _input_hashes(manifest_path, decisions_path, evidence_path),
        "commit": commit,
        "tree": tree,
        "dirty": dirty,
        "terminal_exit_code": 0 if status == "PASS" else 1,
        "status": status,
        "logs": str(log_path),
    }
    write_text_confined(
        log_path,
        f"{status}\n",
        allow_external_absolute=True,
    )
    write_text_confined(
        out_dir / "execution_evidence.json",
        json.dumps(evidence, indent=2),
        allow_external_absolute=True,
    )


def _tracked(repo: Path, relative: str) -> bool:
    try:
        normalized = _normalized_rel(
            repo, relative, "src/" if relative.startswith("src/") else "scripts/"
        )
    except ValueError:
        return False
    try:
        _git_stdout(repo, ["cat-file", "-e", f"HEAD:{normalized}"])
    except (RuntimeError, ValueError):
        return False
    return True


def _row_presence_error(
    repo: Path,
    row: _Row,
    *,
    source_must_exist: bool,
    phase: str,
) -> str | None:
    source = row["source_path"]
    target = row["target_path"]
    try:
        _normalized_rel(repo, source, "src/")
        _normalized_rel(repo, target, "scripts/")
    except ValueError:
        return "Path traversal detected in manifest rows"
    source_exists = _tracked(repo, source)
    target_exists = _tracked(repo, target)
    if source_must_exist and not source_exists:
        return f"Phase {phase}: missing source {source}"
    if source_must_exist and target_exists:
        return f"Phase {phase}: target already exists {target}"
    if not source_must_exist and source_exists:
        return f"Phase {phase}: source still exists {source}"
    if not source_must_exist and not target_exists:
        return f"Phase {phase}: missing target {target}"
    return None


def _moved_module(source: str) -> str | None:
    if not source.startswith("src/") or not source.endswith(".py"):
        return None
    return source[len("src/") : -3].replace("/", ".")


def _import_exempt(item: dict[str, object], path: str, module: str) -> bool:
    if item.get("exception_allowed") is not True:
        return False
    if item.get("executable_import"):
        return False
    if str(item.get("path", "")) != path:
        return False
    literal = str(item.get("literal", ""))
    return module == literal or module.startswith(f"{literal}.")


def _matching_module(imported: str, modules: list[str]) -> str | None:
    for module in modules:
        if imported == module or imported.startswith(f"{module}."):
            return module
    return None


def _leftover_import_error(
    repo: Path, rows: list[_Row], decisions_path: str
) -> str | None:
    modules = [module for row in rows if (module := _moved_module(row["source_path"]))]
    if not modules:
        return None
    try:
        listed = _git_stdout(repo, ["ls-files", "-z"])
        payload = json.loads(_read_external_text(decisions_path))
    except (OSError, RuntimeError, ValueError, json.JSONDecodeError) as exc:
        return f"Could not scan leftover imports: {exc}"
    items = _decision_items(payload)
    decisions = items if isinstance(items, list) else []
    targets = {row["target_path"] for row in rows}
    for relative in listed.split("\0"):
        if not relative or relative in targets:
            continue
        try:
            text = read_text_confined(relative, root=repo)
        except (OSError, UnicodeError, ValueError):
            continue
        for match in _IMPORT_LINE.finditer(text):
            imported = match.group(1)
            if _matching_module(imported, modules) is None:
                continue
            exempt = any(
                isinstance(item, dict) and _import_exempt(item, relative, imported)
                for item in decisions
            )
            if not exempt:
                return f"Phase after: leftover import {imported} in {relative}"
    return None


def _phase_error(
    phase: str, repo: Path, rows: list[_Row], decisions_path: str
) -> str | None:
    try:
        dirty = bool(_git_stdout(repo, ["status", "--porcelain"]))
    except (RuntimeError, ValueError) as exc:
        return f"Could not read git status: {exc}"
    if dirty:
        return "working tree is dirty"
    source_must_exist = phase == "before"
    for row in rows:
        error = _row_presence_error(
            repo,
            row,
            source_must_exist=source_must_exist,
            phase=phase,
        )
        if error:
            return error
    if phase == "after":
        return _leftover_import_error(repo, rows, decisions_path)
    return None


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Verify Quality Move")
    parser.add_argument("--phase", choices=["before", "after"], required=True)
    parser.add_argument("--repo", required=True)
    parser.add_argument("--manifest-path", required=True)
    parser.add_argument("--decisions-path", required=True)
    parser.add_argument("--evidence-path", required=True)
    parser.add_argument("--out-dir", required=True)
    return parser.parse_args(argv)


def _fail(
    out_dir: Path,
    repo: Path,
    status: str,
    message: str,
    *,
    phase: str,
    manifest_path: str,
    decisions_path: str,
    evidence_path: str,
) -> int:
    write_evidence(
        out_dir,
        status,
        repo,
        phase=phase,
        manifest_path=manifest_path,
        decisions_path=decisions_path,
        evidence_path=evidence_path,
    )
    print(message)
    return 1


def _bind_cli_paths(
    args: argparse.Namespace,
) -> tuple[Path, Path, Path] | str:
    try:
        repo = confined_io_path(args.repo, allow_external_absolute=True)
        evidence = confined_io_path(args.evidence_path, allow_external_absolute=True)
        out_dir = confined_io_path(args.out_dir, allow_external_absolute=True)
    except ValueError as exc:
        return str(exc)
    return repo, evidence, out_dir


def _recorded_tree_error(recorded: object, current_tree: str | None) -> str | None:
    if (
        isinstance(recorded, str)
        and recorded
        and isinstance(current_tree, str)
        and current_tree
        and recorded == current_tree
    ):
        return None
    return f"Evidence tree {recorded} does not match current tree {current_tree}"


def _evidence_gate(evidence: Path, repo: Path, phase: str) -> str | None:
    if not evidence.is_file():  # NOSONAR - confined_io_path
        return f"Missing evidence path: {evidence}"
    try:
        payload = json.loads(read_text_confined(evidence, allow_external_absolute=True))
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return f"Could not read evidence: {exc}"
    if not isinstance(payload, dict):
        return "Could not read evidence: payload must be an object"
    if payload.get("status") != "PASS":
        return f"Evidence status is not PASS: {payload.get('status')}"
    tree_error = _recorded_tree_error(payload.get("tree"), _head_tree(repo))
    if tree_error:
        return tree_error
    recorded_phase = payload.get("phase")
    if recorded_phase != phase:
        return f"Evidence phase {recorded_phase} does not match {phase}"
    return None


def _head_tree(repo: Path) -> str | None:
    try:
        return _git_stdout(repo, ["rev-parse", "HEAD^{tree}"])
    except (RuntimeError, ValueError):
        return None


def _manifest_failure(manifest_path: str, repo: Path) -> tuple[str | None, list[_Row]]:
    manifest = verify_manifest(manifest_path, repo)
    if manifest["status"] == "PASS":
        rows = manifest.get("rows")
        if isinstance(rows, list):
            return None, rows
        return "missing rows", []
    reason = manifest.get("reason")
    return str(reason), []


def _emit_failure(
    out_dir: Path,
    repo: Path,
    status: str,
    message: str,
    args: argparse.Namespace,
) -> int:
    return _fail(
        out_dir,
        repo,
        status,
        message,
        phase=args.phase,
        manifest_path=args.manifest_path,
        decisions_path=args.decisions_path,
        evidence_path=args.evidence_path,
    )


def _evidence_status(evidence_error: str) -> str:
    if evidence_error.startswith("Missing evidence"):
        return "NOT_RUN"
    if evidence_error.startswith("Could not read evidence"):
        return "ERROR"
    return "BLOCKED"


def main(argv: list[str] | None = None) -> int:
    """Run one before or after verification phase and write evidence."""
    args = _parse_args(argv)
    bound = _bind_cli_paths(args)
    if isinstance(bound, str):
        print(f"Path error: {bound}")
        return 1
    repo, evidence, out_dir = bound
    manifest_error, rows = _manifest_failure(args.manifest_path, repo)
    if manifest_error:
        return _emit_failure(
            out_dir,
            repo,
            "BLOCKED",
            f"Manifest Error: {manifest_error}",
            args,
        )
    decisions = verify_decisions(args.decisions_path, repo)
    if decisions["status"] != "PASS":
        return _emit_failure(
            out_dir,
            repo,
            "BLOCKED",
            f"Decisions Error: {decisions['reason']}",
            args,
        )
    evidence_error = _evidence_gate(evidence, repo, args.phase)
    if evidence_error:
        return _emit_failure(
            out_dir,
            repo,
            _evidence_status(evidence_error),
            evidence_error,
            args,
        )
    phase_error = _phase_error(args.phase, repo, rows, args.decisions_path)
    if phase_error:
        return _emit_failure(out_dir, repo, "ERROR", phase_error, args)
    write_evidence(
        out_dir,
        "PASS",
        repo,
        phase=args.phase,
        manifest_path=args.manifest_path,
        decisions_path=args.decisions_path,
        evidence_path=args.evidence_path,
    )
    print("Verification PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
