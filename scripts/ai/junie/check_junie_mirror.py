#!/usr/bin/env python3
"""Check or sync parity between `.codex/**` (source runtime) and `.junie/**` (mirror runtime).

Governance contract: `scripts/ai/junie/junie-mirror-contract.json`.

Modes:
  --check   Read-only validation. Exit 0 on parity, 1 on drift with a diff report.
  --sync    Copy missing/outdated files from `.codex/**` into `.junie/**`.
            Never writes into `.codex/**`. Preserves Junie runtime-only files
            (`.junie/agents/JUNIE-RUNTIME.md`, `.junie/guidelines.md`).

The two runtime trees are equal-peer canonical sources; `--sync` propagates
in one direction only (codex → junie). Bidirectional parity is a governance
contract, not an automated write policy.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import Any, cast


REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_PATH = REPO_ROOT / "scripts" / "ai" / "junie" / "junie-mirror-contract.json"
CODEX_DIRNAME = ".codex"
JUNIE_DIRNAME = ".junie"
PROFILE_GLOB = "py-*.md"
SKILLS_CATALOG_FILENAME = "SKILLS-CATALOG.md"

type JsonObject = dict[str, Any]

MAPPED_PROFILE_PATTERN = re.compile(r"^\|\s*`(py-[a-z0-9-]+)`\s*\|", re.MULTILINE)


def sha256_of(path: Path) -> str:
    """Return the SHA-256 hex digest of the file at `path`.

    Line endings are normalized to LF so that Windows/POSIX checkouts
    produce identical hashes for text files. Binary files are hashed as-is
    (they will still match if identical bytes are on disk).
    """
    h = hashlib.sha256()
    try:
        data = path.read_bytes()
    except OSError as exc:
        raise RuntimeError(f"cannot read {path}: {exc}") from exc
    normalized = data.replace(b"\r\n", b"\n")
    h.update(normalized)
    return h.hexdigest()


def rel(path: Path) -> str:
    return str(path.relative_to(REPO_ROOT)).replace("\\", "/")


def load_contract() -> JsonObject:
    with CONTRACT_PATH.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"Junie mirror contract must be an object: {CONTRACT_PATH}")
    return cast(JsonObject, payload)


def collect_files(root: Path, exclude_prefixes: Iterable[str] = ()) -> dict[str, Path]:
    """Return {relative_path_from_root: absolute_path} for every regular file under `root`."""
    result: dict[str, Path] = {}
    if not root.exists():
        return result
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        rel_from_root = str(p.relative_to(root)).replace("\\", "/")
        if any(rel_from_root.startswith(prefix) for prefix in exclude_prefixes):
            continue
        result[rel_from_root] = p
    return result


def check_agents(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["agents"]
    codex_dir = REPO_ROOT / CODEX_DIRNAME / "agents"
    junie_dir = REPO_ROOT / JUNIE_DIRNAME / "agents"
    exclude = set(scope.get("exclude_filenames", []))
    codex_files = {p.name for p in codex_dir.glob(PROFILE_GLOB) if p.name not in exclude}
    junie_files = {p.name for p in junie_dir.glob(PROFILE_GLOB)}
    missing_in_junie = sorted(codex_files - junie_files)
    extra_in_junie = sorted(junie_files - codex_files)
    for name in missing_in_junie:
        issues.append(f"[agents] missing in .junie/agents/: {name}")
    for name in extra_in_junie:
        issues.append(f"[agents] unexpected in .junie/agents/: {name}")
    for name in sorted(codex_files & junie_files):
        h_src = sha256_of(codex_dir / name)
        h_mir = sha256_of(junie_dir / name)
        if h_src != h_mir:
            issues.append(
                f"[agents] content drift: .junie/agents/{name} differs from .codex/agents/{name}"
            )


def check_shared_agent_docs(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["shared_agent_docs"]
    for src_rel, mir_rel in zip(
        scope["source_files"], scope["mirror_files"], strict=True
    ):
        src = REPO_ROOT / src_rel
        mir = REPO_ROOT / mir_rel
        if not mir.exists():
            issues.append(f"[shared_agent_docs] missing mirror: {mir_rel}")
            continue
        if not src.exists():
            issues.append(f"[shared_agent_docs] missing source: {src_rel}")
            continue
        if sha256_of(src) != sha256_of(mir):
            issues.append(f"[shared_agent_docs] content drift: {mir_rel} != {src_rel}")


def check_skills_catalog(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["skills_catalog"]
    src = REPO_ROOT / scope["source_file"]
    mir = REPO_ROOT / scope["mirror_file"]
    if not mir.exists():
        issues.append(f"[skills_catalog] missing mirror: {scope['mirror_file']}")
        return
    if not src.exists():
        issues.append(f"[skills_catalog] missing source: {scope['source_file']}")
        return
    if sha256_of(src) != sha256_of(mir):
        issues.append(
            f"[skills_catalog] content drift: {scope['mirror_file']} != {scope['source_file']}"
        )


def check_skills(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["skills"]
    exclude = set(scope.get("exclude_directory_names", []))
    codex_dir = REPO_ROOT / CODEX_DIRNAME / "skills"
    junie_dir = REPO_ROOT / JUNIE_DIRNAME / "skills"
    codex_dirs = {
        p.name for p in codex_dir.iterdir() if p.is_dir() and p.name not in exclude
    }
    junie_dirs = {p.name for p in junie_dir.iterdir() if p.is_dir()}
    missing_in_junie = sorted(codex_dirs - junie_dirs)
    extra_in_junie = sorted(junie_dirs - codex_dirs)
    for name in missing_in_junie:
        issues.append(f"[skills] missing in .junie/skills/: {name}/")
    for name in extra_in_junie:
        issues.append(f"[skills] unexpected in .junie/skills/: {name}/")


def check_skill_contents(contract: JsonObject, issues: list[str]) -> None:
    scope = contract["parity_scope"]["skill_contents"]
    exclude_prefixes = tuple(scope.get("exclude_relative_path_prefixes", []))
    codex_dir = REPO_ROOT / CODEX_DIRNAME / "skills"
    junie_dir = REPO_ROOT / JUNIE_DIRNAME / "skills"
    codex_files = collect_files(codex_dir, exclude_prefixes)
    junie_files = collect_files(junie_dir, exclude_prefixes)
    # SKILLS-CATALOG.md is handled by check_skills_catalog(); skip here to avoid
    # duplicate reporting.
    codex_files.pop(SKILLS_CATALOG_FILENAME, None)
    junie_files.pop(SKILLS_CATALOG_FILENAME, None)
    missing_in_junie = sorted(set(codex_files) - set(junie_files))
    extra_in_junie = sorted(set(junie_files) - set(codex_files))
    for rel_path in missing_in_junie:
        issues.append(f"[skill_contents] missing in .junie/skills/: {rel_path}")
    for rel_path in extra_in_junie:
        issues.append(f"[skill_contents] unexpected in .junie/skills/: {rel_path}")
    for rel_path in sorted(set(codex_files) & set(junie_files)):
        h_src = sha256_of(codex_files[rel_path])
        h_mir = sha256_of(junie_files[rel_path])
        if h_src != h_mir:
            issues.append(f"[skill_contents] content drift: .junie/skills/{rel_path}")


def check_runtime_only_files(contract: JsonObject, issues: list[str]) -> None:
    ro = contract["runtime_only_files"]
    for path_str in ro["codex_only"]:
        if not (REPO_ROOT / path_str).exists():
            issues.append(f"[runtime_only] missing codex_only file: {path_str}")
    for path_str in ro["junie_only"]:
        if not (REPO_ROOT / path_str).exists():
            issues.append(f"[runtime_only] missing junie_only file: {path_str}")


def check_runtime_semantics(contract: JsonObject, issues: list[str]) -> None:
    """Validate semantic parity for runtime-specific Junie entry points."""
    scope = contract.get("runtime_semantics")
    if not isinstance(scope, dict):
        issues.append("[runtime_semantics] missing runtime_semantics contract")
        return

    agents_scope = contract["parity_scope"]["agents"]
    excluded_profiles = set(agents_scope.get("exclude_filenames", []))
    expected_profiles = {
        path.stem
        for path in (REPO_ROOT / CODEX_DIRNAME / "agents").glob(PROFILE_GLOB)
        if path.name not in excluded_profiles
    }

    runtime_map_rel = scope["junie_runtime_map"]
    guidelines_rel = scope["junie_guidelines"]
    runtime_map = REPO_ROOT / runtime_map_rel
    guidelines = REPO_ROOT / guidelines_rel
    if not runtime_map.exists() or not guidelines.exists():
        return

    runtime_text = runtime_map.read_text(encoding="utf-8")
    guidelines_text = guidelines.read_text(encoding="utf-8")
    mapped_profiles = set(MAPPED_PROFILE_PATTERN.findall(runtime_text))
    for profile in sorted(expected_profiles - mapped_profiles):
        issues.append(f"[runtime_semantics] missing Junie profile mapping: {profile}")
    for profile in sorted(mapped_profiles - expected_profiles):
        issues.append(f"[runtime_semantics] phantom Junie profile mapping: {profile}")

    governed_texts = {
        runtime_map_rel: runtime_text,
        guidelines_rel: guidelines_text,
    }
    for identifier in scope.get("forbidden_identifiers", []):
        for path_str, content in governed_texts.items():
            if identifier in content:
                issues.append(
                    f"[runtime_semantics] forbidden identifier {identifier!r} in {path_str}"
                )

    for skill_name in scope.get("required_dashboard_skills", []):
        skill_ref = f".junie/skills/{skill_name}/"
        if skill_ref not in guidelines_text:
            issues.append(
                f"[runtime_semantics] missing dashboard skill reference: {skill_ref}"
            )


def do_check(contract: JsonObject) -> int:
    issues: list[str] = []
    check_agents(contract, issues)
    check_shared_agent_docs(contract, issues)
    check_skills_catalog(contract, issues)
    check_skills(contract, issues)
    check_skill_contents(contract, issues)
    check_runtime_only_files(contract, issues)
    check_runtime_semantics(contract, issues)
    if issues:
        print("Junie mirror parity FAILED:", file=sys.stderr)
        for line in issues:
            print(f"  - {line}", file=sys.stderr)
        print(
            f"\nTotal drift entries: {len(issues)}.\n"
            "Run `bash scripts/ai/junie/check_junie_mirror.sh --sync` to sync .codex -> .junie.",
            file=sys.stderr,
        )
        return 1
    print(
        "Junie mirror parity OK: .codex/** == .junie/** (per junie-mirror-contract.json)."
    )
    return 0


def _sync_agents(scope: JsonObject) -> None:
    codex_agents = REPO_ROOT / CODEX_DIRNAME / "agents"
    junie_agents = REPO_ROOT / JUNIE_DIRNAME / "agents"
    junie_agents.mkdir(parents=True, exist_ok=True)
    exclude_agents = set(scope["agents"].get("exclude_filenames", []))
    source_names: set[str] = set()
    for source in codex_agents.glob(PROFILE_GLOB):
        if source.name in exclude_agents:
            continue
        source_names.add(source.name)
        shutil.copy2(source, junie_agents / source.name)
    for stray in junie_agents.glob(PROFILE_GLOB):
        if stray.name not in source_names:
            stray.unlink()


def _sync_shared_agent_docs(scope: JsonObject) -> None:
    for source_relative, mirror_relative in zip(
        scope["shared_agent_docs"]["source_files"],
        scope["shared_agent_docs"]["mirror_files"],
        strict=True,
    ):
        source = REPO_ROOT / source_relative
        mirror = REPO_ROOT / mirror_relative
        mirror.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, mirror)


def _sync_skills_catalog(scope: JsonObject) -> Path:
    catalog = scope["skills_catalog"]
    junie_skills = REPO_ROOT / JUNIE_DIRNAME / "skills"
    junie_skills.mkdir(parents=True, exist_ok=True)
    shutil.copy2(
        REPO_ROOT / catalog["source_file"],
        REPO_ROOT / catalog["mirror_file"],
    )
    return junie_skills


def _remove_excluded_skill_dirs(
    junie_skills: Path,
    exclude_skill_dirs: set[str],
) -> None:
    for excluded in exclude_skill_dirs:
        stale_dir = junie_skills / excluded
        if stale_dir.exists():
            shutil.rmtree(stale_dir)


def _copy_skill_contents(
    codex_files: dict[str, Path],
    junie_skills: Path,
    exclude_skill_dirs: set[str],
) -> None:
    for relative, source in codex_files.items():
        if relative.split("/", 1)[0] in exclude_skill_dirs:
            continue
        destination = junie_skills / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)


def _remove_stray_skill_contents(
    codex_files: dict[str, Path],
    junie_files: dict[str, Path],
    junie_skills: Path,
    exclude_skill_dirs: set[str],
) -> None:
    for relative in set(junie_files) - set(codex_files):
        if relative.split("/", 1)[0] not in exclude_skill_dirs:
            (junie_skills / relative).unlink()


def _remove_empty_directories(root: Path) -> None:
    directories = sorted(
        (path for path in root.rglob("*") if path.is_dir()),
        key=lambda path: len(path.parts),
        reverse=True,
    )
    for directory in directories:
        try:
            directory.rmdir()
        except OSError:
            pass


def _sync_skill_contents(scope: JsonObject, junie_skills: Path) -> None:
    codex_skills = REPO_ROOT / CODEX_DIRNAME / "skills"
    exclude_skill_dirs = set(scope["skills"].get("exclude_directory_names", []))
    exclude_prefixes = tuple(
        scope["skill_contents"].get("exclude_relative_path_prefixes", [])
    )
    _remove_excluded_skill_dirs(junie_skills, exclude_skill_dirs)
    codex_files = collect_files(codex_skills, exclude_prefixes)
    codex_files.pop(SKILLS_CATALOG_FILENAME, None)
    _copy_skill_contents(codex_files, junie_skills, exclude_skill_dirs)
    junie_files = collect_files(junie_skills, exclude_prefixes)
    junie_files.pop(SKILLS_CATALOG_FILENAME, None)
    _remove_stray_skill_contents(
        codex_files,
        junie_files,
        junie_skills,
        exclude_skill_dirs,
    )
    _remove_empty_directories(junie_skills)


def do_sync(contract: JsonObject) -> int:
    """One-way sync .codex → .junie for every file under parity scope.

    Never writes into `.codex/**`. Preserves Junie runtime-only files.
    """
    scope = contract["parity_scope"]
    _sync_agents(scope)
    _sync_shared_agent_docs(scope)
    junie_skills = _sync_skills_catalog(scope)
    _sync_skill_contents(scope, junie_skills)
    print("Junie mirror sync complete (.codex -> .junie).")
    print("Re-running --check to validate final state...")
    return do_check(contract)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--check", action="store_true", help="read-only parity check")
    group.add_argument(
        "--sync", action="store_true", help="copy .codex/** into .junie/**"
    )
    args = parser.parse_args()
    contract = load_contract()
    if args.check:
        return do_check(contract)
    if args.sync:
        return do_sync(contract)
    return 2


if __name__ == "__main__":
    sys.exit(main())
