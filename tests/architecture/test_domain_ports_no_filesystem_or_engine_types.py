"""Architecture ratchet for domain port contract purity."""

from __future__ import annotations

from pathlib import Path
import re

import pytest

PORTS_DIR = Path("src/bioetl/domain/ports")

FORBIDDEN_TOKENS = (
    "from pathlib import Path",
    "import pathlib",
)

FORBIDDEN_PATTERNS = (
    r"\bPath\b",
    r"\bpyarrow\b",
    r"\bPyArrow\b",
    r"\bpolars\b",
    r"\bPolars\b",
    r"\bpa\.Table\b",
)


def _python_files() -> list[Path]:
    return sorted(PORTS_DIR.rglob("*.py"))


@pytest.mark.architecture
def test_domain_ports_do_not_reference_filesystem_or_engine_specific_types() -> None:
    """Domain ports must stay free of filesystem and concrete table-engine types."""
    violations: list[str] = []

    for py_file in _python_files():
        source = py_file.read_text(encoding="utf-8")
        for token in FORBIDDEN_TOKENS:
            if token in source:
                violations.append(f"{py_file}:{token}")
        for pattern in FORBIDDEN_PATTERNS:
            if re.search(pattern, source):
                violations.append(f"{py_file}:/{pattern}/")

    assert not violations, (
        "Domain ports must not expose filesystem or engine-specific contract "
        f"tokens. Violations: {violations}"
    )
