#!/usr/bin/env python3
"""Generate *-with-descriptions.pdf documents with print-safe layout."""

from __future__ import annotations

import argparse
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
    return current.parents[0]


REPO_ROOT = _resolve_repo_root()
DEFAULT_INPUTS = [
    Path("docs/02-architecture/mmd-diagrams/class-diagrams-with-descriptions.md"),
    Path("docs/02-architecture/mmd-diagrams/foundation-diagrams-with-descriptions.md"),
]
DEFAULT_CSS = Path("docs/02-architecture/mmd-diagrams/theme/with-descriptions-print.css")
DEFAULT_BOUNDS_CHECKER = Path("scripts/diagrams/check_pdf_image_bounds.py")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build with-descriptions PDFs from Markdown using Pandoc + wkhtmltopdf "
            "with fit-to-page print CSS."
        ),
    )
    parser.add_argument(
        "--input-md",
        action="append",
        default=[],
        help="Input markdown file (repeatable). Defaults to class/foundation bundles.",
    )
    parser.add_argument(
        "--css",
        type=Path,
        default=DEFAULT_CSS,
        help=f"Print CSS for HTML/PDF conversion (default: {DEFAULT_CSS}).",
    )
    parser.add_argument(
        "--page-size",
        default="A3",
        help="wkhtmltopdf page size (default: A3).",
    )
    parser.add_argument(
        "--orientation",
        default="Landscape",
        choices=["Portrait", "Landscape"],
        help="wkhtmltopdf page orientation (default: Landscape).",
    )
    parser.add_argument(
        "--prefer-svg",
        action="store_true",
        default=True,
        help="Rewrite markdown image refs from /png/*.png to /svg/*.svg (default: on).",
    )
    parser.add_argument(
        "--no-prefer-svg",
        action="store_false",
        dest="prefer_svg",
        help="Do not rewrite PNG links to SVG for PDF generation.",
    )
    parser.add_argument(
        "--skip-bounds-check",
        action="store_true",
        help="Skip post-generation PDF image bounds validation.",
    )
    parser.add_argument(
        "--max-overflow-ratio",
        type=float,
        default=1.02,
        help="Allowed page overflow ratio for PDF bounds check (default: 1.02).",
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


def rewrite_image_links(markdown_text: str, *, base_dir: Path, prefer_svg: bool) -> str:
    pattern = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)\)")

    def _replace(match: re.Match[str]) -> str:
        alt = match.group(1)
        target = match.group(2)
        updated = target
        if prefer_svg and "/png/" in updated and updated.endswith(".png"):
            updated = updated.replace("/png/", "/svg/")[:-4] + ".svg"

        if "://" in updated or updated.startswith("data:"):
            return f"![{alt}]({updated})"

        absolute = (base_dir / updated).resolve()
        return f"![{alt}]({absolute.as_uri()})"

    return pattern.sub(_replace, markdown_text)


def run(cmd: list[str], cwd: Path | None = None) -> None:
    completed = subprocess.run(cmd, cwd=str(cwd) if cwd else None, capture_output=True, text=True)
    if completed.returncode == 0:
        return
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    details = stderr or stdout or "(no output)"
    raise RuntimeError(f"Command failed ({completed.returncode}): {' '.join(cmd)}\n{details}")


def render_one(
    input_md: Path,
    css_path: Path,
    page_size: str,
    orientation: str,
    prefer_svg: bool,
    run_bounds_check: bool,
    max_overflow_ratio: float,
) -> Path:
    if not input_md.exists():
        raise FileNotFoundError(f"Input markdown not found: {input_md}")
    output_pdf = input_md.with_suffix(".pdf")
    title = input_md.stem.replace("-", " ")

    markdown_text = input_md.read_text(encoding="utf-8")
    markdown_text = rewrite_image_links(
        markdown_text,
        base_dir=input_md.parent,
        prefer_svg=prefer_svg,
    )

    with tempfile.TemporaryDirectory(prefix="bioetl-diagram-pdf-") as tmp_dir_raw:
        tmp_dir = Path(tmp_dir_raw)
        tmp_md = tmp_dir / f"{input_md.stem}.md"
        tmp_html = tmp_dir / f"{input_md.stem}.html"

        tmp_md.write_text(markdown_text, encoding="utf-8")
        resource_path = f"{input_md.parent}:{REPO_ROOT}"

        run(
            [
                "pandoc",
                str(tmp_md),
                "--from",
                "gfm",
                "--to",
                "html5",
                "--standalone",
                "--metadata",
                f"title={title}",
                "--css",
                str(css_path),
                "--resource-path",
                resource_path,
                "--output",
                str(tmp_html),
            ]
        )

        run(
            [
                "wkhtmltopdf",
                "--enable-local-file-access",
                "--page-size",
                page_size,
                "--orientation",
                orientation,
                "--margin-top",
                "10",
                "--margin-right",
                "10",
                "--margin-bottom",
                "10",
                "--margin-left",
                "10",
                str(tmp_html),
                str(output_pdf),
            ]
        )

    if run_bounds_check:
        run(
            [
                sys.executable,
                str(REPO_ROOT / DEFAULT_BOUNDS_CHECKER),
                "--pdf",
                str(output_pdf),
                "--max-overflow-ratio",
                str(max_overflow_ratio),
            ]
        )

    return output_pdf


def main() -> int:
    args = parse_args()
    input_paths = resolve_inputs(args.input_md)
    css_path = args.css if args.css.is_absolute() else REPO_ROOT / args.css

    missing_tools: list[str] = []
    for tool in ("pandoc", "wkhtmltopdf"):
        if shutil.which(tool) is None:
            missing_tools.append(tool)
    if missing_tools:
        print(f"[ERROR] Missing required tools: {', '.join(missing_tools)}", file=sys.stderr)
        return 2
    if not css_path.exists():
        print(f"[ERROR] CSS file not found: {css_path}", file=sys.stderr)
        return 2

    rendered: list[Path] = []
    for input_md in input_paths:
        try:
            output_pdf = render_one(
                input_md=input_md,
                css_path=css_path,
                page_size=args.page_size,
                orientation=args.orientation,
                prefer_svg=args.prefer_svg,
                run_bounds_check=not args.skip_bounds_check,
                max_overflow_ratio=args.max_overflow_ratio,
            )
        except Exception as exc:  # noqa: BLE001 - CLI boundary
            print(f"[ERROR] {exc}", file=sys.stderr)
            return 1
        rendered.append(output_pdf)
        print(f"[OK] Generated: {output_pdf}")

    print(f"[INFO] Generated PDFs: {len(rendered)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
