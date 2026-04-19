#!/usr/bin/env python3
"""Validate rendered SVG text visibility for diagram smoke baselines.

This guard focuses on failures where labels are rendered as white rectangles
without readable text in some viewers.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path

SVG_NS = "http://www.w3.org/2000/svg"
NS = {"svg": SVG_NS}

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

try:
    from .diagram_paths import VISUAL_SMOKE_MANIFEST
except ImportError:  # pragma: no cover - direct script execution
    from diagram_paths import VISUAL_SMOKE_MANIFEST


DEFAULT_MANIFEST = VISUAL_SMOKE_MANIFEST


@dataclass(frozen=True)
class SvgMetrics:
    file: str
    edge_label_groups: int
    edge_label_groups_with_text: int
    foreign_objects: int
    fallback_text_nodes: int
    has_edge_label_color_css: bool
    has_fallback_color_css: bool


def _normalize(text: str) -> str:
    return " ".join(text.split()).strip()


def _local_name(tag: str) -> str:
    return tag.split("}", 1)[1] if "}" in tag else tag


def _class_tokens(elem: ET.Element) -> set[str]:
    raw = elem.attrib.get("class", "")
    return {token for token in raw.split() if token}


def _has_nonempty_text(elem: ET.Element) -> bool:
    text = _normalize(" ".join(elem.itertext()))
    return bool(text)


def _collect_style_text(root: ET.Element) -> str:
    parts: list[str] = []
    for style in root.findall(".//svg:style", NS):
        parts.append(style.text or "")
    return "\n".join(parts)


def analyze_svg(path: Path) -> tuple[SvgMetrics, list[str]]:
    tree = ET.parse(path)
    root = tree.getroot()

    edge_groups: list[ET.Element] = []
    fallback_text_nodes = 0
    foreign_objects = 0

    for elem in root.iter():
        name = _local_name(elem.tag)
        if name == "foreignObject":
            foreign_objects += 1
        if name == "g" and "edgeLabel" in _class_tokens(elem):
            edge_groups.append(elem)
        if (
            name == "text"
            and "fo-fallback" in _class_tokens(elem)
            and _has_nonempty_text(elem)
        ):
            fallback_text_nodes += 1

    edge_with_text = 0
    for group in edge_groups:
        has_text = False
        for child in group.iter():
            child_name = _local_name(child.tag)
            if child_name == "foreignObject" and _has_nonempty_text(child):
                has_text = True
                break
            if (
                child_name == "text"
                and "fo-fallback" in _class_tokens(child)
                and _has_nonempty_text(child)
            ):
                has_text = True
                break
        if has_text:
            edge_with_text += 1

    style_text = _collect_style_text(root)
    has_edge_label_color_css = (
        ".edgeLabel span" in style_text and "#111827" in style_text
    )
    has_fallback_color_css = (
        "text.fo-fallback" in style_text and "#111827" in style_text
    )

    metrics = SvgMetrics(
        file=str(path),
        edge_label_groups=len(edge_groups),
        edge_label_groups_with_text=edge_with_text,
        foreign_objects=foreign_objects,
        fallback_text_nodes=fallback_text_nodes,
        has_edge_label_color_css=has_edge_label_color_css,
        has_fallback_color_css=has_fallback_color_css,
    )

    issues: list[str] = []
    if metrics.edge_label_groups > 0 and metrics.edge_label_groups_with_text == 0:
        issues.append("edgeLabel groups exist but no readable label text was found")
    if (
        metrics.edge_label_groups > 0
        and not metrics.has_edge_label_color_css
        and metrics.fallback_text_nodes == 0
    ):
        issues.append(
            "missing edge-label text safeguards: no .edgeLabel color CSS and no fallback text"
        )
    if metrics.fallback_text_nodes > 0 and not metrics.has_fallback_color_css:
        issues.append(
            "fallback text nodes exist but text.fo-fallback CSS color rule is missing"
        )

    return metrics, issues


def load_manifest(manifest_path: Path) -> list[str]:
    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest not found: {manifest_path}")

    paths: list[str] = []
    for raw in manifest_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        paths.append(line)

    if not paths:
        raise ValueError(f"Manifest is empty: {manifest_path}")
    return paths


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Check SVG text visibility for diagram smoke set."
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=DEFAULT_MANIFEST,
        help=f"Path to manifest file (default: {DEFAULT_MANIFEST})",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit JSON report.",
    )
    parser.add_argument(
        "-f",
        "--file",
        type=Path,
        action="append",
        help="Check specific SVG file(s). If set, manifest is ignored.",
    )
    parser.add_argument(
        "--dir",
        type=Path,
        action="append",
        help="Check all *.svg in specific directory(ies). If set, manifest is ignored.",
    )
    return parser.parse_args()


def _out(message: str) -> None:
    sys.stdout.write(f"{message}\n")


def _err(message: str) -> None:
    sys.stderr.write(f"{message}\n")


def _collect_targets(args: argparse.Namespace, repo_root: Path) -> list[Path]:
    if args.file or args.dir:
        return _deduplicate_targets(
            [
                *(_resolve_target_path(repo_root, file_path) for file_path in args.file or []),
                *(
                    path
                    for directory in args.dir or []
                    for path in _svg_targets_in_directory(repo_root, directory)
                ),
            ]
        )

    manifest = (
        args.manifest if args.manifest.is_absolute() else repo_root / args.manifest
    )
    rel_paths = load_manifest(manifest)
    return [repo_root / rel for rel in rel_paths]


def _resolve_target_path(repo_root: Path, path: Path) -> Path:
    return path if path.is_absolute() else repo_root / path


def _svg_targets_in_directory(repo_root: Path, directory: Path) -> list[Path]:
    abs_dir = _resolve_target_path(repo_root, directory)
    if not abs_dir.is_dir():
        return []
    return sorted(abs_dir.glob("*.svg"))


def _deduplicate_targets(targets: list[Path]) -> list[Path]:
    unique: list[Path] = []
    seen: set[str] = set()
    for path in targets:
        key = str(path.resolve()) if path.exists() else str(path)
        if key in seen:
            continue
        unique.append(path)
        seen.add(key)
    return unique


def _relative_path(path: Path, repo_root: Path) -> str:
    if path.is_absolute() and str(path).startswith(str(repo_root)):
        return str(path.relative_to(repo_root))
    return str(path)


def _json_payload(
    targets: list[Path],
    metrics_out: list[SvgMetrics],
    failures: list[tuple[str, list[str]]],
) -> str:
    payload = {
        "ok": not failures,
        "checked": len(targets),
        "metrics": [asdict(m) for m in metrics_out],
        "failures": [{"file": f, "issues": i} for f, i in failures],
    }
    return json.dumps(payload, ensure_ascii=True, indent=2)


def _print_text_report(targets: list[Path], metrics_out: list[SvgMetrics]) -> None:
    _out(f"[INFO] Checked {len(targets)} SVG file(s).")
    for m in metrics_out:
        _out(
            "[INFO] "
            f"{Path(m.file).name}: edgeLabels={m.edge_label_groups}, "
            f"withText={m.edge_label_groups_with_text}, "
            f"foreignObject={m.foreign_objects}, "
            f"foFallback={m.fallback_text_nodes}"
        )


def main() -> int:
    args = parse_args()
    repo_root = Path.cwd()
    try:
        targets = _collect_targets(args, repo_root)
    except (FileNotFoundError, ValueError) as exc:
        _err(f"[ERROR] {exc}")
        return 2

    if not targets:
        _err("[ERROR] No SVG files to check.")
        return 2

    metrics_out: list[SvgMetrics] = []
    failures: list[tuple[str, list[str]]] = []

    for path in targets:
        rel = _relative_path(path, repo_root)
        if not path.exists():
            failures.append((rel, ["file not found"]))
            continue
        try:
            metrics, issues = analyze_svg(path)
        except ET.ParseError as exc:
            failures.append((rel, [f"xml parse error: {exc}"]))
            continue
        metrics_out.append(metrics)
        if issues:
            failures.append((rel, issues))

    if args.json:
        _out(_json_payload(targets, metrics_out, failures))
    else:
        _print_text_report(targets, metrics_out)

    if failures:
        _err("[ERROR] SVG text visibility check failed:")
        for file_path, issues in failures:
            _err(f"  - {file_path}")
            for issue in issues:
                _err(f"      * {issue}")
        return 1

    if not args.json:
        _out("[OK] SVG text visibility check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
