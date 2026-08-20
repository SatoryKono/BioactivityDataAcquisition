"""Load and validate Prompt Library REGISTRY.yaml and card frontmatter."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
PROMPTS_ROOT = REPO_ROOT / "docs" / "00-project" / "ai" / "prompts"
REGISTRY_PATH = PROMPTS_ROOT / "REGISTRY.yaml"
SCHEMA_PATH = PROMPTS_ROOT / "_schema" / "prompt.schema.json"

STATUS_ENUM = frozenset({"draft", "active", "deprecated", "archived"})
CLASS_ENUM = frozenset(
    {"operator-paste", "campaign", "fragment", "mirror", "historical", "index"}
)
ID_PATTERN = re.compile(r"^prompt\.[a-z0-9]+(\.[a-z0-9-]+)+$")
FRONTMATTER_DELIMITER = "---"

# Mandatory guardrail fragments for operator-paste (basename match)
MANDATORY_GUARDRAILS = frozenset(
    {
        "debt-budget-ban.md",
        "env-guardrail.md",
        "git-safety.md",
    }
)

DEFAULT_OPERATOR_PASTE_MAX_LINES = 120
DEFAULT_CAMPAIGN_MAX_LINES = 400


@dataclass(frozen=True, slots=True)
class RegistryEntry:
    id: str
    path: str
    status: str
    class_: str
    tags: tuple[str, ...] = ()
    summary: str = ""

    @property
    def absolute_path(self) -> Path:
        return PROMPTS_ROOT / self.path


@dataclass(slots=True)
class PromptCard:
    id: str
    version: str
    status: str
    class_: str
    owner: str
    path: Path
    body: str
    runtimes: list[str] = field(default_factory=list)
    params: list[str] = field(default_factory=list)
    includes: list[str] = field(default_factory=list)
    related_ssot: list[str] = field(default_factory=list)
    anti_patterns: list[str] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    summary: str = ""
    supersedes: str | None = None
    successor: str | None = None
    waive_guardrails: str | None = None
    max_body_lines: int | None = None
    raw_frontmatter: dict[str, Any] = field(default_factory=dict)


def load_registry(path: Path | None = None) -> list[RegistryEntry]:
    reg_path = path or REGISTRY_PATH
    data = yaml.safe_load(reg_path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"REGISTRY must be a mapping: {reg_path}")
    entries_raw = data.get("entries")
    if not isinstance(entries_raw, list):
        raise ValueError(f"REGISTRY.entries must be a list: {reg_path}")
    entries: list[RegistryEntry] = []
    for item in entries_raw:
        if not isinstance(item, dict):
            raise ValueError(f"REGISTRY entry must be a mapping: {item!r}")
        entries.append(
            RegistryEntry(
                id=str(item["id"]),
                path=str(item["path"]),
                status=str(item.get("status", "active")),
                class_=str(item.get("class", "operator-paste")),
                tags=tuple(str(t) for t in (item.get("tags") or [])),
                summary=str(item.get("summary") or ""),
            )
        )
    return entries


def parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != FRONTMATTER_DELIMITER:
        return {}, text
    closing_index = next(
        (
            index
            for index, line in enumerate(lines[1:], start=1)
            if line.strip() == FRONTMATTER_DELIMITER
        ),
        None,
    )
    if closing_index is None:
        return {}, text
    meta = yaml.safe_load("".join(lines[1:closing_index])) or {}
    if not isinstance(meta, dict):
        raise ValueError("frontmatter must be a YAML mapping")
    body = "".join(lines[closing_index + 1 :])
    return meta, body


def _optional_text(meta: dict[str, Any], key: str) -> str | None:
    value = meta.get(key)
    return str(value) if value else None


def load_card(path: Path) -> PromptCard:
    text = path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    return PromptCard(
        id=str(meta.get("id") or path.stem),
        version=str(meta.get("version") or "0.0.0"),
        status=str(meta.get("status") or "draft"),
        class_=str(meta.get("class") or "operator-paste"),
        owner=str(meta.get("owner") or ""),
        path=path,
        body=body.lstrip("\n"),
        runtimes=[str(x) for x in (meta.get("runtimes") or [])],
        params=[str(x) for x in (meta.get("params") or [])],
        includes=[str(x) for x in (meta.get("includes") or [])],
        related_ssot=[str(x) for x in (meta.get("related_ssot") or [])],
        anti_patterns=[str(x) for x in (meta.get("anti_patterns") or [])],
        tags=[str(x) for x in (meta.get("tags") or [])],
        summary=str(meta.get("summary") or ""),
        supersedes=_optional_text(meta, "supersedes"),
        successor=_optional_text(meta, "successor"),
        waive_guardrails=_optional_text(meta, "waive_guardrails"),
        max_body_lines=(
            int(meta["max_body_lines"])
            if meta.get("max_body_lines") is not None
            else None
        ),
        raw_frontmatter=meta,
    )


def find_entry(entries: list[RegistryEntry], prompt_id: str) -> RegistryEntry:
    for entry in entries:
        if entry.id == prompt_id:
            return entry
    known = ", ".join(e.id for e in entries)
    raise KeyError(f"unknown prompt id {prompt_id!r}; known: {known}")


def resolve_include(rel: str) -> Path:
    """Resolve include path relative to prompts root."""
    candidate = PROMPTS_ROOT / rel
    if candidate.is_file():
        return candidate
    # allow bare fragments/foo.md already relative
    raise FileNotFoundError(f"include not found: {rel} (under {PROMPTS_ROOT})")


def fragment_body(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    _, body = parse_frontmatter(text)
    return body.strip() + "\n"


def body_line_count(body: str) -> int:
    if not body.strip():
        return 0
    return len(body.splitlines())
