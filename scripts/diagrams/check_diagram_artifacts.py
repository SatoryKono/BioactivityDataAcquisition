#!/usr/bin/env python3
"""Validate rendered diagram artifacts for smoke baseline set.

Checks:
- DIAG-T010: required SVG artifacts exist
- DIAG-T011: PNG compatibility artifacts exist when explicitly required
- DIAG-T012: required artifacts are non-empty
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from .diagram_paths import VISUAL_SMOKE_MANIFEST
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import VISUAL_SMOKE_MANIFEST


DEFAULT_MANIFEST = VISUAL_SMOKE_MANIFEST


@dataclass(frozen=True)
class ArtifactIssue:
    file: str
    kind: str
    message: str


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _err(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def load_manifest(manifest_path: Path) -> list[Path]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    paths: list[Path] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        path = Path(line)
        if path.suffix.lower() != ".svg":
            raise ValueError(f"Manifest must contain SVG paths only: {line}")
        paths.append(path)

    if not paths:
        raise ValueError(f"Manifest is empty: {manifest_path}")

    return paths


def to_png_path(svg_path: Path) -> Path:
    parts = list(svg_path.parts)
    try:
        svg_idx = parts.index("svg")
    except ValueError:
        raise ValueError(
            f"Cannot derive PNG path (missing '/svg/' segment): {svg_path}"
        ) from None

    parts[svg_idx] = "png"
    return Path(*parts).with_suffix(".png")


def validate_artifacts(
    repo_root: Path, svg_rel_paths: list[Path], *, require_png: bool = False
) -> list[ArtifactIssue]:
    issues: list[ArtifactIssue] = []

    for svg_rel in svg_rel_paths:
        svg_abs = repo_root / svg_rel
        png_rel = to_png_path(svg_rel)
        png_abs = repo_root / png_rel

        if not svg_abs.exists():
            issues.append(
                ArtifactIssue(
                    file=str(svg_rel),
                    kind="DIAG-T010",
                    message="SVG artifact is missing",
                )
            )
        elif svg_abs.stat().st_size <= 0:
            issues.append(
                ArtifactIssue(
                    file=str(svg_rel),
                    kind="DIAG-T012",
                    message="SVG artifact is empty",
                )
            )

        if require_png:
            if not png_abs.exists():
                issues.append(
                    ArtifactIssue(
                        file=str(png_rel),
                        kind="DIAG-T011",
                        message="PNG compatibility artifact is missing",
                    )
                )
            elif png_abs.stat().st_size <= 0:
                issues.append(
                    ArtifactIssue(
                        file=str(png_rel),
                        kind="DIAG-T012",
                        message="PNG compatibility artifact is empty",
                    )
                )

    return issues


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate diagram render artifacts (SVG required, PNG optional)"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Path to SVG manifest (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--require-png",
        action="store_true",
        help="Also require derived PNG compatibility artifacts for manifest entries",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON report",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    repo_root = Path.cwd()
    manifest = (
        args.manifest if args.manifest.is_absolute() else repo_root / args.manifest
    )

    try:
        svg_paths = load_manifest(manifest)
    except (FileNotFoundError, ValueError) as exc:
        _err(f"[ERROR] {exc}")
        return 2

    issues = validate_artifacts(repo_root, svg_paths, require_png=args.require_png)

    if args.json:
        _out(
            json.dumps(
                {
                    "ok": not issues,
                    "checked": len(svg_paths),
                    "require_png": args.require_png,
                    "issues": [asdict(issue) for issue in issues],
                },
                ensure_ascii=True,
                indent=2,
            )
        )
    else:
        mode = "SVG+PNG compatibility" if args.require_png else "SVG primary"
        _out(f"[INFO] Checked artifact entries: {len(svg_paths)} ({mode})")

    if issues:
        _err("[ERROR] Diagram artifact validation failed:")
        for issue in issues:
            _err(f"  - {issue.kind} {issue.file}: {issue.message}")
        return 1

    if not args.json:
        _out("[OK] Diagram artifact validation passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
