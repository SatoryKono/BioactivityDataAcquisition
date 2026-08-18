# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Запретить утечку presentation-adapter literals в Domain и Application."""

from __future__ import annotations

import ast
import re
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
CORE_ROOTS = (
    ROOT / "src" / "bioetl" / "domain",
    ROOT / "src" / "bioetl" / "application",
)
FORBIDDEN_PRESENTATION_PATTERNS = {
    "grafana": re.compile(r"\bgrafana\b", re.IGNORECASE),
    "tempo": re.compile(r"\btempo\b", re.IGNORECASE),
    "loki": re.compile(r"\bloki\b", re.IGNORECASE),
    "traceql": re.compile(r"\btraceql\b", re.IGNORECASE),
    "/a/": re.compile(r"/a/"),
}


def _python_files() -> list[Path]:
    return [path for root in CORE_ROOTS for path in sorted(root.rglob("*.py"))]


def _presentation_literal_violations(path: Path) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    violations: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str):
            continue
        matched_tokens = [
            token
            for token, pattern in FORBIDDEN_PRESENTATION_PATTERNS.items()
            if pattern.search(node.value)
        ]
        if matched_tokens:
            relative_path = path.relative_to(ROOT).as_posix()
            violations.append(
                f"{relative_path}:{node.lineno}: {', '.join(matched_tokens)}"
            )
    return violations


@pytest.mark.architecture
def test_domain_and_application_do_not_embed_presentation_adapter_literals() -> None:
    """Core слои публикуют только нейтральные facts и не знают UI adapters."""
    violations = [
        violation
        for path in _python_files()
        for violation in _presentation_literal_violations(path)
    ]

    assert not violations, (
        "Domain/Application must not embed Grafana, Tempo, Loki, TraceQL, or UI "
        "route literals. Keep presentation-specific handoff in an optional adapter:\n"
        + "\n".join(violations)
    )
