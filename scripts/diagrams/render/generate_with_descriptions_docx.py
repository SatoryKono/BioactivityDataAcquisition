#!/usr/bin/env python3
"""Generate *-with-descriptions.docx documents from Markdown bundles."""

from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def _resolve_repo_root() -> Path:
    current = Path(__file__).resolve()
    for parent in current.parents:
        if (parent / "pyproject.toml").exists() and (parent / "scripts").exists():
            return parent
    return current.parents[1]


REPO_ROOT = _resolve_repo_root()
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.diagrams.core.diagram_paths import bundle_markdown_path

PAGEBREAK_LUA = REPO_ROOT / "scripts" / "diagrams" / "pagebreak.lua"
DEFAULT_INPUTS = [
    bundle_markdown_path("class-diagrams").relative_to(REPO_ROOT),
    bundle_markdown_path("foundation").relative_to(REPO_ROOT),
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
    if raw_inputs:
        paths = [Path(item) for item in raw_inputs]
    else:
        paths = DEFAULT_INPUTS
    resolved: list[Path] = []
    for path in paths:
        resolved.append(path if path.is_absolute() else REPO_ROOT / path)
    return resolved


def _resource_path_sep() -> str:
    """Return the resource-path separator: ';' on Windows, ':' on POSIX."""
    return ";" if os.name == "nt" else ":"


def rewrite_image_links(markdown_text: str, *, base_dir: Path) -> str:
    """Rewrite bundle image links to absolute PNG assets for DOCX compatibility."""
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")

    def _replace(match: re.Match[str]) -> str:
        alt = match.group(1)
        target = match.group(2)
        updated = target
        if "/svg/" in updated and updated.endswith(".svg"):
            updated = updated.replace("/svg/", "/png/")[:-4] + ".png"

        if "://" in updated or updated.startswith("data:"):
            return f"![{alt}]({updated})"

        absolute = (base_dir / updated).resolve()
        return f"![{alt}]({absolute.as_uri()})"

    return pattern.sub(_replace, markdown_text)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    from scripts.engineering.common.repo_paths import ensure_safe_cli_argv

    completed = subprocess.run(
        ensure_safe_cli_argv([str(token) for token in cmd]),
        cwd=str(cwd) if cwd else None,
        capture_output=True,
        text=True,
    )
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
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_cli_path

    input_md = resolve_cli_path(input_md, root=REPO_ROOT)
    markdown_text = input_md.read_text(encoding="utf-8")
    markdown_text = rewrite_image_links(markdown_text, base_dir=input_md.parent)

    with tempfile.TemporaryDirectory(prefix="bioetl-diagram-docx-") as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        tmp_md = tmp_dir / input_md.name
        tmp_md.write_text(markdown_text, encoding="utf-8")

        sep = _resource_path_sep()
        resource_path = f"{input_md.parent}{sep}{REPO_ROOT}"

        cmd = [
            "pandoc",
            str(tmp_md),
            "--from",
            "markdown",
            "--to",
            "docx",
            "--standalone",
            "--resource-path",
            resource_path,
            "--output",
            str(output_docx),
        ]
        if PAGEBREAK_LUA.exists():
            cmd.extend(["--lua-filter", str(PAGEBREAK_LUA)])
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
        print("[ERROR] Missing required tool: pandoc", file=sys.stderr)
        return 2
    if reference_doc is not None and not reference_doc.exists():
        print(f"[ERROR] Reference DOCX not found: {reference_doc}", file=sys.stderr)
        return 2

    rendered: list[Path] = []
    for input_md in input_paths:
        try:
            output_docx = render_one(input_md=input_md, reference_doc=reference_doc)
        except Exception as exc:
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        rendered.append(output_docx)
        print(f"[OK] Generated: {output_docx}")

    print(f"[INFO] Generated DOCX files: {len(rendered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
