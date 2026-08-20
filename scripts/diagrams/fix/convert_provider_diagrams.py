"""Convert legacy provider Mermaid metadata to the ADR-040 comment format.

The converter is intentionally scoped to ``docs/02-architecture/diagrams/providers``.
It replaces YAML frontmatter, converts the known legacy inline fill palette to
canonical ``classDef`` assignments, and writes files atomically.

Usage:
    python -m scripts.diagrams convert-provider-diagrams --check
    python -m scripts.diagrams convert-provider-diagrams
"""

from __future__ import annotations

import argparse
import os
import re
import tempfile
from collections.abc import Mapping, Sequence
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PROVIDER_ROOT = REPO_ROOT / "docs/02-architecture/diagrams/providers"
MAX_DIAGRAM_BYTES = 2_000_000

_PUBLISHED_HEADER_RE = re.compile(
    r"\A_{20,}\r?\n.*?\r?\n_{20,}\r?\n+",
    re.DOTALL,
)
_METADATA_RE = re.compile(
    r"^%%\s+@(?P<key>version|date|type|level|nodes|adr)\s+(?P<value>[^\r\n]+)$"
)


def _split_frontmatter(body: str) -> tuple[str, str] | None:
    """Split leading YAML frontmatter without a backtracking regex."""
    opening = "---\n"
    closing = "\n---\n"
    if not body.startswith(opening):
        return None
    closing_index = body.find(closing, len(opening))
    if closing_index < 0:
        return None
    remainder = body[closing_index + len(closing) :].lstrip("\n")
    return body[len(opening) : closing_index], remainder


_NODE_RE = re.compile(
    r"(?<![\w])([A-Za-z_][A-Za-z0-9_]*+)[ \t]*+"
    r"(?=[\[({>/])"
)
_STYLE_RE = re.compile(
    r"^\s*style\s+(?P<node>[A-Za-z_][A-Za-z0-9_]*)\s+"
    r"fill:(?P<fill>#[0-9A-Fa-f]{6})(?:,.*)?\s*$"
)

_FILL_CLASS = {
    "#e1f5ff": "interfaces",
    "#c8e6c9": "app",
    "#ffcccc": "infra",
    "#fff4e6": "domain",
    "#ffe0b2": "composition",
}
_CLASS_DEFS = {
    "domain": "    classDef domain fill:#f5f3ff,stroke:#7c3aed,stroke-width:2px",
    "app": "    classDef app fill:#f0fdf4,stroke:#16a34a,stroke-width:2px",
    "infra": "    classDef infra fill:#fff1f2,stroke:#dc2626,stroke-width:2px",
    "composition": (
        "    classDef composition fill:#fff7ed,stroke:#ea580c,stroke-width:2px"
    ),
    "interfaces": (
        "    classDef interfaces fill:#eff6ff,stroke:#2563eb,stroke-width:2px"
    ),
}


def _single_line(value: object, *, default: str = "") -> str:
    """Normalize one metadata value to a single deterministic line."""
    rendered = " ".join(str(value).split()) if value is not None else ""
    return rendered or default


def _metadata_value(
    payload: Mapping[str, object],
    existing: Mapping[str, str],
    key: str,
    *,
    fallback: str,
) -> str:
    """Resolve metadata from YAML, then retained comments, then a fallback."""
    return _single_line(payload.get(key), default=existing.get(key, fallback))


def _normalize_adr_references(value: object) -> str:
    """Render YAML ADR references as a stable comma-separated identifier list."""
    if value is None:
        return ""
    items: Sequence[object] = value if isinstance(value, list) else [value]
    identifiers: list[str] = []
    for item in items:
        if isinstance(item, Mapping):
            identifiers.extend(_single_line(key) for key in item)
            continue
        identifier = _single_line(item).split(":", maxsplit=1)[0].strip()
        if identifier:
            identifiers.append(identifier)
    return ", ".join(dict.fromkeys(identifiers))


def _split_existing_metadata(text: str) -> tuple[dict[str, str], str]:
    """Remove the legacy leading ``%% @...`` block and return its values."""
    metadata: dict[str, str] = {}
    lines = text.lstrip("\n").splitlines()
    consumed = 0
    for line in lines:
        match = _METADATA_RE.match(line.strip())
        if match is None:
            if not line.strip():
                consumed += 1
                continue
            break
        metadata[match.group("key")] = match.group("value").strip()
        consumed += 1
    return metadata, "\n".join(lines[consumed:]).lstrip("\n")


def _convert_inline_styles(text: str) -> str:
    """Map the known provider fill palette to canonical class assignments."""
    assignments: dict[str, list[str]] = {}
    retained_lines: list[str] = []
    for line in text.splitlines():
        if not line.lstrip().startswith("style "):
            retained_lines.append(line)
            continue
        match = _STYLE_RE.match(line)
        if match is None:
            raise ValueError(f"unsupported provider inline style: {line.strip()}")
        fill = match.group("fill").lower()
        class_name = _FILL_CLASS.get(fill)
        if class_name is None:
            raise ValueError(f"unsupported provider fill colour: {fill}")
        assignments.setdefault(class_name, []).append(match.group("node"))

    if not assignments:
        return text.rstrip()

    converted = "\n".join(retained_lines).rstrip()
    additions: list[str] = []
    for class_name in _CLASS_DEFS:
        if class_name not in assignments:
            continue
        if f"classDef {class_name} " not in converted:
            additions.append(_CLASS_DEFS[class_name])
    additions.append("")
    additions.extend(
        f"    class {','.join(nodes)} {class_name}"
        for class_name, nodes in assignments.items()
    )
    return f"{converted}\n\n" + "\n".join(additions).rstrip()


def convert_legacy_content(content: str) -> str | None:
    """Return converted Mermaid text, or ``None`` when already compliant."""
    normalized = content.replace("\r\n", "\n")
    body = _PUBLISHED_HEADER_RE.sub("", normalized, count=1)
    if body.startswith("%% Title:"):
        return None

    frontmatter = _split_frontmatter(body)
    if frontmatter is None:
        return None
    frontmatter_payload, content_body = frontmatter
    loaded = yaml.safe_load(frontmatter_payload) or {}
    if not isinstance(loaded, Mapping):
        raise ValueError("provider diagram YAML frontmatter must be a mapping")
    payload = {str(key): value for key, value in loaded.items()}

    existing, diagram_body = _split_existing_metadata(content_body)
    title = _single_line(payload.get("title"))
    description = _single_line(payload.get("description"))
    if not title or not description:
        raise ValueError("provider diagram frontmatter requires title and description")

    version = _metadata_value(payload, existing, "version", fallback="1.0.0")
    date = _single_line(
        payload.get("last_verified"),
        default=existing.get("date", "1970-01-01"),
    )
    diagram_type = _metadata_value(payload, existing, "type", fallback="flowchart")
    level = _metadata_value(payload, existing, "level", fallback="system")
    node_count = _single_line(
        payload.get("nodes"),
        default=existing.get("nodes", str(len(set(_NODE_RE.findall(diagram_body))))),
    )
    adr_references = _normalize_adr_references(payload.get("adr_references"))
    if not adr_references:
        adr_references = existing.get("adr", "")

    metadata_lines = [
        f"%% Title: {title}",
        f"%% Description: {description}",
        f"%% @version {version}",
        f"%% @date {date}",
        f"%% @type {diagram_type}",
        f"%% @level {level}",
        f"%% @nodes {node_count}",
    ]
    if adr_references:
        metadata_lines.append(f"%% @adr {adr_references}")

    converted_body = _convert_inline_styles(diagram_body)
    return "\n".join([*metadata_lines, converted_body]).rstrip() + "\n"


def _safe_diagram_path(path: Path, provider_root: Path) -> Path:
    """Resolve a non-symlink ``.mmd`` target below the provider root."""
    if path.is_symlink():
        raise ValueError(f"refusing symlinked provider diagram: {path}")
    resolved_root = provider_root.resolve()
    resolved = path.resolve()
    if resolved_root != resolved and resolved_root not in resolved.parents:
        raise ValueError(f"refusing provider diagram outside {resolved_root}: {path}")
    if resolved.suffix != ".mmd":
        raise ValueError(f"expected a .mmd provider diagram: {path}")
    if not resolved.is_file():
        raise ValueError(f"provider diagram does not exist: {path}")
    if resolved.stat().st_size > MAX_DIAGRAM_BYTES:
        raise ValueError(f"provider diagram exceeds {MAX_DIAGRAM_BYTES} bytes: {path}")
    return resolved


def _write_atomic(path: Path, content: str) -> None:
    """Replace a validated diagram atomically in its current directory."""
    fd, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary_path = Path(temporary_name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(content)
        os.replace(temporary_path, path)
    finally:
        temporary_path.unlink(missing_ok=True)


def convert_file(path: Path, *, provider_root: Path, write: bool) -> bool:
    """Convert one validated file and return whether conversion was needed."""
    safe_path = _safe_diagram_path(path, provider_root)
    converted = convert_legacy_content(safe_path.read_text(encoding="utf-8"))
    if converted is None:
        return False
    if write:
        _write_atomic(safe_path, converted)
    return True


def _discover_targets(paths: Sequence[Path], provider_root: Path) -> list[Path]:
    """Return explicit targets or every canonical provider ``.mmd`` file."""
    if paths:
        return sorted(paths)
    return sorted(provider_root.glob("*/*.mmd"))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("paths", nargs="*", type=Path)
    parser.add_argument(
        "--check",
        action="store_true",
        help="report legacy files without modifying them and fail on drift",
    )
    parser.add_argument(
        "--provider-root",
        type=Path,
        default=PROVIDER_ROOT,
        help=argparse.SUPPRESS,
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    """Convert provider diagrams, or check that no legacy input remains."""
    args = _parser().parse_args(argv)
    provider_root = args.provider_root.resolve()
    changed: list[Path] = []
    for path in _discover_targets(args.paths, provider_root):
        if convert_file(path, provider_root=provider_root, write=not args.check):
            changed.append(path)
            action = "needs conversion" if args.check else "converted"
            print(f"{action}: {path}")

    if args.check and changed:
        return 1
    print(f"provider diagrams requiring conversion: {len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
