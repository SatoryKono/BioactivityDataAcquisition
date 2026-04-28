#!/usr/bin/env python3
"""Shared root-governance helpers for structure audits and cleanup tooling."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any

import yaml

ALLOWLIST_FILE = Path(".github/root-allowlist.txt")
STRUCTURE_CATALOG_FILE = Path("configs/quality/repo_structure_catalog.yaml")

BASE_ALLOWED_ROOT_DIRECTORIES: frozenset[str] = frozenset(
    {
        ".ai",
        ".aiassistant",
        "ai",
        ".codex",
        ".cursor",
        ".gemini",
        ".github",
        ".idea",
        ".jules",
        ".junie",
        ".sonarlint",
        ".vibe",
        ".vscode",
        "script-codex",
        "script-gemini",
        "script-mistrall",
        "script-mistrallvibe",
        "assets",
        "configs",
        "data",
        "docs",
        "grafana",
        "reports",
        "scripts",
        "src",
        "tests",
    }
)

REQUIRED_STRUCTURE_CATALOG_SECTIONS: frozenset[str] = frozenset(
    {
        "blocked_cleanup_zones",
        "docs_drafts",
        "plans",
        "src_sidecars",
    }
)


@dataclass(frozen=True)
class RootGovernancePolicy:
    """Machine-readable root governance model for the repository."""

    catalog: dict[str, Any]
    allowed_root_files: frozenset[str]
    approved_root_directories: frozenset[str]
    blocked_cleanup_paths: frozenset[str]


def collect_cataloged_paths(
    entries: list[dict[str, Any]], *, field_name: str = "path"
) -> set[str]:
    """Return normalized path set from catalog entries."""
    cataloged: set[str] = set()
    for entry in entries:
        path = entry.get(field_name)
        if not isinstance(path, str) or not path:
            raise RuntimeError(
                f"Structure catalog entry must contain non-empty '{field_name}'"
            )
        cataloged.add(path)
    return cataloged


def load_structure_catalog(repo_root: Path) -> dict[str, Any]:
    """Load machine-readable structure governance catalog."""
    catalog_path = repo_root / STRUCTURE_CATALOG_FILE
    if not catalog_path.exists():
        raise RuntimeError(f"Structure catalog does not exist: {catalog_path}")

    with catalog_path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}

    missing_sections = sorted(
        section
        for section in REQUIRED_STRUCTURE_CATALOG_SECTIONS
        if section not in payload
    )
    if missing_sections:
        missing = ", ".join(missing_sections)
        raise RuntimeError(f"Structure catalog missing required sections: {missing}")
    return payload


def load_allowed_root_files(repo_root: Path) -> frozenset[str]:
    """Load canonical root-file allowlist from .github/root-allowlist.txt."""
    allowlist_path = repo_root / ALLOWLIST_FILE
    if not allowlist_path.exists():
        raise RuntimeError(f"Allowlist file does not exist: {allowlist_path}")

    entries: set[str] = set()
    with allowlist_path.open("r", encoding="utf-8") as handle:
        for line in handle:
            cleaned = line.strip()
            if not cleaned or cleaned.startswith("#"):
                continue
            if "/" in cleaned:
                raise RuntimeError(
                    "Root allowlist must contain only root-level file names "
                    f"(invalid entry: {cleaned})"
                )
            entries.add(cleaned)

    if not entries:
        raise RuntimeError(f"Allowlist is empty: {allowlist_path}")
    return frozenset(entries)


def approved_root_directories(catalog: dict[str, Any]) -> frozenset[str]:
    """Return allowed root directories from shared baseline and catalog policy."""
    approved_dirs: set[str] = set(BASE_ALLOWED_ROOT_DIRECTORIES)
    for section_name in ("root_tooling_roots", "test_support_roots"):
        section = catalog.get(section_name)
        if not isinstance(section, dict):
            continue
        approved_dirs.update(collect_cataloged_paths(section.get("approved_roots", [])))
    return frozenset(approved_dirs)


def blocked_cleanup_paths(catalog: dict[str, Any]) -> frozenset[str]:
    """Return blocked cleanup zones from the structure catalog."""
    return frozenset(collect_cataloged_paths(catalog["blocked_cleanup_zones"]))


def load_root_governance_policy(repo_root: Path) -> RootGovernancePolicy:
    """Load the full root-governance policy model for a repository root."""
    catalog = load_structure_catalog(repo_root)
    return RootGovernancePolicy(
        catalog=catalog,
        allowed_root_files=load_allowed_root_files(repo_root),
        approved_root_directories=approved_root_directories(catalog),
        blocked_cleanup_paths=blocked_cleanup_paths(catalog),
    )


def is_within_blocked_cleanup_zone(
    path: str | Path,
    blocked_paths: frozenset[str],
) -> bool:
    """Return True when a relative path falls under a blocked cleanup zone."""
    path_text = path.as_posix() if isinstance(path, Path) else path
    normalized = PurePosixPath(path_text)
    if str(normalized) in {"", "."}:
        return False
    for blocked in blocked_paths:
        blocked_path = PurePosixPath(blocked)
        if normalized == blocked_path or blocked_path in normalized.parents:
            return True
    return False
