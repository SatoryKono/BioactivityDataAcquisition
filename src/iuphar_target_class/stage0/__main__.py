"""Publish TC-01 stage-0 artifacts from a survey file."""

from __future__ import annotations

import argparse
from pathlib import Path

from .build import publish_stage0


def main(argv: list[str] | None = None) -> int:
    """Write the stage-0 bundle. Originals named by the survey are only read."""
    parser = argparse.ArgumentParser(description="Publish TC-01 stage-0 artifacts")
    parser.add_argument("--repo-root", type=Path, required=True)
    parser.add_argument("--survey", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    publish_stage0(args.repo_root, args.survey, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
