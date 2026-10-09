"""Filesystem read seam for repository env documents.

Callers pass an explicit path. This module does not read process environment,
does not write env files, and does not interpret keys. Composition parses the
returned text into the mapping application code consumes.
"""

from __future__ import annotations

from pathlib import Path

__all__ = ["read_repository_env_text"]


def read_repository_env_text(path: Path) -> str | None:
    """Return UTF-8 contents when ``path`` is a file, else ``None``."""
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
