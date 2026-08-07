#!/usr/bin/env python3
"""Audit, apply, and restore benchmark-selected local Codex model profiles."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import stat
import sys
import tempfile
from pathlib import Path
from typing import Any, Final

REPO_ROOT: Final = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.ai.codex.profile_benchmark import PROFILES

SCHEMA_VERSION: Final = "bioetl-codex-profile-config-v1"
PROFILE_FILES: Final = {
    "default": ("config.toml", "balanced"),
    "fast": ("fast.config.toml", "fast"),
    "balanced": ("balanced.config.toml", "balanced"),
    "deep": ("deep.config.toml", "deep"),
}
MODEL_KEYS: Final = ("model", "model_reasoning_effort")
TOP_LEVEL_ASSIGNMENT: Final = re.compile(
    r'^(model|model_reasoning_effort)\s*=\s*"([^"]*)"\s*$'
)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _expected(profile_name: str) -> dict[str, str]:
    profile = PROFILES[profile_name]
    return {
        "model": profile.model,
        "model_reasoning_effort": profile.reasoning_effort,
    }


def _top_level_values(content: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in content.splitlines():
        if line.lstrip().startswith("["):
            break
        match = TOP_LEVEL_ASSIGNMENT.fullmatch(line.strip())
        if match:
            key, value = match.groups()
            if key in values:
                raise ValueError(f"duplicate top-level {key!r}")
            values[key] = value
    return values


def _render_profile(content: str, profile_name: str) -> str:
    expected = _expected(profile_name)
    lines = content.splitlines()
    section_index = next(
        (index for index, line in enumerate(lines) if line.lstrip().startswith("[")),
        len(lines),
    )
    seen: set[str] = set()
    rendered_prefix: list[str] = []
    for line in lines[:section_index]:
        match = TOP_LEVEL_ASSIGNMENT.fullmatch(line.strip())
        if match is None:
            rendered_prefix.append(line)
            continue
        key = match.group(1)
        if key in seen:
            raise ValueError(f"duplicate top-level {key!r}")
        seen.add(key)
        rendered_prefix.append(f'{key} = "{expected[key]}"')
    for key in MODEL_KEYS:
        if key not in seen:
            rendered_prefix.append(f'{key} = "{expected[key]}"')
    suffix = lines[section_index:]
    if suffix and rendered_prefix and rendered_prefix[-1].strip():
        rendered_prefix.append("")
    return "\n".join([*rendered_prefix, *suffix]).rstrip() + "\n"


def audit_profiles(codex_home: Path) -> dict[str, Any]:
    profiles: dict[str, dict[str, Any]] = {}
    for logical_name, (filename, profile_name) in PROFILE_FILES.items():
        path = codex_home / filename
        values: dict[str, str] = {}
        readable = False
        if path.is_file() and not path.is_symlink():
            try:
                values = _top_level_values(path.read_text(encoding="utf-8"))
                readable = True
            except (OSError, UnicodeError, ValueError):
                readable = False
        expected = _expected(profile_name)
        profiles[logical_name] = {
            "exists": path.is_file() and not path.is_symlink(),
            "readable": readable,
            "model": values.get("model", "missing"),
            "model_reasoning_effort": values.get(
                "model_reasoning_effort", "missing"
            ),
            "expected_model": expected["model"],
            "expected_reasoning_effort": expected["model_reasoning_effort"],
            "matches_benchmark": readable and values == expected,
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "profiles": profiles,
        "paths_emitted": False,
        "credentials_emitted": False,
        "env_files_touched": False,
    }


def _validate_backup_dir(codex_home: Path, backup_dir: Path) -> Path:
    allowed_root = (codex_home / "backups").resolve()
    resolved = backup_dir.resolve()
    if not resolved.is_relative_to(allowed_root):
        raise ValueError("backup directory must be under the Codex backups directory")
    return resolved


def create_backup(codex_home: Path, backup_dir: Path) -> dict[str, Any]:
    _validate_backup_dir(codex_home, backup_dir)
    if backup_dir.exists() and any(backup_dir.iterdir()):
        raise ValueError("backup directory must not already contain files")
    backup_dir.mkdir(parents=True, exist_ok=True, mode=0o700)
    os.chmod(backup_dir, 0o700)
    copied: list[dict[str, Any]] = []
    for filename, _profile_name in PROFILE_FILES.values():
        source = codex_home / filename
        entry: dict[str, Any] = {"filename": filename, "existed": False}
        if source.is_symlink():
            raise ValueError("profile config symlinks are not supported")
        if source.is_file():
            destination = backup_dir / "files" / filename
            destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(destination.parent, 0o700)
            shutil.copy2(source, destination)
            os.chmod(destination, 0o600)
            entry.update({"existed": True, "sha256": _sha256(destination)})
        copied.append(entry)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "files": copied,
        "env_files_included": False,
    }
    manifest_path = backup_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    os.chmod(manifest_path, 0o600)
    verified = all(
        not entry["existed"]
        or _sha256(backup_dir / "files" / entry["filename"])
        == entry["sha256"]
        for entry in copied
    )
    return {
        "files_recorded": len(copied),
        "existing_files_copied": sum(entry["existed"] for entry in copied),
        "verified": verified,
        "private_directory": stat.S_IMODE(backup_dir.stat().st_mode) == 0o700,
        "paths_emitted": False,
    }


def _write_private(path: Path, content: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        dir=path.parent,
        prefix=".codex-profile-",
        delete=False,
    ) as stream:
        stream.write(content)
        temporary = Path(stream.name)
    os.chmod(temporary, 0o600)
    os.replace(temporary, path)


def apply_profiles(codex_home: Path, backup_dir: Path) -> dict[str, Any]:
    backup = create_backup(codex_home, backup_dir)
    if not backup["verified"]:
        raise RuntimeError("profile backup verification failed")
    for _logical_name, (filename, profile_name) in PROFILE_FILES.items():
        path = codex_home / filename
        content = path.read_text(encoding="utf-8") if path.is_file() else ""
        _write_private(path, _render_profile(content, profile_name))
    after = audit_profiles(codex_home)
    matches = all(
        profile["matches_benchmark"] for profile in after["profiles"].values()
    )
    return {
        "backup": backup,
        "all_profiles_match": matches,
        "profile_count": len(PROFILE_FILES),
        "default_profile": "balanced",
        "agents_max_threads_changed": False,
        "env_files_touched": False,
    }


def restore_profiles(codex_home: Path, backup_dir: Path) -> dict[str, Any]:
    _validate_backup_dir(codex_home, backup_dir)
    manifest = json.loads((backup_dir / "manifest.json").read_text(encoding="utf-8"))
    restored = 0
    removed_new = 0
    for entry in manifest.get("files", []):
        filename = entry.get("filename")
        allowed = {item[0] for item in PROFILE_FILES.values()}
        if filename not in allowed:
            raise ValueError("backup manifest contains an unexpected file")
        destination = codex_home / filename
        if entry.get("existed"):
            source = backup_dir / "files" / filename
            if _sha256(source) != entry.get("sha256"):
                raise ValueError("profile backup checksum verification failed")
            _write_private(destination, source.read_text(encoding="utf-8"))
            restored += 1
        elif destination.exists():
            destination.unlink()
            removed_new += 1
    return {
        "restored_files": restored,
        "removed_new_files": removed_new,
        "checksums_verified": True,
        "env_files_touched": False,
    }


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("audit", "apply", "restore"), nargs="?", default="audit")
    parser.add_argument(
        "--codex-home",
        type=Path,
        default=Path(os.environ.get("CODEX_HOME", Path.home() / ".codex")),
    )
    parser.add_argument("--backup-dir", type=Path)
    parser.add_argument("--confirm", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    codex_home = args.codex_home.resolve()
    if not codex_home.is_dir():
        raise SystemExit("Codex home is unavailable")
    if args.mode in {"apply", "restore"} and not args.confirm:
        raise SystemExit(f"{args.mode} requires explicit --confirm")
    if args.mode in {"apply", "restore"} and args.backup_dir is None:
        raise SystemExit(f"{args.mode} requires --backup-dir")

    os.umask(0o077)
    if args.mode == "audit":
        payload = {"status": "AUDIT", **audit_profiles(codex_home)}
    elif args.mode == "apply":
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "APPLIED",
            "result": apply_profiles(codex_home, args.backup_dir),
        }
    else:
        payload = {
            "schema_version": SCHEMA_VERSION,
            "status": "RESTORED",
            "result": restore_profiles(codex_home, args.backup_dir),
        }
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
