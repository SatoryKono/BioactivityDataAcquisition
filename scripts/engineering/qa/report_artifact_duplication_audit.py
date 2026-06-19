#!/usr/bin/env python3
"""Report exact-byte duplication in non-JSCPD governance artifacts."""

from __future__ import annotations

import argparse
import json
import hashlib
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_JSON_ARTIFACT = Path(
    "reports/quality/config-contract-registry-artifact-duplication.json"
)
TRACKED_EXTENSIONS = frozenset({".csv", ".json", ".md", ".toml", ".yaml", ".yml"})
DEFAULT_INCLUDE_PATTERNS = (
    "configs/**/*.csv",
    "configs/**/*.json",
    "configs/**/*.toml",
    "configs/**/*.yaml",
    "configs/**/*.yml",
    "docs/04-reference/contracts/**/*.md",
    "reports/quality/*contract*.json",
    "reports/quality/*contract*.md",
    "reports/quality/*matrix*.json",
    "reports/quality/*matrix*.md",
    "reports/quality/*ownership*.json",
    "reports/quality/*ownership*.md",
    "reports/quality/*registry*.json",
    "reports/quality/*registry*.md",
    "tests/fixtures/contracts/**/*.json",
    "tests/fixtures/contracts/**/*.yaml",
    "tests/fixtures/contracts/**/*.yml",
    "tests/fixtures/golden/**/*.json",
    "tests/fixtures/golden/**/*.yaml",
    "tests/fixtures/golden/**/*.yml",
)
DEFAULT_EXCLUDE_PATTERNS = (
    DEFAULT_JSON_ARTIFACT.as_posix(),
)
JSCPD_BLIND_SPOT_ANCHORS = (
    "**/configs/**",
    "**/*.yaml",
    "**/*.yml",
    "**/*.json",
    "**/*.md",
)


def _canonical_json(payload: dict[str, Any]) -> str:
    return json.dumps(payload, indent=2, sort_keys=True) + "\n"


def _matches_any(path: str, patterns: tuple[str, ...]) -> bool:
    candidate = Path(path)
    return any(candidate.match(pattern) for pattern in patterns)


def _iter_tracked_paths(
    root: Path,
    *,
    include_patterns: tuple[str, ...],
    exclude_patterns: tuple[str, ...],
) -> list[Path]:
    paths: dict[str, Path] = {}
    for pattern in include_patterns:
        for path in root.glob(pattern):
            if not path.is_file():
                continue
            if path.suffix.lower() not in TRACKED_EXTENSIONS:
                continue
            relative = path.relative_to(root).as_posix()
            if _matches_any(relative, exclude_patterns):
                continue
            paths[relative] = path
    return [paths[key] for key in sorted(paths)]


def classify_artifact_scope(relative_path: str) -> str:
    """Return the primary governance scope for one tracked artifact path."""
    normalized = relative_path.replace("\\", "/")
    if "registry" in normalized:
        return "registry"
    if normalized.startswith("tests/fixtures/contracts/") or "/contracts/" in normalized:
        return "contract"
    if normalized.startswith("configs/"):
        return "config"
    if normalized.startswith("tests/fixtures/golden/"):
        return "golden"
    if "registry" in normalized:
        return "registry"
    if normalized.startswith("reports/quality/"):
        return "quality_report"
    return "artifact"


def collect_artifact_duplication_report(
    root: Path = ROOT,
    *,
    include_patterns: tuple[str, ...] = DEFAULT_INCLUDE_PATTERNS,
    exclude_patterns: tuple[str, ...] = DEFAULT_EXCLUDE_PATTERNS,
) -> dict[str, Any]:
    """Collect exact-byte duplicate groups for JSCPD-excluded governance artifacts."""
    resolved_root = root.resolve()
    groups_by_hash: dict[str, list[str]] = defaultdict(list)
    total_bytes_by_hash: dict[str, int] = defaultdict(int)
    scope_file_counts: Counter[str] = Counter()
    pattern_file_counts: Counter[str] = Counter()

    for path in _iter_tracked_paths(
        resolved_root,
        include_patterns=include_patterns,
        exclude_patterns=exclude_patterns,
    ):
        relative = path.relative_to(resolved_root).as_posix()
        payload = path.read_bytes()
        digest = hashlib.sha256(payload).hexdigest()
        scope = classify_artifact_scope(relative)

        groups_by_hash[digest].append(relative)
        total_bytes_by_hash[digest] += len(payload)
        scope_file_counts[scope] += 1
        for pattern in include_patterns:
            if Path(relative).match(pattern):
                pattern_file_counts[pattern] += 1
                break

    duplicate_groups: list[dict[str, Any]] = []
    duplicate_file_count = 0
    for digest, paths in sorted(
        groups_by_hash.items(),
        key=lambda item: (-len(item[1]), item[0]),
    ):
        if len(paths) < 2:
            continue
        duplicate_file_count += len(paths)
        group_scope_counts = Counter(classify_artifact_scope(path) for path in paths)
        duplicate_groups.append(
            {
                "sha256": digest,
                "file_count": len(paths),
                "total_bytes": total_bytes_by_hash[digest],
                "scope_counts": dict(sorted(group_scope_counts.items())),
                "paths": sorted(paths, key=str.lower),
            }
        )

    return {
        "schema_version": 1,
        "policy_scope": "config_contract_registry_artifact_duplication",
        "scan_root": ".",
        "jscpd_blind_spot_anchors": list(JSCPD_BLIND_SPOT_ANCHORS),
        "tracked_extensions": sorted(TRACKED_EXTENSIONS),
        "include_patterns": list(include_patterns),
        "exclude_patterns": list(exclude_patterns),
        "total_files": sum(scope_file_counts.values()),
        "scope_file_counts": dict(sorted(scope_file_counts.items())),
        "pattern_file_counts": dict(sorted(pattern_file_counts.items())),
        "duplicate_groups": len(duplicate_groups),
        "duplicate_files": duplicate_file_count,
        "max_group_size": max(
            (int(group["file_count"]) for group in duplicate_groups),
            default=0,
        ),
        "groups": duplicate_groups,
    }


def _check_json_artifact(path: Path, payload: dict[str, Any]) -> bool:
    expected = _canonical_json(payload)
    if not path.exists():
        print(f"[drift] missing: {path}")
        return False
    actual = path.read_text(encoding="utf-8")
    if actual == expected:
        return True
    print(f"[drift] mismatch: {path}")
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Report exact-byte duplication for config, contract, and registry "
            "artifacts excluded from JSCPD."
        ),
    )
    parser.add_argument("--root", type=Path, default=ROOT)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--max-duplicate-groups",
        type=int,
        help="Optional reviewed ceiling for exact-byte duplicate groups.",
    )
    args = parser.parse_args(argv)

    report = collect_artifact_duplication_report(args.root)
    json_out = args.json_out
    if args.check and json_out is None:
        candidate = args.root / DEFAULT_JSON_ARTIFACT
        if candidate.exists():
            json_out = candidate

    exit_code = 0
    if (
        args.max_duplicate_groups is not None
        and int(report["duplicate_groups"]) > args.max_duplicate_groups
    ):
        print(
            "[budget] duplicate_groups "
            f"{report['duplicate_groups']} exceeds {args.max_duplicate_groups}"
        )
        exit_code = 1

    if args.check:
        if json_out is not None and not _check_json_artifact(json_out, report):
            exit_code = 1
    elif json_out:
        json_out.parent.mkdir(parents=True, exist_ok=True)
        json_out.write_text(_canonical_json(report), encoding="utf-8")
    else:
        print(_canonical_json(report), end="")

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
