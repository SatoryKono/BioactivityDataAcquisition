"""ADR metadata extraction utilities."""

from __future__ import annotations

STATUS_LABELS = ("Status", "Статус")
DATE_LABELS = ("Date", "Дата")


def parse_h1_title(text: str) -> str | None:
    """Extract H1 title from markdown text.

    Args:
        text: Markdown text.

    Returns:
        H1 title or None if not found.
    """
    for line in text.splitlines():
        if line.startswith("# "):
            return line[2:].strip()
    return None


def extract_prefixed_line_value(
    stripped: str,
    lowered: str,
    label_variants: tuple[str, ...],
) -> str | None:
    """Extract value from line with prefixed label.

    Args:
        stripped: Stripped line.
        lowered: Lowercased line.
        label_variants: Label variants to match.

    Returns:
        Extracted value or None.
    """
    for label in label_variants:
        for prefix in (f"**{label}:**", f"{label}:"):
            if lowered.startswith(prefix):
                value = stripped[len(prefix) :].strip()
                return value or None
    return None


def extract_table_line_value(
    stripped: str,
    label_variants: tuple[str, ...],
) -> str | None:
    """Extract value from table row.

    Args:
        stripped: Stripped line.
        label_variants: Label variants to match.

    Returns:
        Extracted value or None.
    """
    if not stripped.startswith("|"):
        return None
    cells = [cell.strip() for cell in stripped.split("|") if cell.strip()]
    if len(cells) < 2:
        return None
    header = cells[0].strip("* ").casefold()
    if header in label_variants and cells[1]:
        return cells[1]
    return None


def extract_labeled_line_value(text: str, labels: tuple[str, ...]) -> str | None:
    """Extract value from labeled line in text.

    Args:
        text: Text to search.
        labels: Label variants to match.

    Returns:
        Extracted value or None.
    """
    label_variants = tuple(label.casefold() for label in labels)
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue

        lowered = stripped.casefold()
        prefixed_value = extract_prefixed_line_value(
            stripped,
            lowered,
            label_variants,
        )
        if prefixed_value is not None:
            return prefixed_value

        table_value = extract_table_line_value(stripped, label_variants)
        if table_value is not None:
            return table_value
    return None


def extract_with_patterns(text: str, patterns: tuple[str, ...]) -> str | None:
    """Backward-compatible wrapper for labeled line extraction.

    Args:
        text: Text to search.
        patterns: Pattern variants to match.

    Returns:
        Extracted value or None.
    """
    return extract_labeled_line_value(text, patterns)


def first_content_line(lines: list[str], start: int) -> str | None:
    """Return first non-empty content line after a heading.

    Args:
        lines: List of lines.
        start: Starting index.

    Returns:
        First content line or None.
    """
    for candidate in lines[start + 1 : start + 8]:
        value = candidate.strip()
        if not value:
            continue
        if value.startswith("#") or value.startswith("|"):
            return None
        return value
    return None


def match_heading_to_section(
    heading: str,
    normalized_names: set[str],
) -> tuple[str | None, bool]:
    """Check heading against section names.

    Args:
        heading: Heading text.
        normalized_names: Normalized section names.

    Returns:
        Tuple of (inline_value, is_exact_match).
    """
    heading_lower = heading.lower()
    for name in normalized_names:
        if heading_lower == name:
            return None, True
        prefix = f"{name}:"
        if heading_lower.startswith(prefix):
            value = heading[len(prefix) :].strip()
            return (value if value else None), False
    return None, False


def extract_from_section(
    text: str,
    section_names: tuple[str, ...],
) -> str | None:
    """Extract value from markdown section.

    Args:
        text: Markdown text.
        section_names: Section name variants.

    Returns:
        Extracted value or None.
    """
    lines = text.splitlines()[:120]
    normalized_names = {name.lower() for name in section_names}

    for index, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("#"):
            continue

        heading = stripped.lstrip("#").strip()
        inline_value, is_exact = match_heading_to_section(heading, normalized_names)

        if is_exact:
            result = first_content_line(lines, index)
            if result is not None:
                return result
        elif inline_value is not None:
            return inline_value
    return None


def extract_meta(text: str) -> tuple[str | None, str | None]:
    """Extract status and date from ADR metadata.

    Args:
        text: ADR text.

    Returns:
        Tuple of (status, date) or (None, None).
    """
    status = extract_labeled_line_value(text, STATUS_LABELS)
    if status is None:
        status = extract_from_section(text, ("Status", "Статус"))

    date = extract_labeled_line_value(text, DATE_LABELS)
    if date is None:
        date = extract_from_section(text, ("Date", "Дата"))

    return status, date
