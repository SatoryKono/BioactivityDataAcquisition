"""Chunking helpers for deterministic project-memory manifests."""

from __future__ import annotations

import ast
import hashlib
import json
import re
import tomllib
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path

import yaml

HEADING_PATTERN = re.compile(r"^(#{1,6})\s+(.*\S)\s*$")
FRONTMATTER_DELIMITER = "---"


@dataclass(frozen=True, slots=True)
class ChunkSection:
    """Represents a deterministic chunk section extracted from a source file."""

    index: int
    title: str
    level: int
    content: str
    symbol_kind: str | None = None


def _strip_frontmatter(text: str) -> str:
    lines = text.splitlines()
    if len(lines) >= 3 and lines[0].strip() == FRONTMATTER_DELIMITER:
        for idx in range(1, len(lines)):
            if lines[idx].strip() == FRONTMATTER_DELIMITER:
                return "\n".join(lines[idx + 1 :]).lstrip("\n")
    return text


def _slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug or "section"


def split_markdown_sections(text: str) -> list[ChunkSection]:
    """Split markdown text into section chunks using heading boundaries."""
    body = _strip_frontmatter(text).strip()
    if not body:
        return []

    sections: list[ChunkSection] = []
    current_title = "preamble"
    current_level = 0
    current_lines: list[str] = []
    current_index = 0

    for line in body.splitlines():
        match = HEADING_PATTERN.match(line)
        if match:
            content = "\n".join(current_lines).strip()
            if content:
                sections.append(
                    ChunkSection(
                        index=current_index,
                        title=current_title,
                        level=current_level,
                        content=content,
                        symbol_kind="markdown_section",
                    )
                )
                current_index += 1
            current_title = match.group(2).strip()
            current_level = len(match.group(1))
            current_lines = [line]
            continue
        current_lines.append(line)

    content = "\n".join(current_lines).strip()
    if content:
        sections.append(
            ChunkSection(
                index=current_index,
                title=current_title,
                level=current_level,
                content=content,
                symbol_kind="markdown_section",
            )
        )
    return sections


def split_python_symbols(text: str) -> list[ChunkSection]:
    """Split Python source into a preamble plus top-level symbol chunks."""
    stripped = text.strip()
    if not stripped:
        return []

    lines = text.splitlines()
    sections: list[ChunkSection] = []
    index = 0

    try:
        module = ast.parse(text)
    except SyntaxError:
        return [
            ChunkSection(
                index=0,
                title="module",
                level=0,
                content=text.strip(),
                symbol_kind="module",
            )
        ]

    top_level_nodes = [
        node
        for node in module.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    ]
    if not top_level_nodes:
        return [
            ChunkSection(
                index=0,
                title="module",
                level=0,
                content=text.strip(),
                symbol_kind="module",
            )
        ]

    first_lineno = min(node.lineno for node in top_level_nodes)
    preamble = "\n".join(lines[: first_lineno - 1]).strip()
    if preamble:
        sections.append(
            ChunkSection(
                index=index,
                title="module-preamble",
                level=0,
                content=preamble,
                symbol_kind="module_preamble",
            )
        )
        index += 1

    for node in top_level_nodes:
        start = max(node.lineno - 1, 0)
        end = getattr(node, "end_lineno", node.lineno)
        content = "\n".join(lines[start:end]).strip()
        if not content:
            continue
        if isinstance(node, ast.ClassDef):
            symbol_kind = "class"
        elif isinstance(node, ast.AsyncFunctionDef):
            symbol_kind = "async_function"
        else:
            symbol_kind = "function"
        sections.append(
            ChunkSection(
                index=index,
                title=node.name,
                level=1,
                content=content,
                symbol_kind=symbol_kind,
            )
        )
        index += 1
    return sections


def _json_ready_config_value(value: object) -> object:
    if isinstance(value, dict):
        return {str(key): _json_ready_config_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_ready_config_value(item) for item in value]
    if isinstance(value, tuple):
        return [_json_ready_config_value(item) for item in value]
    if isinstance(value, set):
        normalized = (_json_ready_config_value(item) for item in value)
        return sorted(normalized, key=lambda item: json.dumps(item, sort_keys=True))
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return value.as_posix()
    return value


def _serialize_config_value(value: object) -> str:
    normalized = _json_ready_config_value(value)
    if isinstance(normalized, (dict, list)):
        return json.dumps(normalized, indent=2, sort_keys=True, ensure_ascii=True)
    return json.dumps(normalized, ensure_ascii=True)


def split_config_sections(text: str, path: Path) -> list[ChunkSection]:
    """Split a config file into deterministic top-level sections."""
    stripped = text.strip()
    if not stripped:
        return []

    suffix = path.suffix.lower()
    try:
        if suffix in {".yaml", ".yml"}:
            payload = yaml.safe_load(text)
        elif suffix == ".json":
            payload = json.loads(text)
        elif suffix == ".toml":
            payload = tomllib.loads(text)
        else:
            payload = None
    except Exception:
        payload = None

    if not isinstance(payload, dict) or not payload:
        return [
            ChunkSection(
                index=0,
                title="document",
                level=0,
                content=stripped,
                symbol_kind="config_document",
            )
        ]

    sections: list[ChunkSection] = []
    for index, key in enumerate(payload):
        sections.append(
            ChunkSection(
                index=index,
                title=str(key),
                level=1,
                content=_serialize_config_value(payload[key]),
                symbol_kind="config_section",
            )
        )
    return sections


def chunk_source(path: Path, text: str) -> list[ChunkSection]:
    """Dispatch source chunking by file type and repository surface."""
    source_type = infer_source_type(path)
    if source_type in {"adr", "runbook", "doc", "plan"}:
        return split_markdown_sections(text)
    if source_type in {"code", "test"}:
        return split_python_symbols(text)
    if source_type == "memory":
        if path.suffix == ".py":
            return split_python_symbols(text)
        if path.suffix == ".md":
            return split_markdown_sections(text)
        if path.suffix in {".yaml", ".yml", ".json", ".toml"}:
            return split_config_sections(text, path)
        return [
            ChunkSection(
                index=0,
                title="document",
                level=0,
                content=text.strip(),
                symbol_kind="memory_document",
            )
        ]
    if source_type in {"config", "workflow", "dashboard"}:
        return split_config_sections(text, path)
    if source_type == "script" and path.suffix == ".py":
        return split_python_symbols(text)
    return [
        ChunkSection(
            index=0,
            title="document",
            level=0,
            content=text.strip(),
            symbol_kind="document",
        )
    ]


def content_hash(text: str) -> str:
    """Return a stable SHA-256 content hash for a text payload."""
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_chunk_id(source_path: str, title: str, index: int) -> str:
    """Build a deterministic chunk identifier from source path and section title."""
    digest = hashlib.sha1(f"{source_path}:{index}:{title}".encode()).hexdigest()[:12]
    return f"{source_path}#{_slugify(title)}-{digest}"


def infer_source_type(path: Path) -> str:
    """Classify a repository file into a deterministic RAG source type."""
    normalized = path.as_posix()
    if normalized.startswith("docs/02-architecture/decisions/ADR-"):
        return "adr"
    if normalized.startswith("docs/05-operations/runbooks/"):
        return "runbook"
    if normalized.startswith("docs/plans/"):
        return "plan"
    if normalized == ".devin/wiki.json":
        return "devin_wiki"
    if normalized.startswith("src/memory/"):
        return "memory"
    if normalized.startswith("src/bioetl/") and path.suffix == ".py":
        return "code"
    if normalized.startswith("tests/") and path.suffix == ".py":
        return "test"
    if normalized.startswith("configs/"):
        return "config"
    if normalized.startswith(".github/workflows/"):
        return "workflow"
    if normalized.startswith("grafana/"):
        return "dashboard"
    if normalized.startswith("scripts/"):
        return "script"
    return "doc"


def infer_domain(path: Path) -> str:
    """Infer a coarse domain label from a repository path."""
    normalized = path.as_posix()
    if normalized.startswith("docs/02-architecture/"):
        return "architecture"
    if normalized.startswith("docs/05-operations/"):
        return "operations"
    if normalized.startswith("src/memory/"):
        return "memory_subsystem"
    if normalized.startswith((".github/", "grafana/", "scripts/")):
        return "operations"
    if normalized.startswith("src/bioetl/"):
        return "runtime"
    if normalized.startswith("tests/"):
        return "quality"
    if normalized.startswith("configs/"):
        return "configuration"
    return "project"
