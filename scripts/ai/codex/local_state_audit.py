#!/usr/bin/env python3
"""Audit and safely remediate local Codex state without exposing its contents."""

from __future__ import annotations

import argparse
import ast
import hashlib
import json
import os
import re
import shutil
import sqlite3
import stat
import subprocess
import tempfile
import time
from collections import Counter
from pathlib import Path
from typing import Any, Final

SCHEMA_VERSION: Final = "bioetl-codex-local-state-audit-v1"
DEFAULT_RETENTION_DAYS: Final = 90
REPO_ROOT: Final = Path(__file__).resolve().parents[3]
RULE_PATTERN: Final = re.compile(
    r'^\s*prefix_rule\(pattern=(\[.*\]),\s*decision="([a-z_]+)"\)\s*$'
)
SECRET_PATTERN: Final = re.compile(
    r"(?i)(?:api[_-]?key|access[_-]?token|authorization|password|credential|secret)"
)
UUID_PATTERN: Final = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.I,
)
SQLITE_IDENTIFIER_PATTERN: Final = re.compile(r"[A-Za-z_]\w*", re.ASCII)
SHELLS: Final = {"bash", "sh", "zsh", "pwsh", "powershell", "cmd", "cmd.exe"}
SENSITIVE_DIRS: Final = (
    "sessions",
    "archived_sessions",
    "rules",
    "logs",
    "shell_snapshots",
    "backups",
)
SENSITIVE_TOP_GLOBS: Final = (
    "auth.json",
    "config.toml",
    "*.config.toml",
    "history*.jsonl",
    "state*.sqlite*",
    "*.db",
    "*.db-*",
    "session*.jsonl",
    "models_cache.json",
    "version.json",
    ".codex-global-state.json",
)


def _is_env_file(path: Path) -> bool:
    return path.name == ".env" or path.name.startswith(".env.")


def _eligible_sensitive_node(path: Path) -> bool:
    return not path.is_symlink() and not _is_env_file(path)


def _iter_sensitive_nodes(codex_home: Path) -> list[Path]:
    nodes: set[Path] = {codex_home}
    for name in SENSITIVE_DIRS:
        root = codex_home / name
        if not root.exists() or root.is_symlink():
            continue
        nodes.add(root)
        nodes.update(path for path in root.rglob("*") if _eligible_sensitive_node(path))
    for pattern in SENSITIVE_TOP_GLOBS:
        nodes.update(
            path for path in codex_home.glob(pattern) if _eligible_sensitive_node(path)
        )
    return sorted(nodes, key=lambda path: (len(path.parts), path.as_posix()))


def _expected_mode(path: Path) -> int:
    return 0o700 if path.is_dir() else 0o600


def audit_permissions(codex_home: Path) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    errors = 0
    for path in _iter_sensitive_nodes(codex_home):
        try:
            actual = stat.S_IMODE(path.stat().st_mode)
            kind = "directories" if path.is_dir() else "files"
            counts[f"checked_{kind}"] += 1
            if actual & 0o077:
                counts[f"unsafe_{kind}"] += 1
        except OSError:
            errors += 1
    return {
        "checked_directories": counts["checked_directories"],
        "checked_files": counts["checked_files"],
        "unsafe_directories": counts["unsafe_directories"],
        "unsafe_files": counts["unsafe_files"],
        "errors": errors,
        "required_directory_mode": "0700",
        "required_file_mode": "0600",
    }


def _parse_rule(line: str) -> tuple[list[str], str] | None:
    match = RULE_PATTERN.match(line)
    if match is None:
        return None
    try:
        pattern = ast.literal_eval(match.group(1))
    except (SyntaxError, ValueError):
        return None
    if not isinstance(pattern, list) or not all(
        isinstance(item, str) for item in pattern
    ):
        return None
    return pattern, match.group(2)


def _looks_like_temporary_path(value: str) -> bool:
    """Classify temporary-path tokens without accessing a shared directory."""
    parts = tuple(
        part for part in value.replace("\\", "/").casefold().split("/") if part
    )
    if not parts:
        return False
    if parts[0] in {"tmp", "temp"}:
        return True
    if len(parts) >= 2 and parts[:2] == ("var", "tmp"):
        return True
    return "temp" in parts


def _removal_or_secret_rule_class(
    pattern: list[str],
    joined: str,
    executable: str,
) -> tuple[str, str] | None:
    if SECRET_PATTERN.search(joined):
        return "SECRET_REVIEW", "credential_like"
    if any("bioactivitydataacquisition2" in item.casefold() for item in pattern):
        return "REMOVE", "obsolete_checkout"
    if any(_looks_like_temporary_path(item) for item in pattern):
        return "REMOVE", "temporary_path"
    if executable in SHELLS and (
        len(pattern) <= 2
        or any(item.casefold() in {"-c", "-lc", "/c"} for item in pattern[1:])
    ):
        return "REMOVE", "broad_shell"
    if "--no-verify" in pattern:
        return "REMOVE", "verification_bypass"
    return None


def _narrow_rule_class(
    pattern: list[str],
    joined: str,
    executable: str,
) -> tuple[str, str] | None:
    if any(
        item.startswith(("/home/", "/mnt/", "/Users/"))
        or re.match(r"^[A-Za-z]:[\\/]", item)
        for item in pattern
    ):
        return "NARROW", "machine_specific_path"
    if len(pattern) == 1 and executable not in {"pwd", "true"}:
        return "NARROW", "broad_prefix"
    history_derived = (
        len(pattern) > 5
        or any(len(item) > 120 for item in pattern)
        or any(token in joined for token in ("&&", "||", ";", "`", "$("))
        or (len(pattern) >= 3 and any("\n" in item for item in pattern))
    )
    return ("NARROW", "command_history_derived") if history_derived else None


def _rule_class(pattern: list[str], decision: str) -> tuple[str, str]:
    if decision != "allow":
        return "KEEP", "non_allow_policy"
    joined = " ".join(pattern)
    lowered = joined.casefold()
    executable = Path(pattern[0]).name.casefold() if pattern else ""
    classified = _removal_or_secret_rule_class(pattern, joined, executable)
    if classified is not None:
        return classified
    classified = _narrow_rule_class(pattern, joined, executable)
    if classified is not None:
        return classified
    if not pattern or not executable:
        return "REMOVE", "invalid_empty"
    if any(value in lowered for value in ("gh auth token", "printenv", "env |")):
        return "SECRET_REVIEW", "credential_command"
    return "KEEP", "reusable_prefix"


def _rule_files(codex_home: Path) -> list[Path]:
    root = codex_home / "rules"
    if not root.is_dir():
        return []
    return [
        path
        for path in sorted(root.rglob("*"))
        if path.is_file() and not path.is_symlink() and not _is_env_file(path)
    ]


def audit_rules(codex_home: Path) -> dict[str, Any]:
    dispositions: Counter[str] = Counter()
    reasons: Counter[str] = Counter()
    parse_errors = 0
    rule_count = 0
    for path in _rule_files(codex_home):
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            parse_errors += 1
            continue
        for line in lines:
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parsed = _parse_rule(line)
            if parsed is None:
                parse_errors += 1
                continue
            rule_count += 1
            disposition, reason = _rule_class(*parsed)
            dispositions[disposition] += 1
            reasons[reason] += 1
    return {
        "files": len(_rule_files(codex_home)),
        "rules": rule_count,
        "dispositions": {
            name: dispositions[name]
            for name in ("KEEP", "NARROW", "REMOVE", "SECRET_REVIEW")
        },
        "reason_counts": dict(sorted(reasons.items())),
        "parse_errors": parse_errors,
        "content_emitted": False,
    }


def _sqlite_table_identifiers(
    connection: sqlite3.Connection,
    table: str,
) -> set[str]:
    if not SQLITE_IDENTIFIER_PATTERN.fullmatch(table):
        return set()
    columns = {
        row[1]
        for row in connection.execute(f'PRAGMA table_info("{table}")').fetchall()
        if isinstance(row[1], str)
    }
    identifiers: set[str] = set()
    for column in ("rollout_path", "session_id", "thread_id"):
        if column not in columns:
            continue
        values = connection.execute(
            f'SELECT "{column}" FROM "{table}" WHERE "{column}" IS NOT NULL'
        ).fetchall()
        for (value,) in values:
            if isinstance(value, str):
                identifiers.add(Path(value).name)
                identifiers.update(UUID_PATTERN.findall(value))
    return identifiers


def _sqlite_database_index(path: Path) -> tuple[set[str], bool]:
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        row = connection.execute("PRAGMA integrity_check").fetchone()
        integrity_ok = row is not None and row[0] == "ok"
        tables = connection.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        ).fetchall()
        identifiers: set[str] = set()
        for (table,) in tables:
            if isinstance(table, str):
                identifiers.update(_sqlite_table_identifiers(connection, table))
        return identifiers, integrity_ok
    finally:
        connection.close()


def _sqlite_index(codex_home: Path) -> tuple[set[str], str]:
    identifiers: set[str] = set()
    databases = [
        path
        for path in sorted(codex_home.glob("state*.sqlite"))
        if path.is_file() and not path.is_symlink()
    ]
    if not databases:
        return identifiers, "missing"
    integrity = "ok"
    for path in databases:
        try:
            database_identifiers, integrity_ok = _sqlite_database_index(path)
            identifiers.update(database_identifiers)
            if not integrity_ok:
                integrity = "failed"
        except sqlite3.Error:
            integrity = "failed"
    return identifiers, integrity


def _session_retention_class(
    *,
    archived: bool,
    age_days: float,
    retention_days: int,
    size: int,
) -> str:
    if size == 0:
        return "CORRUPT"
    if age_days <= retention_days:
        return "KEEP"
    return "REVIEW_REQUIRED" if archived else "ARCHIVE"


def _audit_session_tree(
    root: Path,
    *,
    archived: bool,
    retention_days: int,
    reference_time: float,
    indexed: set[str],
    groups: dict[str, Counter[str]],
    index_counts: Counter[str],
) -> None:
    if not root.is_dir():
        return
    for path in root.rglob("*.jsonl"):
        if path.is_symlink():
            continue
        try:
            metadata = path.stat()
            age_days = max(0.0, (reference_time - metadata.st_mtime) / 86_400)
            retention_class = _session_retention_class(
                archived=archived,
                age_days=age_days,
                retention_days=retention_days,
                size=metadata.st_size,
            )
            groups[retention_class]["count"] += 1
            groups[retention_class]["bytes"] += metadata.st_size
            path_ids = {path.name, *UUID_PATTERN.findall(path.name)}
            index_counts["indexed" if path_ids & indexed else "unindexed"] += 1
        except OSError:
            groups["BLOCKED"]["count"] += 1


def audit_retention(
    codex_home: Path,
    *,
    retention_days: int = DEFAULT_RETENTION_DAYS,
    now: float | None = None,
) -> dict[str, Any]:
    reference_time = time.time() if now is None else now
    indexed, integrity = _sqlite_index(codex_home)
    groups: dict[str, Counter[str]] = {
        name: Counter()
        for name in ("KEEP", "ARCHIVE", "REVIEW_REQUIRED", "CORRUPT", "BLOCKED")
    }
    index_counts: Counter[str] = Counter()
    for directory_name, archived in (
        ("sessions", False),
        ("archived_sessions", True),
    ):
        _audit_session_tree(
            codex_home / directory_name,
            archived=archived,
            retention_days=retention_days,
            reference_time=reference_time,
            indexed=indexed,
            groups=groups,
            index_counts=index_counts,
        )
    policy = {
        "KEEP": {"action": "retain", "restore": "not_required"},
        "ARCHIVE": {
            "action": "supported_archive_after_exact_approval",
            "restore": "verified_backup",
        },
        "REVIEW_REQUIRED": {
            "action": "manual_review_before_any_delete",
            "restore": "verified_backup",
        },
        "CORRUPT": {
            "action": "quarantine_after_exact_approval",
            "restore": "verified_backup",
        },
        "BLOCKED": {
            "action": "resolve_access_or_state_first",
            "restore": "not_applicable",
        },
    }
    return {
        "retention_days": retention_days,
        "groups": {
            name: {
                "count": groups[name]["count"],
                "bytes": groups[name]["bytes"],
                **policy[name],
            }
            for name in groups
        },
        "index_state": dict(sorted(index_counts.items())),
        "sqlite_integrity": integrity,
        "index_repair": (
            "retain_valid_database; audited Codex CLI exposes no supported "
            "reindex command; document upstream limitation"
        ),
        "session_content_read": False,
        "deletion_performed": False,
    }


def _safe_version(executable: Path) -> str:
    try:
        result = subprocess.run(
            [str(executable), "--version"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (OSError, subprocess.SubprocessError):
        return "unavailable"
    value = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    return (
        value[:80]
        if re.fullmatch(r"[A-Za-z0-9 ._+()-]+", value[:80])
        else "unavailable"
    )


def audit_path(codex_home: Path) -> dict[str, Any]:
    del codex_home
    candidates: list[Path] = []
    for entry in os.environ.get("PATH", "").split(os.pathsep):
        if not entry:
            continue
        candidate = Path(entry) / "codex"
        if candidate.is_file() and os.access(candidate, os.X_OK):
            resolved = candidate.resolve()
            if resolved not in candidates:
                candidates.append(resolved)
    managed = Path.home() / ".cache" / "bioetl-codex" / "npm-global" / "bin" / "codex"
    managed_resolved = managed.resolve() if managed.is_file() else None
    selected = candidates[0] if candidates else None
    return {
        "candidate_count": len(candidates),
        "canonical_available": managed_resolved is not None,
        "canonical_wins": bool(selected and selected == managed_resolved),
        "selected_version": _safe_version(selected) if selected else "unavailable",
        "managed_version": (
            _safe_version(managed_resolved) if managed_resolved else "unavailable"
        ),
        "launcher_policy": "managed_linux_first",
        "paths_emitted": False,
    }


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _relative(codex_home: Path, path: Path) -> str:
    return "." if path == codex_home else path.relative_to(codex_home).as_posix()


def create_backup(codex_home: Path, backup_dir: Path) -> dict[str, Any]:
    allowed_root = (codex_home / "backups").resolve()
    resolved_backup = backup_dir.resolve()
    if not resolved_backup.is_relative_to(allowed_root):
        raise ValueError("backup directory must be under the Codex backups directory")
    backup_dir = resolved_backup
    if backup_dir.exists() and any(backup_dir.iterdir()):
        raise ValueError("backup directory must not already contain files")
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(backup_dir, 0o700)

    mode_manifest: list[dict[str, Any]] = []
    for path in _iter_sensitive_nodes(codex_home):
        try:
            mode_manifest.append(
                {
                    "relative": _relative(codex_home, path),
                    "mode": stat.S_IMODE(path.stat().st_mode),
                    "directory": path.is_dir(),
                }
            )
        except OSError:
            continue

    copied: list[dict[str, str]] = []
    for source in _rule_files(codex_home):
        relative = source.relative_to(codex_home)
        destination = backup_dir / "files" / relative
        destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(destination.parent, 0o700)
        shutil.copy2(source, destination)
        os.chmod(destination, 0o600)
        copied.append({"relative": relative.as_posix(), "sha256": _sha256(destination)})

    manifest = {
        "schema_version": SCHEMA_VERSION,
        "mode_manifest": mode_manifest,
        "copied_files": copied,
        "env_files_included": False,
    }
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    verified = all(
        _sha256(backup_dir / "files" / item["relative"]) == item["sha256"]
        for item in copied
    )
    return {
        "copied_files": len(copied),
        "mode_entries": len(mode_manifest),
        "verified": verified,
        "private_directory": stat.S_IMODE(backup_dir.stat().st_mode) == 0o700,
        "paths_emitted": False,
    }


def _rewrite_rules(codex_home: Path) -> dict[str, Any]:
    before = audit_rules(codex_home)
    if before["parse_errors"]:
        raise ValueError("rule parsing failed; refusing to rewrite")
    removed: Counter[str] = Counter()
    for path in _rule_files(codex_home):
        lines = path.read_text(encoding="utf-8").splitlines(keepends=True)
        retained: list[str] = []
        for line in lines:
            parsed = _parse_rule(line.rstrip("\r\n"))
            if parsed is None:
                retained.append(line)
                continue
            disposition, reason = _rule_class(*parsed)
            if disposition == "KEEP":
                retained.append(line)
            else:
                removed[reason] += 1
        with tempfile.NamedTemporaryFile(
            "w",
            encoding="utf-8",
            dir=path.parent,
            prefix=".codex-rules-",
            delete=False,
        ) as stream:
            stream.writelines(retained)
            temporary = Path(stream.name)
        os.chmod(temporary, 0o600)
        temporary.replace(path)
    after = audit_rules(codex_home)
    if after["rules"] > before["rules"]:
        raise RuntimeError("rule count increased unexpectedly")
    return {
        "before": before["rules"],
        "after": after["rules"],
        "removed": before["rules"] - after["rules"],
        "removed_reason_counts": dict(sorted(removed.items())),
        "content_emitted": False,
    }


def _harden_permissions(codex_home: Path) -> dict[str, int]:
    changed = 0
    errors = 0
    for path in _iter_sensitive_nodes(codex_home):
        try:
            expected = _expected_mode(path)
            if stat.S_IMODE(path.stat().st_mode) != expected:
                os.chmod(path, expected)
                changed += 1
        except OSError:
            errors += 1
    return {"changed": changed, "errors": errors}


def apply_remediation(codex_home: Path, backup_dir: Path) -> dict[str, Any]:
    backup = create_backup(codex_home, backup_dir)
    if not backup["verified"]:
        raise RuntimeError("backup verification failed")
    rules = _rewrite_rules(codex_home)
    permissions = _harden_permissions(codex_home)
    after = audit_permissions(codex_home)
    return {
        "backup": backup,
        "rules": rules,
        "permissions": {
            **permissions,
            "unsafe_after": after["unsafe_directories"] + after["unsafe_files"],
        },
        "env_files_touched": False,
        "session_files_deleted": 0,
    }


def restore_backup(codex_home: Path, backup_dir: Path) -> dict[str, Any]:
    allowed_root = (codex_home / "backups").resolve()
    backup_dir = backup_dir.resolve()
    if not backup_dir.is_relative_to(allowed_root):
        raise ValueError("backup directory must be under the Codex backups directory")
    manifest_path = backup_dir / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    restored_files = 0
    for item in manifest.get("copied_files", []):
        relative = Path(item["relative"])
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError("backup manifest contains an unsafe path")
        if _is_env_file(relative):
            raise ValueError("backup unexpectedly contains an env file")
        files_root = (backup_dir / "files").resolve()
        source = (files_root / relative).resolve()
        if not source.is_relative_to(files_root):
            raise ValueError("backup source escapes the private backup root")
        if _sha256(source) != item["sha256"]:
            raise ValueError("backup checksum verification failed")
        destination = (codex_home.resolve() / relative).resolve()
        if not destination.is_relative_to(codex_home.resolve()):
            raise ValueError("backup destination escapes the Codex home")
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)
        restored_files += 1
    restored_modes = 0
    for item in reversed(manifest.get("mode_manifest", [])):
        relative = item["relative"]
        destination = codex_home if relative == "." else codex_home / relative
        if (
            destination.exists()
            and not destination.is_symlink()
            and not _is_env_file(destination)
        ):
            os.chmod(destination, int(item["mode"]))
            restored_modes += 1
    return {
        "restored_files": restored_files,
        "restored_modes": restored_modes,
        "checksums_verified": True,
        "env_files_touched": False,
    }


def collect_audit(codex_home: Path, retention_days: int) -> dict[str, Any]:
    permissions = audit_permissions(codex_home)
    rules = audit_rules(codex_home)
    retention = audit_retention(codex_home, retention_days=retention_days)
    path = audit_path(codex_home)
    hard_failures = permissions["errors"] + rules["parse_errors"]
    unsafe = permissions["unsafe_directories"] + permissions["unsafe_files"]
    risky_rules = sum(
        rules["dispositions"][name] for name in ("NARROW", "REMOVE", "SECRET_REVIEW")
    )
    status = "FAIL" if hard_failures or unsafe or risky_rules else "PASS"
    if status == "PASS" and (
        retention["index_state"].get("unindexed", 0)
        or retention["groups"]["CORRUPT"]["count"]
        or not path["canonical_wins"]
    ):
        status = "WARN"
    return {
        "schema_version": SCHEMA_VERSION,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": status,
        "permissions": permissions,
        "rules": rules,
        "retention": retention,
        "path": path,
        "privacy": {
            "rule_content_emitted": False,
            "session_content_read": False,
            "credentials_emitted": False,
            "user_paths_emitted": False,
            "env_files_touched": False,
        },
    }


def _report_path(requested: Path) -> Path:
    candidate = requested if requested.is_absolute() else REPO_ROOT / requested
    resolved = candidate.resolve()
    quality_root = (REPO_ROOT / "reports/quality").resolve()
    if not resolved.is_relative_to(quality_root) or resolved.suffix != ".json":
        raise ValueError("--output must be a .json file under reports/quality")
    return resolved


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "mode",
        choices=("audit", "retention", "remediate", "restore"),
        nargs="?",
        default="audit",
    )
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    parser.add_argument("--retention-days", type=int, choices=(60, 90), default=90)
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--output", type=Path)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    codex_home = args.codex_home.resolve()
    if not codex_home.is_dir():
        raise SystemExit("Codex home is unavailable")
    if args.mode in {"remediate", "restore"} and not args.apply:
        raise SystemExit(f"{args.mode} requires explicit --apply")
    if args.mode in {"remediate", "restore"} and args.backup_dir is None:
        raise SystemExit(f"{args.mode} requires --backup-dir")

    if args.mode == "audit":
        payload = collect_audit(codex_home, args.retention_days)
    elif args.mode == "retention":
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "DRY_RUN",
            "retention": audit_retention(
                codex_home, retention_days=args.retention_days
            ),
        }
    elif args.mode == "remediate":
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "APPLIED",
            "remediation": apply_remediation(codex_home, args.backup_dir),
        }
    else:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "RESTORED",
            "restore": restore_backup(codex_home, args.backup_dir),
        }

    rendered = json.dumps(payload, indent=2, sort_keys=True) + "\n"
    if args.output:
        output = _report_path(args.output)
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(  # NOSONAR -- _report_path confines under reports/quality
            rendered, encoding="utf-8"
        )
    print(rendered, end="")
    return 1 if payload.get("status") == "FAIL" else 0


if __name__ == "__main__":
    raise SystemExit(main())
