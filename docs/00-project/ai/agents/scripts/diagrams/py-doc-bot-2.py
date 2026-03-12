#!/usr/bin/env python3
"""Generate *-with-descriptions.docx documents from Markdown bundles."""

from __future__ import annotations

import argparse
import shutil
import subprocess
from pathlib import Path


def _resolve_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[0]


REPO_ROOT = _resolve_repo_root()
DEFAULT_INPUTS = [
    Path("docs/02-architecture/mmd-diagrams/class-diagrams-with-descriptions.md"),
    Path("docs/02-architecture/mmd-diagrams/foundation-diagrams-with-descriptions.md"),
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build with-descriptions DOCX files from Markdown using Pandoc. "
            "By default generates class/foundation bundles."
        )
    )
    parser.add_argument(
        "--input-md",
        action="append",
        default=[],
        help="Input markdown file (repeatable). Defaults to class/foundation bundles.",
    )
    parser.add_argument(
        "--reference-doc",
        type=Path,
        default=None,
        help="Optional Pandoc reference docx for style inheritance.",
    )
    return parser.parse_args()


def resolve_inputs(raw_inputs: list[str]) -> list[Path]:
    paths = [Path(item) for item in raw_inputs] if raw_inputs else DEFAULT_INPUTS
    resolved: list[Path] = []
    for path in paths:
        resolved.append(path if path.is_absolute() else REPO_ROOT / path)
    return resolved


def run(cmd: list[str]) -> None:
    completed = subprocess.run(cmd, capture_output=True, text=True)
    if completed.returncode == 0:
        return
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    details = stderr or stdout or "(no output)"
    raise RuntimeError(
        f"Command failed ({completed.returncode}): {' '.join(cmd)}\n{details}"
    )


def render_one(input_md: Path, reference_doc: Path | None) -> Path:
    if not input_md.exists():
        raise FileNotFoundError(f"Input markdown not found: {input_md}")

    output_docx = input_md.with_suffix(".docx")
    resource_path = f"{input_md.parent}:{REPO_ROOT}"

    cmd = [
        "pandoc",
        str(input_md),
        "--from",
        "gfm",
        "--to",
        "docx",
        "--standalone",
        "--resource-path",
        resource_path,
        "--output",
        str(output_docx),
    ]
    if reference_doc is not None:
        cmd.extend(["--reference-doc", str(reference_doc)])

    run(cmd)
    return output_docx


def main() -> int:
    args = parse_args()
    input_paths = resolve_inputs(args.input_md)
    reference_doc = args.reference_doc
    if reference_doc is not None and not reference_doc.is_absolute():
        reference_doc = REPO_ROOT / reference_doc

    if shutil.which("pandoc") is None:
        return 2
    if reference_doc is not None and not reference_doc.exists():
        return 2

    rendered: list[Path] = []
    for input_md in input_paths:
        try:
            output_docx = render_one(input_md=input_md, reference_doc=reference_doc)
        except Exception:
            return 1
        rendered.append(output_docx)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
