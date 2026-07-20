#!/usr/bin/env python3
"""Generate source-backed diagrams and field inventories for entity pipelines."""

from __future__ import annotations

import argparse
import os
import sys
import tempfile
from pathlib import Path

from scripts.diagrams.pipeline_dataflow_ir import build_pipeline_dataflow_ir
from scripts.diagrams.pipeline_dataflow_render import render_text_outputs

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DIAGRAM_DIR = PROJECT_ROOT / "docs/02-architecture/diagrams/architecture"
DEFAULT_DESCRIPTION_DIR = (
    PROJECT_ROOT / "docs/02-architecture/diagrams/descriptions/architecture"
)
DEFAULT_ARTIFACT_ROOT = (
    PROJECT_ROOT / "docs/02-architecture/generated/pipeline-dataflows"
)
SUPPORTED_PIPELINES = ("chembl_activity",)


def _absolute(path: Path) -> Path:
    return path if path.is_absolute() else PROJECT_ROOT / path


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        dir=path.parent,
        text=True,
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as handle:
            handle.write(content)
        os.replace(temp_name, path)
    except BaseException:
        Path(temp_name).unlink(missing_ok=True)
        raise


def _check_outputs(outputs: dict[Path, str]) -> list[Path]:
    stale: list[Path] = []
    for path, expected in outputs.items():
        if not path.is_file() or path.read_text(encoding="utf-8") != expected:
            stale.append(path)
    return stale


def build_outputs(args: argparse.Namespace) -> dict[Path, str]:
    """Build the complete destination-to-content map for parsed CLI args."""
    pipeline_name = str(args.pipeline)
    ir = build_pipeline_dataflow_ir(
        pipeline_name,
        configs_root=_absolute(args.configs_root),
    )
    return render_text_outputs(
        ir,
        diagram_dir=_absolute(args.diagram_dir),
        description_dir=_absolute(args.description_dir),
        artifact_dir=_absolute(args.artifact_root) / pipeline_name,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate deterministic Mermaid views, a pipeline passport, JSON IR, "
            "and a Silver/Gold field CSV."
        )
    )
    parser.add_argument(
        "--pipeline",
        choices=SUPPORTED_PIPELINES,
        default="chembl_activity",
        help="Registered pipeline to document (default: chembl_activity).",
    )
    parser.add_argument(
        "--configs-root",
        type=Path,
        default=Path("configs"),
        help="Configuration root (default: configs).",
    )
    parser.add_argument(
        "--diagram-dir",
        type=Path,
        default=DEFAULT_DIAGRAM_DIR,
        help="Destination for canonical Mermaid sources.",
    )
    parser.add_argument(
        "--description-dir",
        type=Path,
        default=DEFAULT_DESCRIPTION_DIR,
        help="Destination for governed diagram description cards.",
    )
    parser.add_argument(
        "--artifact-root",
        type=Path,
        default=DEFAULT_ARTIFACT_ROOT,
        help="Root destination for per-pipeline companion artifacts.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Fail if committed generated text differs from live inputs.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        outputs = build_outputs(args)
    except Exception as exc:
        print(
            f"Unable to build pipeline dataflow artifacts for {args.pipeline}: {exc}",
            file=sys.stderr,
        )
        return 1
    if args.check:
        stale = _check_outputs(outputs)
        if stale:
            print("Pipeline dataflow artifacts are stale or missing:", file=sys.stderr)
            for path in stale:
                try:
                    display = path.relative_to(PROJECT_ROOT)
                except ValueError:
                    display = path
                print(f"  - {display}", file=sys.stderr)
            print(
                "Run: python -m scripts.diagrams generate-dataflows "
                f"--pipeline {args.pipeline}",
                file=sys.stderr,
            )
            return 1
        print(f"Pipeline dataflow artifacts are current: {args.pipeline}")
        return 0

    for path, content in outputs.items():
        _atomic_write(path, content)
    print(f"Generated {len(outputs)} text artifacts for {args.pipeline}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
