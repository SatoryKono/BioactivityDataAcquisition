#!/usr/bin/env python3
"""Nightly regression suite for diagram Phase 2 checks (DIAG-T024..DIAG-T029)."""

from __future__ import annotations

import argparse
import json
import random
import re
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

try:
    from .diagram_paths import (
        DIAGRAM_THEME_DIR,
        QUALITY_GATE_MANIFEST,
        REPO_ROOT,
        VISUAL_SMOKE_MANIFEST,
    )
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import (
        DIAGRAM_THEME_DIR,
        QUALITY_GATE_MANIFEST,
        REPO_ROOT,
        VISUAL_SMOKE_MANIFEST,
    )


DEFAULT_SOURCE_MANIFEST = QUALITY_GATE_MANIFEST
DEFAULT_RENDER_MANIFEST = VISUAL_SMOKE_MANIFEST
DEFAULT_CONFIG = DIAGRAM_THEME_DIR / "mermaid-config.json"
DEFAULT_CSS = DIAGRAM_THEME_DIR / "custom.css"
GIT_DIFF_SCOPE = "<git-diff>"

SVG_NS = "http://www.w3.org/2000/svg"
NS = {"svg": SVG_NS}
QUOTED_RE = re.compile(r'"([^"\\]*(?:\\.[^"\\]*)*)"')
TAG_RE = re.compile(r"<[^>]+>")
EDGE_RE = re.compile(r"\s(?:-->|-.->|==>|---|--x|x--)\s")
NODE_ID_RE = re.compile(r"\b([A-Za-z_][A-Za-z0-9_]*)\b")


@dataclass(frozen=True)
class Issue:
    rule_id: str
    severity: str
    file: str
    message: str


@dataclass(frozen=True)
class Report:
    checked_sources: int
    checked_renders: int
    warnings: int
    errors: int
    issues: list[Issue]


@dataclass(frozen=True)
class SvgShape:
    node_groups: int
    edge_paths: int
    edge_labels: int
    text_nodes: int
    foreign_object_text_nodes: int
    viewbox_width: float
    viewbox_height: float


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _err(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def _ensure_path_within_root(path: Path, root: Path) -> Path:
    resolved_root = root.resolve()
    resolved_path = path.resolve()
    if resolved_root != resolved_path and resolved_root not in resolved_path.parents:
        raise ValueError(f"refusing to process path outside {resolved_root}: {resolved_path}")
    return resolved_path


def _ensure_repo_path(path: Path) -> Path:
    return _ensure_path_within_root(path, REPO_ROOT)


def _git_pathspec(path: Path) -> str:
    """Return a sanitized repo-relative Git pathspec."""
    safe_path = _ensure_repo_path(REPO_ROOT / path)
    relative = safe_path.relative_to(REPO_ROOT.resolve()).as_posix()
    if relative.startswith("-"):
        raise ValueError(f"Git pathspec must not start with '-': {relative}")
    return relative


def _parse_manifest_path_entry(line: str, allowed_suffixes: tuple[str, ...]) -> Path:
    path = Path(line)
    if path.is_absolute():
        raise ValueError(f"Manifest paths must be relative: {line}")
    if any(part == ".." for part in path.parts):
        raise ValueError(f"Manifest paths must not escape the repository root: {line}")
    if line.startswith("-"):
        raise ValueError(f"Manifest paths must not start with '-': {line}")
    if path.suffix.lower() not in allowed_suffixes:
        allowed = ", ".join(allowed_suffixes)
        raise ValueError(f"Unsupported suffix in manifest ({allowed} expected): {line}")
    return path


def load_manifest(manifest_path: Path, allowed_suffixes: tuple[str, ...]) -> list[Path]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")
    paths: list[Path] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(_parse_manifest_path_entry(line, allowed_suffixes))
    if not paths:
        raise ValueError(f"Manifest is empty: {manifest_path}")
    return paths


def normalize_label(text: str) -> str:
    no_br = text.replace("<br/>", " ").replace("<br>", " ")
    no_tags = TAG_RE.sub("", no_br)
    return " ".join(no_tags.split())


def parse_long_label_count(lines: list[str], *, max_len: int, max_br: int) -> int:
    count = 0
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        for match in QUOTED_RE.finditer(stripped):
            raw = match.group(1)
            normalized = normalize_label(raw)
            br_count = raw.lower().count("<br/>") + raw.lower().count("<br>")
            if len(normalized) > max_len or br_count > max_br:
                count += 1
    return count


def has_interactivity_markers(lines: list[str]) -> bool:
    content = "\n".join(lines)
    return (
        re.search(r"^\s*click\s+", content, flags=re.MULTILINE) is not None
        or "tooltip" in content.lower()
        or "%% Tooltip:" in content
    )


def derive_png_path(svg_path: Path) -> Path:
    parts = list(svg_path.parts)
    if "svg" not in parts:
        raise ValueError(
            f"Cannot derive PNG path from SVG path without '/svg/': {svg_path}"
        )
    idx = parts.index("svg")
    parts[idx] = "png"
    return Path(*parts).with_suffix(".png")


def read_png_dimensions(path: Path) -> tuple[int, int]:
    raw = path.read_bytes()
    if len(raw) < 24 or raw[:8] != b"\x89PNG\r\n\x1a\n":
        raise ValueError(f"Invalid PNG signature: {path}")
    width = int.from_bytes(raw[16:20], "big")
    height = int.from_bytes(raw[20:24], "big")
    return width, height


def _class_tokens(elem: ET.Element) -> set[str]:
    raw = elem.attrib.get("class", "")
    return {token for token in raw.split() if token}


def parse_viewbox(root: ET.Element) -> tuple[float, float]:
    view_box = root.attrib.get("viewBox", "")
    if view_box:
        parts = view_box.split()
        if len(parts) == 4:
            return float(parts[2]), float(parts[3])
    width = float(root.attrib.get("width", "0").replace("px", "") or 0)
    height = float(root.attrib.get("height", "0").replace("px", "") or 0)
    return width, height


def analyze_svg_shape(path: Path) -> SvgShape:
    tree = ET.parse(path)
    root = tree.getroot()

    node_groups = 0
    edge_paths = 0
    edge_labels = 0
    text_nodes = 0
    foreign_object_text_nodes = 0

    for elem in root.iter():
        tag = elem.tag.split("}", 1)[1] if "}" in elem.tag else elem.tag
        classes = _class_tokens(elem)
        if tag == "g" and "node" in classes:
            node_groups += 1
        if tag == "g" and "edgePath" in classes:
            edge_paths += 1
        if tag == "g" and "edgeLabel" in classes:
            edge_labels += 1
        if tag == "text":
            text = " ".join(elem.itertext()).strip()
            if text:
                text_nodes += 1
        if tag == "foreignObject":
            text = " ".join(elem.itertext()).strip()
            if text:
                foreign_object_text_nodes += 1

    vb_w, vb_h = parse_viewbox(root)
    return SvgShape(
        node_groups=node_groups,
        edge_paths=edge_paths,
        edge_labels=edge_labels,
        text_nodes=text_nodes,
        foreign_object_text_nodes=foreign_object_text_nodes,
        viewbox_width=vb_w,
        viewbox_height=vb_h,
    )


def is_flowchart(lines: list[str]) -> bool:
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        lowered = stripped.lower()
        return lowered.startswith("flowchart") or lowered.startswith("graph")
    return False


def reorder_edge_lines(lines: list[str], seed: int = 13) -> list[str]:
    candidates: list[tuple[int, str]] = []
    for idx, line in enumerate(lines):
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if stripped.startswith("linkStyle"):
            continue
        if EDGE_RE.search(stripped):
            candidates.append((idx, line))

    if len(candidates) < 4:
        return lines[:]

    shuffled = [line for _, line in candidates]
    rng = random.Random(seed)
    rng.shuffle(shuffled)

    result = lines[:]
    for position, candidate in enumerate(candidates):
        idx, _ = candidate
        result[idx] = shuffled[position]
    return result


def extract_anchor_node(lines: list[str]) -> str:
    for line in lines:
        stripped = line.strip()
        if not stripped or stripped.startswith("%%"):
            continue
        if EDGE_RE.search(stripped):
            tokens = NODE_ID_RE.findall(stripped)
            if tokens:
                return tokens[0]
    return "A"


def inject_growth_node(lines: list[str]) -> list[str]:
    anchor = extract_anchor_node(lines)
    result = lines[:]
    result.append('    __stress_node__["Stress Node"]')
    result.append(f"    {anchor} --> __stress_node__")
    return result


def run_command(cmd: list[str]) -> tuple[int, str]:
    try:
        completed = subprocess.run(
            cmd,
            check=False,
            capture_output=True,
            text=True,
        )
    except FileNotFoundError as exc:
        return 127, str(exc)
    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    details = stderr or stdout
    return completed.returncode, details


def render_with_mmdc(
    source: Path,
    output: Path,
    *,
    mmdc_bin: str,
    config: Path,
    css: Path,
    puppeteer: Path | None,
) -> tuple[bool, str]:
    cmd = [
        mmdc_bin,
        "-i",
        str(source),
        "-o",
        str(output),
        "-c",
        str(config),
        "--cssFile",
        str(css),
        "-b",
        "white",
    ]
    if puppeteer is not None:
        cmd.extend(["-p", str(puppeteer)])
    code, details = run_command(cmd)
    return code == 0, details


def probe_render_backend(
    *,
    mmdc_bin: str,
    config: Path,
    css: Path,
    puppeteer: Path | None,
    tmpdir: Path,
) -> tuple[bool, str]:
    probe_src = tmpdir / "probe.mmd"
    probe_svg = tmpdir / "probe.svg"
    probe_src.write_text("flowchart TB\nA --> B\n", encoding="utf-8")
    return render_with_mmdc(
        probe_src,
        probe_svg,
        mmdc_bin=mmdc_bin,
        config=config,
        css=css,
        puppeteer=puppeteer,
    )


def check_diag_t024(source_paths: list[Path], max_len: int, max_br: int) -> list[Issue]:
    issues: list[Issue] = []
    for rel in source_paths:
        path = REPO_ROOT / rel
        if not path.exists():
            issues.append(
                Issue("DIAG-T024", "WARNING", str(rel), "source file missing")
            )
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        long_labels = parse_long_label_count(lines, max_len=max_len, max_br=max_br)
        if long_labels > 0 and not has_interactivity_markers(lines):
            issues.append(
                Issue(
                    "DIAG-T024",
                    "WARNING",
                    str(rel),
                    f"{long_labels} long labels detected but no click/tooltip fallback markers",
                )
            )
    return issues


def check_diag_t025(render_paths: list[Path]) -> list[Issue]:
    issues: list[Issue] = []
    for svg_rel in render_paths:
        svg = REPO_ROOT / svg_rel
        if not svg.exists():
            issues.append(
                Issue("DIAG-T025", "WARNING", str(svg_rel), "SVG render missing")
            )
            continue

        try:
            shape = analyze_svg_shape(svg)
        except ET.ParseError as exc:
            issues.append(
                Issue("DIAG-T025", "WARNING", str(svg_rel), f"SVG parse error: {exc}")
            )
            continue

        png_rel = derive_png_path(svg_rel)
        png = REPO_ROOT / png_rel
        if not png.exists():
            issues.append(
                Issue("DIAG-T025", "WARNING", str(png_rel), "PNG render missing")
            )
            continue

        try:
            png_w, png_h = read_png_dimensions(png)
        except ValueError as exc:
            issues.append(Issue("DIAG-T025", "WARNING", str(png_rel), str(exc)))
            continue

        if (
            shape.edge_labels > 0
            and (shape.text_nodes + shape.foreign_object_text_nodes) == 0
        ):
            issues.append(
                Issue(
                    "DIAG-T025",
                    "WARNING",
                    str(svg_rel),
                    "edge labels exist but no readable text in SVG (text/foreignObject)",
                )
            )

        if (png_w * png_h) < 300_000:
            issues.append(
                Issue(
                    "DIAG-T025",
                    "WARNING",
                    str(png_rel),
                    f"PNG effective area too low ({png_w}x{png_h})",
                )
            )

        if shape.viewbox_width > 0 and shape.viewbox_height > 0:
            svg_ratio = shape.viewbox_width / shape.viewbox_height
            png_ratio = png_w / max(png_h, 1)
            if abs(svg_ratio - png_ratio) > 0.6:
                issues.append(
                    Issue(
                        "DIAG-T025",
                        "WARNING",
                        str(svg_rel),
                        f"aspect drift between SVG ({svg_ratio:.2f}) and PNG ({png_ratio:.2f})",
                    )
                )

    return issues


def check_diag_t026(render_paths: list[Path]) -> list[Issue]:
    try:
        pathspecs = [_git_pathspec(path) for path in render_paths]
    except ValueError as exc:
        return [
            Issue("DIAG-T026", "WARNING", GIT_DIFF_SCOPE, f"invalid render path: {exc}")
        ]

    try:
        completed = subprocess.run(
            ["git", "diff", "--name-only", "--", *pathspecs],
            check=False,
            capture_output=True,
            text=True,
            cwd=REPO_ROOT,
        )
    except FileNotFoundError as exc:
        return [
            Issue("DIAG-T026", "WARNING", GIT_DIFF_SCOPE, f"git diff failed: {exc}")
        ]

    stderr = completed.stderr.strip()
    stdout = completed.stdout.strip()
    details = stderr or stdout
    code = completed.returncode
    if code != 0:
        return [
            Issue("DIAG-T026", "WARNING", GIT_DIFF_SCOPE, f"git diff failed: {details}")
        ]

    changed = [line.strip() for line in details.splitlines() if line.strip()]
    if not changed:
        return []

    return [
        Issue(
            "DIAG-T026",
            "WARNING",
            path,
            "rendered baseline differs from committed version",
        )
        for path in changed
    ]


def write_temp_source(tmpdir: Path, stem: str, lines: list[str]) -> Path:
    path = tmpdir / f"{stem}.mmd"
    safe_path = _ensure_path_within_root(path, tmpdir)
    safe_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return safe_path


def check_diag_t027(
    source_paths: list[Path],
    *,
    mmdc_bin: str,
    config: Path,
    css: Path,
    puppeteer: Path | None,
    tmpdir: Path,
) -> list[Issue]:
    issues: list[Issue] = []

    for rel in source_paths:
        path = REPO_ROOT / rel
        if not path.exists():
            issues.append(
                Issue("DIAG-T027", "WARNING", str(rel), "source file missing")
            )
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        if not is_flowchart(lines):
            continue

        reordered = reorder_edge_lines(lines)
        if reordered == lines:
            continue

        base_src = write_temp_source(tmpdir, f"base-{path.stem}", lines)
        chaos_src = write_temp_source(tmpdir, f"chaos-{path.stem}", reordered)
        base_svg = tmpdir / f"base-{path.stem}.svg"
        chaos_svg = tmpdir / f"chaos-{path.stem}.svg"

        ok_base, err_base = render_with_mmdc(
            base_src,
            base_svg,
            mmdc_bin=mmdc_bin,
            config=config,
            css=css,
            puppeteer=puppeteer,
        )
        ok_chaos, err_chaos = render_with_mmdc(
            chaos_src,
            chaos_svg,
            mmdc_bin=mmdc_bin,
            config=config,
            css=css,
            puppeteer=puppeteer,
        )

        if not ok_base:
            issues.append(
                Issue(
                    "DIAG-T027",
                    "WARNING",
                    str(rel),
                    f"baseline render failed: {err_base}",
                )
            )
            continue
        if not ok_chaos:
            issues.append(
                Issue(
                    "DIAG-T027",
                    "WARNING",
                    str(rel),
                    f"reorder render failed: {err_chaos}",
                )
            )
            continue

        base_shape = analyze_svg_shape(base_svg)
        chaos_shape = analyze_svg_shape(chaos_svg)

        if (
            base_shape.edge_paths != chaos_shape.edge_paths
            or base_shape.node_groups != chaos_shape.node_groups
            or base_shape.edge_labels != chaos_shape.edge_labels
        ):
            issues.append(
                Issue(
                    "DIAG-T027",
                    "WARNING",
                    str(rel),
                    "shape metrics changed after edge reorder",
                )
            )

    return issues


def check_diag_t028(
    source_paths: list[Path],
    *,
    mmdc_bin: str,
    config: Path,
    css: Path,
    puppeteer: Path | None,
    tmpdir: Path,
) -> list[Issue]:
    issues: list[Issue] = []

    for rel in source_paths:
        path = REPO_ROOT / rel
        if not path.exists():
            issues.append(
                Issue("DIAG-T028", "WARNING", str(rel), "source file missing")
            )
            continue

        lines = path.read_text(encoding="utf-8").splitlines()
        if not is_flowchart(lines):
            continue

        stressed = inject_growth_node(lines)
        base_src = write_temp_source(tmpdir, f"growth-base-{path.stem}", lines)
        stress_src = write_temp_source(tmpdir, f"growth-stress-{path.stem}", stressed)
        base_svg = tmpdir / f"growth-base-{path.stem}.svg"
        stress_svg = tmpdir / f"growth-stress-{path.stem}.svg"

        ok_base, err_base = render_with_mmdc(
            base_src,
            base_svg,
            mmdc_bin=mmdc_bin,
            config=config,
            css=css,
            puppeteer=puppeteer,
        )
        ok_stress, err_stress = render_with_mmdc(
            stress_src,
            stress_svg,
            mmdc_bin=mmdc_bin,
            config=config,
            css=css,
            puppeteer=puppeteer,
        )

        if not ok_base:
            issues.append(
                Issue(
                    "DIAG-T028",
                    "WARNING",
                    str(rel),
                    f"baseline render failed: {err_base}",
                )
            )
            continue
        if not ok_stress:
            issues.append(
                Issue(
                    "DIAG-T028",
                    "WARNING",
                    str(rel),
                    f"growth render failed: {err_stress}",
                )
            )
            continue

        base_shape = analyze_svg_shape(base_svg)
        stress_shape = analyze_svg_shape(stress_svg)

        if stress_shape.edge_paths < base_shape.edge_paths:
            issues.append(
                Issue(
                    "DIAG-T028",
                    "WARNING",
                    str(rel),
                    "edge path count decreased after node growth",
                )
            )

    return issues


def build_alt_css() -> str:
    safe_original = _ensure_repo_path(DEFAULT_CSS)
    content = safe_original.read_text(encoding="utf-8")
    content = content.replace("#f5f3ff", "#ede9fe")
    content = content.replace("#fff1f2", "#ffe4e6")
    content = content.replace("#111827", "#0f172a")
    return content


def check_diag_t029(
    source_paths: list[Path],
    *,
    mmdc_bin: str,
    config: Path,
    css: Path,
    puppeteer: Path | None,
    tmpdir: Path,
) -> list[Issue]:
    issues: list[Issue] = []
    with tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        suffix=".css",
        dir=tmpdir,
        delete=False,
    ) as handle:
        alt_css = _ensure_path_within_root(Path(handle.name), tmpdir)
        handle.write(build_alt_css())

    for rel in source_paths:
        path = REPO_ROOT / rel
        if not path.exists():
            issues.append(
                Issue("DIAG-T029", "WARNING", str(rel), "source file missing")
            )
            continue

        canonical_svg = tmpdir / f"theme-canonical-{path.stem}.svg"
        alt_svg = tmpdir / f"theme-alt-{path.stem}.svg"

        ok_canonical, err_canonical = render_with_mmdc(
            path,
            canonical_svg,
            mmdc_bin=mmdc_bin,
            config=config,
            css=css,
            puppeteer=puppeteer,
        )
        ok_alt, err_alt = render_with_mmdc(
            path,
            alt_svg,
            mmdc_bin=mmdc_bin,
            config=config,
            css=alt_css,
            puppeteer=puppeteer,
        )

        if not ok_canonical:
            issues.append(
                Issue(
                    "DIAG-T029",
                    "WARNING",
                    str(rel),
                    f"canonical theme render failed: {err_canonical}",
                )
            )
            continue
        if not ok_alt:
            issues.append(
                Issue(
                    "DIAG-T029",
                    "WARNING",
                    str(rel),
                    f"alt theme render failed: {err_alt}",
                )
            )
            continue

        can_shape = analyze_svg_shape(canonical_svg)
        alt_shape = analyze_svg_shape(alt_svg)
        can_readable = can_shape.text_nodes + can_shape.foreign_object_text_nodes
        alt_readable = alt_shape.text_nodes + alt_shape.foreign_object_text_nodes
        if can_readable == 0 or alt_readable == 0:
            issues.append(
                Issue(
                    "DIAG-T029",
                    "WARNING",
                    str(rel),
                    "readable text missing in one of theme renders (text/foreignObject)",
                )
            )

    return issues


def render_markdown(report: Report) -> str:
    lines: list[str] = []
    lines.append("# Diagram Nightly Phase 2 Report")
    lines.append("")
    lines.append("## Summary")
    lines.append("")
    lines.append(f"- Checked source diagrams: {report.checked_sources}")
    lines.append(f"- Checked rendered diagrams: {report.checked_renders}")
    lines.append(f"- Warnings: {report.warnings}")
    lines.append(f"- Errors: {report.errors}")

    if report.issues:
        lines.append("")
        lines.append("## Findings")
        lines.append("")
        for issue in report.issues:
            lines.append(
                f"- `{issue.rule_id}` [{issue.severity}] {issue.file}: {issue.message}"
            )

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run nightly diagram regression suite")
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    parser.add_argument("--render-manifest", type=Path, default=DEFAULT_RENDER_MANIFEST)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--css", type=Path, default=DEFAULT_CSS)
    parser.add_argument("--puppeteer", type=Path, default=None)
    parser.add_argument("--mmdc-bin", default="mmdc")
    parser.add_argument("--max-label-length", type=int, default=90)
    parser.add_argument("--max-br", type=int, default=4)
    parser.add_argument("--json-out", type=Path)
    parser.add_argument("--markdown-out", type=Path)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--skip-chaos", action="store_true")
    parser.add_argument("--skip-growth", action="store_true")
    parser.add_argument("--skip-theme", action="store_true")
    parser.add_argument("--json", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    src_manifest = (
        args.source_manifest
        if args.source_manifest.is_absolute()
        else REPO_ROOT / args.source_manifest
    )
    rnd_manifest = (
        args.render_manifest
        if args.render_manifest.is_absolute()
        else REPO_ROOT / args.render_manifest
    )
    config = args.config if args.config.is_absolute() else REPO_ROOT / args.config
    css = args.css if args.css.is_absolute() else REPO_ROOT / args.css
    puppeteer = None
    if args.puppeteer is not None:
        puppeteer = (
            args.puppeteer
            if args.puppeteer.is_absolute()
            else REPO_ROOT / args.puppeteer
        )

    try:
        source_paths = load_manifest(src_manifest, (".mmd", ".mermaid"))
        render_paths = load_manifest(rnd_manifest, (".svg",))
    except (FileNotFoundError, ValueError) as exc:
        _err(f"[ERROR] {exc}")
        return 2

    issues: list[Issue] = []

    issues.extend(
        check_diag_t024(source_paths, max_len=args.max_label_length, max_br=args.max_br)
    )
    issues.extend(check_diag_t025(render_paths))
    issues.extend(check_diag_t026(render_paths))

    with tempfile.TemporaryDirectory(prefix="diagram-nightly-") as temp_dir:
        tmpdir = Path(temp_dir)
        needs_render_backend = not (
            args.skip_chaos and args.skip_growth and args.skip_theme
        )
        backend_ok = True
        backend_error = ""
        if needs_render_backend:
            backend_ok, backend_error = probe_render_backend(
                mmdc_bin=args.mmdc_bin,
                config=config,
                css=css,
                puppeteer=puppeteer,
                tmpdir=tmpdir,
            )
            if not backend_ok:
                issues.append(
                    Issue(
                        "DIAG-T027",
                        "WARNING",
                        "<render-backend>",
                        f"render backend unavailable, chaos/growth/theme checks skipped: {backend_error}",
                    )
                )

        if not args.skip_chaos and backend_ok:
            issues.extend(
                check_diag_t027(
                    source_paths,
                    mmdc_bin=args.mmdc_bin,
                    config=config,
                    css=css,
                    puppeteer=puppeteer,
                    tmpdir=tmpdir,
                )
            )
        if not args.skip_growth and backend_ok:
            issues.extend(
                check_diag_t028(
                    source_paths,
                    mmdc_bin=args.mmdc_bin,
                    config=config,
                    css=css,
                    puppeteer=puppeteer,
                    tmpdir=tmpdir,
                )
            )
        if not args.skip_theme and backend_ok:
            issues.extend(
                check_diag_t029(
                    source_paths,
                    mmdc_bin=args.mmdc_bin,
                    config=config,
                    css=css,
                    puppeteer=puppeteer,
                    tmpdir=tmpdir,
                )
            )

    errors = sum(1 for issue in issues if issue.severity == "ERROR")
    warnings = sum(1 for issue in issues if issue.severity == "WARNING")
    report = Report(
        checked_sources=len(source_paths),
        checked_renders=len(render_paths),
        warnings=warnings,
        errors=errors,
        issues=issues,
    )

    payload = {
        "checked_sources": report.checked_sources,
        "checked_renders": report.checked_renders,
        "warnings": report.warnings,
        "errors": report.errors,
        "issues": [asdict(issue) for issue in report.issues],
    }

    if args.json_out is not None:
        json_out = (
            args.json_out if args.json_out.is_absolute() else REPO_ROOT / args.json_out
        )
        safe_json_out = _ensure_repo_path(json_out)
        safe_json_out.parent.mkdir(parents=True, exist_ok=True)
        safe_json_out.write_text(
            json.dumps(payload, ensure_ascii=True, indent=2) + "\n",
            encoding="utf-8",
        )

    if args.markdown_out is not None:
        md_out = (
            args.markdown_out
            if args.markdown_out.is_absolute()
            else REPO_ROOT / args.markdown_out
        )
        safe_md_out = _ensure_repo_path(md_out)
        safe_md_out.parent.mkdir(parents=True, exist_ok=True)
        safe_md_out.write_text(render_markdown(report), encoding="utf-8")

    if args.json:
        _out(json.dumps(payload, ensure_ascii=True, indent=2))
    else:
        _out(
            "[INFO] Nightly suite summary: "
            f"sources={report.checked_sources}, renders={report.checked_renders}, "
            f"warnings={report.warnings}, errors={report.errors}"
        )
        for issue in report.issues:
            _out(
                f"[INFO] {issue.rule_id} [{issue.severity}] {issue.file}: {issue.message}"
            )

    if args.strict:
        return 1 if (errors > 0 or warnings > 0) else 0
    return 1 if errors > 0 else 0


if __name__ == "__main__":
    raise SystemExit(main())
