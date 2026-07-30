"""Normalized duplication audit for generated pipeline passport Markdown."""

from __future__ import annotations

import re
from collections import Counter
from pathlib import Path
from typing import TypedDict


class DuplicateAudit(TypedDict):
    passport_count: int
    total_markdown_lines: int
    duplicate_line_groups: int
    duplicate_paragraph_groups: int
    duplicate_diagram_groups: int
    identity_duplicate_count: int
    empty_section_count: int
    average_passport_lines: float
    maximum_passport_lines: int


_CODE_VALUE = re.compile(r"`[^`\n]+`")
_PIPELINE_VALUE = re.compile(
    r"\b(?:chembl|crossref|openalex|pubchem|pubmed|semanticscholar|uniprot|composite)"
    r"_[a-z0-9_]+\b"
)


def _normalize(text: str) -> str:
    text = _CODE_VALUE.sub("`<value>`", text)
    text = _PIPELINE_VALUE.sub("<pipeline>", text)
    text = re.sub(r"\s+", " ", text).strip().lower()
    return text


def audit_markdown_texts(texts: list[str]) -> DuplicateAudit:
    """Measure structural duplication after Markdown/value normalization."""
    lines = [
        _normalize(line)
        for text in texts
        for line in text.splitlines()
        if line.strip() and not re.fullmatch(r"[-| :]+", line.strip())
    ]
    paragraphs = [
        _normalize(paragraph)
        for text in texts
        for paragraph in re.split(r"\n\s*\n", text)
        if paragraph.strip() and not paragraph.lstrip().startswith("#")
    ]
    diagrams = [
        _normalize(diagram)
        for text in texts
        for diagram in re.findall(r"```mermaid\n(.*?)```", text, re.DOTALL)
    ]
    line_counts = Counter(item for item in lines if len(item) >= 12)
    paragraph_counts = Counter(item for item in paragraphs if len(item) >= 40)
    diagram_counts = Counter(diagrams)
    line_lengths = [len(text.splitlines()) for text in texts]
    return {
        "passport_count": len(texts),
        "total_markdown_lines": sum(line_lengths),
        "duplicate_line_groups": sum(value > 1 for value in line_counts.values()),
        "duplicate_paragraph_groups": sum(
            value > 1 for value in paragraph_counts.values()
        ),
        "duplicate_diagram_groups": sum(value > 1 for value in diagram_counts.values()),
        "identity_duplicate_count": sum(
            max(0, text.count("Typed identity") - 1) for text in texts
        ),
        "empty_section_count": sum(
            len(re.findall(r"^##[^\n]+\n\s*(?=##|\Z)", text, re.MULTILINE))
            for text in texts
        ),
        "average_passport_lines": (
            round(sum(line_lengths) / len(line_lengths), 1) if line_lengths else 0.0
        ),
        "maximum_passport_lines": max(line_lengths, default=0),
    }


def audit_paths(paths: list[Path]) -> DuplicateAudit:
    return audit_markdown_texts(
        [path.read_text(encoding="utf-8") for path in sorted(paths)]
    )
