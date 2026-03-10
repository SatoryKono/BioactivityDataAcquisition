#!/usr/bin/env python3
"""Generate and validate scripts inventory metadata.

This tool inventories script entrypoints in:
- scripts/**
- src/tools/**

It classifies each script by discovered call-sites and can:
- update a committed manifest (`--update`)
- verify drift against a manifest (`--check`)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Final

SCRIPT_EXTENSIONS: Final[tuple[str, ...]] = (".py", ".sh", ".ps1", ".cmd", ".bat")
SCRIPT_ROOTS: Final[tuple[str, ...]] = ("scripts", "src/tools")
SEARCH_ROOTS: Final[tuple[str, ...]] = (
    "AGENTS.md",
    ".codex/skills",
    ".github/workflows",
    "pyproject.toml",
    "Makefile",
    "makefile",
    "docs",
    "tests",
    "scripts",
    "src/tools",
)
SKIP_DIR_NAMES: Final[set[str]] = {
    ".git",
    ".venv",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tox",
    ".nox",
    "__pycache__",
    "node_modules",
}
SKIP_PATH_PREFIXES: Final[tuple[str, ...]] = (
    "tests/fixtures/",
    "docs/exports/",
)
SKIP_FILE_EXTENSIONS: Final[set[str]] = {
    ".7z",
    ".avi",
    ".bmp",
    ".doc",
    ".docx",
    ".gif",
    ".gz",
    ".ico",
    ".jpeg",
    ".jpg",
    ".mp3",
    ".mp4",
    ".parquet",
    ".pdf",
    ".png",
    ".tar",
    ".tgz",
    ".wav",
    ".webm",
    ".webp",
    ".whl",
    ".xz",
    ".zip",
}
SCRIPT_PATH_TOKENS: Final[tuple[str, ...]] = ("scripts/", "src/tools/")
SCRIPT_PATH_CANDIDATE_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"(?:scripts|src/tools)/[A-Za-z0-9._/-]+\.(?:py|sh|ps1|cmd|bat)"
)
MANIFEST_DEFAULT: Final[str] = "configs/quality/scripts_inventory_manifest.json"
DEPRECATION_REPORT_DEFAULT: Final[str] = (
    "reports/quality/scripts_deprecation_backlog.md"
)
LIFECYCLE_REGISTRY_DEFAULT: Final[str] = (
    "configs/quality/scripts_lifecycle_registry.json"
)
SCHEMA_VERSION: Final[str] = "1.0"


@dataclass(frozen=True)
class RefEvidence:
    """Reference evidence item for a script."""

    path: str
    line: int
    text: str
    source_group: str


def _project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _iter_scripts(root: Path) -> list[Path]:
    scripts: list[Path] = []
    for rel_root in SCRIPT_ROOTS:
        base = root / rel_root
        if not base.exists():
            continue
        for file_path in base.rglob("*"):
            if not file_path.is_file():
                continue
            if file_path.suffix not in SCRIPT_EXTENSIONS:
                continue
            scripts.append(file_path)
    return sorted(set(scripts))


def _iter_search_files(root: Path) -> list[Path]:
    files: list[Path] = []
    for rel in SEARCH_ROOTS:
        path = root / rel
        if not path.exists():
            continue
        if path.is_file():
            rel_path = path.relative_to(root).as_posix()
            if any(
                rel_path == prefix.rstrip("/") or rel_path.startswith(prefix)
                for prefix in SKIP_PATH_PREFIXES
            ):
                continue
            if path.suffix.lower() in SKIP_FILE_EXTENSIONS:
                continue
            files.append(path)
            continue
        for dirpath, dirnames, filenames in os.walk(path):
            current_path = Path(dirpath)
            rel_dir = current_path.relative_to(root).as_posix()
            rel_dir_prefix = f"{rel_dir}/"
            if any(rel_dir_prefix.startswith(prefix) for prefix in SKIP_PATH_PREFIXES):
                dirnames.clear()
                continue

            dirnames[:] = [name for name in dirnames if name not in SKIP_DIR_NAMES]
            for filename in filenames:
                file_path = current_path / filename
                rel_file = file_path.relative_to(root).as_posix()
                if any(
                    rel_file == prefix.rstrip("/") or rel_file.startswith(prefix)
                    for prefix in SKIP_PATH_PREFIXES
                ):
                    continue
                if file_path.suffix.lower() in SKIP_FILE_EXTENSIONS:
                    continue
                files.append(file_path)
    return sorted(files)


def _source_group(rel_path: str) -> str:
    if rel_path.startswith(".github/workflows/"):
        return "ci"
    if rel_path.startswith(".codex/skills/"):
        return "skills"
    if rel_path in {"Makefile", "makefile", "pyproject.toml"}:
        return "build"
    if rel_path.startswith("tests/"):
        return "tests"
    if rel_path.startswith("docs/"):
        return "docs"
    if rel_path == "AGENTS.md":
        return "agents"
    if rel_path.startswith("scripts/") or rel_path.startswith("src/tools/"):
        return "scripts"
    return "other"


def _discover_refs(root: Path, scripts: list[Path]) -> dict[str, list[RefEvidence]]:
    rel_scripts = [path.relative_to(root).as_posix() for path in scripts]
    script_set = set(rel_scripts)
    refs: dict[str, list[RefEvidence]] = {item: [] for item in rel_scripts}
    search_files = _iter_search_files(root)

    for file_path in search_files:
        rel = file_path.relative_to(root).as_posix()
        try:
            text = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue

        if not any(token in text for token in SCRIPT_PATH_TOKENS):
            continue

        lines = text.splitlines()
        for line_no, line in enumerate(lines, start=1):
            if not any(token in line for token in SCRIPT_PATH_TOKENS):
                continue
            for script_rel in set(SCRIPT_PATH_CANDIDATE_PATTERN.findall(line)):
                if script_rel not in script_set:
                    continue
                if rel == script_rel:
                    continue
                refs[script_rel].append(
                    RefEvidence(
                        path=rel,
                        line=line_no,
                        text=line.strip()[:200],
                        source_group=_source_group(rel),
                    )
                )
    return refs


def _dedupe_refs(refs: list[RefEvidence]) -> list[RefEvidence]:
    seen: set[tuple[str, int, str]] = set()
    result: list[RefEvidence] = []
    for item in refs:
        key = (item.path, item.line, item.text)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return sorted(result, key=lambda item: (item.path, item.line, item.text))


def _status_for(script_rel: str, refs: list[RefEvidence]) -> str:
    if not refs:
        return "legacy" if ("_tmp" in script_rel or "debug_" in script_rel) else "orphan"

    groups = {item.source_group for item in refs}
    if groups & {"ci", "build", "skills", "tests", "scripts", "agents"}:
        return "active"
    if groups == {"docs"}:
        return "unknown"
    return "unknown"


def _agent_usage(refs: list[RefEvidence]) -> list[str]:
    usages: set[str] = set()
    for item in refs:
        if not item.path.startswith(".codex/skills/"):
            continue
        parts = item.path.split("/")
        if len(parts) >= 4:
            usages.add(parts[2])
    return sorted(usages)


def _build_inventory(root: Path) -> dict[str, object]:
    scripts = _iter_scripts(root)
    refs_map = _discover_refs(root, scripts)
    rows: list[dict[str, object]] = []
    status_counts: Counter[str] = Counter()
    group_counts: Counter[str] = Counter()

    for script in scripts:
        script_rel = script.relative_to(root).as_posix()
        refs = _dedupe_refs(refs_map[script_rel])
        status = _status_for(script_rel, refs)
        status_counts[status] += 1
        for group in {item.source_group for item in refs}:
            group_counts[group] += 1

        rows.append(
            {
                "path": script_rel,
                "type": script.suffix.lstrip("."),
                "status": status,
                "agent_usage": _agent_usage(refs),
                "reference_count": len(refs),
                "references": [
                    {
                        "path": item.path,
                        "line": item.line,
                        "source_group": item.source_group,
                        "text": item.text,
                    }
                    for item in refs[:8]
                ],
            }
        )

    rows.sort(key=lambda item: str(item["path"]))
    summary = {
        "total_scripts": len(rows),
        "status_counts": dict(sorted(status_counts.items())),
        "reference_group_coverage": dict(sorted(group_counts.items())),
    }
    return {
        "schema_version": SCHEMA_VERSION,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "summary": summary,
        "scripts": rows,
    }


def _stable_manifest(data: dict[str, object]) -> dict[str, object]:
    normalized = dict(data)
    normalized.pop("generated_at", None)
    return normalized


def _write_manifest(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )


def _check(manifest_path: Path, actual: dict[str, object]) -> int:
    if not manifest_path.exists():
        print(f"[FAIL] Manifest not found: {manifest_path}")
        print("Run with --update to create baseline manifest.")
        return 1

    expected = json.loads(manifest_path.read_text(encoding="utf-8"))
    if _stable_manifest(expected) == _stable_manifest(actual):
        print(f"[OK] Scripts inventory is in sync: {manifest_path}")
        return 0

    print(f"[FAIL] Scripts inventory drift detected: {manifest_path}")
    print("Run with --update to refresh manifest.")
    return 1


def _write_deprecation_report(path: Path, payload: dict[str, object]) -> None:
    scripts = payload["scripts"]
    assert isinstance(scripts, list)

    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for item in scripts:
        assert isinstance(item, dict)
        status = str(item.get("status", "unknown"))
        if status in {"unknown", "orphan", "legacy"}:
            grouped[status].append(item)

    lines = [
        "# Scripts Deprecation Backlog",
        "",
        "Auto-generated from `scripts/check_scripts_inventory.py`.",
        "",
    ]

    for status in ("unknown", "orphan", "legacy"):
        entries = sorted(grouped.get(status, []), key=lambda row: str(row["path"]))
        lines.append(f"## {status} ({len(entries)})")
        lines.append("")
        lines.append("| Script Path | Type | Reference Count | Suggested Next Step |")
        lines.append("|---|---|---:|---|")
        for item in entries:
            path_value = str(item["path"])
            type_value = str(item["type"])
            ref_count = int(item["reference_count"])
            if status == "unknown":
                next_step = "Validate runtime usage; promote to active or mark deprecated."
            elif status == "orphan":
                next_step = "Plan staged removal or add explicit compatibility call-site."
            else:
                next_step = "Archive/remove after freeze window if no active consumers."
            lines.append(
                f"| `{path_value}` | `{type_value}` | {ref_count} | {next_step} |"
            )
        lines.append("")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def _load_json(path: Path) -> dict[str, object]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise ValueError(f"Expected JSON object in {path}")
    return raw


def _check_lifecycle_registry(
    root: Path,
    payload: dict[str, object],
    registry_rel_path: str,
    forbid_evaluate_active: bool,
) -> int:
    registry_path = root / registry_rel_path
    if not registry_path.exists():
        print(f"[FAIL] Lifecycle registry not found: {registry_path}")
        return 1

    try:
        registry = _load_json(registry_path)
    except ValueError as exc:
        print(f"[FAIL] {exc}")
        return 1

    entries_raw = registry.get("entries")
    if not isinstance(entries_raw, dict):
        print(f"[FAIL] Lifecycle registry must contain object field 'entries': {registry_path}")
        return 1

    script_rows = payload["scripts"]
    assert isinstance(script_rows, list)
    script_map: dict[str, dict[str, object]] = {
        str(item["path"]): item for item in script_rows if isinstance(item, dict)
    }

    target_statuses = {"unknown", "orphan", "legacy"}
    missing: list[str] = []
    stale: list[str] = []
    invalid: list[str] = []
    forbidden: list[str] = []

    for path, row in script_map.items():
        status = str(row.get("status", "unknown"))
        if status not in target_statuses:
            continue
        entry = entries_raw.get(path)
        if not isinstance(entry, dict):
            missing.append(path)
            continue
        required = {"owner", "decision", "review_by", "next_step"}
        absent = sorted(required - set(entry.keys()))
        if absent:
            invalid.append(f"{path}: missing fields {absent}")
        if forbid_evaluate_active and str(entry.get("decision")) == "evaluate_active":
            forbidden.append(path)

    for path, entry in entries_raw.items():
        if not isinstance(entry, dict):
            invalid.append(f"{path}: entry must be object")
            continue
        row = script_map.get(path)
        if row is None:
            stale.append(f"{path}: script not found in current inventory")
            continue
        status = str(row.get("status", "unknown"))
        if status not in target_statuses:
            stale.append(f"{path}: status changed to {status}")

    if missing or stale or invalid or forbidden:
        print(f"[FAIL] Lifecycle registry validation failed: {registry_path}")
        if missing:
            print("  Missing entries:")
            for item in missing:
                print(f"    - {item}")
        if forbidden:
            print("  Forbidden decision values (evaluate_active):")
            for item in forbidden:
                print(f"    - {item}")
        if invalid:
            print("  Invalid entries:")
            for item in invalid:
                print(f"    - {item}")
        if stale:
            print("  Stale entries:")
            for item in stale:
                print(f"    - {item}")
        return 1

    print(
        f"[OK] Lifecycle registry covers unknown/orphan/legacy scripts: {registry_path}"
    )
    return 0


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Scripts inventory drift checker")
    parser.add_argument(
        "--manifest",
        default=MANIFEST_DEFAULT,
        help="Path to inventory manifest JSON",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Print generated inventory JSON to stdout",
    )
    parser.add_argument(
        "--update",
        action="store_true",
        help="Write/update manifest file",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate current inventory against manifest file",
    )
    parser.add_argument(
        "--deprecation-report",
        default="",
        help=(
            "Optional path to write markdown backlog for unknown/orphan/legacy scripts. "
            f"Use default path with --deprecation-report={DEPRECATION_REPORT_DEFAULT}"
        ),
    )
    parser.add_argument(
        "--lifecycle-registry",
        default=LIFECYCLE_REGISTRY_DEFAULT,
        help="Path to lifecycle registry JSON for orphan/legacy scripts",
    )
    parser.add_argument(
        "--check-lifecycle",
        action="store_true",
        help="Validate lifecycle registry coverage for unknown/orphan/legacy scripts",
    )
    parser.add_argument(
        "--forbid-evaluate-active",
        action="store_true",
        help="Fail lifecycle validation if any entry has decision=evaluate_active",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    root = _project_root()
    manifest_path = root / args.manifest
    payload = _build_inventory(root)

    if args.update:
        _write_manifest(manifest_path, payload)
        print(f"[OK] Updated scripts inventory manifest: {manifest_path}")

    if args.check:
        result = _check(manifest_path, payload)
        if result != 0:
            return result

    if args.check_lifecycle:
        lifecycle_result = _check_lifecycle_registry(
            root=root,
            payload=payload,
            registry_rel_path=str(args.lifecycle_registry),
            forbid_evaluate_active=bool(args.forbid_evaluate_active),
        )
        if lifecycle_result != 0:
            return lifecycle_result

    report_path_text = str(args.deprecation_report).strip()
    if report_path_text:
        report_path = root / report_path_text
        _write_deprecation_report(report_path, payload)
        print(f"[OK] Updated scripts deprecation report: {report_path}")

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        summary = payload["summary"]
        print(
            "[INFO] scripts={total} active={active} unknown={unknown} orphan={orphan} legacy={legacy}".format(
                total=summary["total_scripts"],
                active=summary["status_counts"].get("active", 0),
                unknown=summary["status_counts"].get("unknown", 0),
                orphan=summary["status_counts"].get("orphan", 0),
                legacy=summary["status_counts"].get("legacy", 0),
            )
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
