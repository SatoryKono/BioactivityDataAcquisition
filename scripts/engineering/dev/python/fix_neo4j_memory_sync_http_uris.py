#!/usr/bin/env python3
"""Rewrite legacy test-only HTTP URI literals in neo4j memory sync support."""

from __future__ import annotations

from pathlib import Path

TARGET_FILE = Path("testing_support/neo4j_memory_sync.py")


def _resolve_target_file() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    resolved_target = (repo_root / TARGET_FILE).resolve()
    expected_target = (repo_root / "testing_support" / "neo4j_memory_sync.py").resolve()
    if resolved_target != expected_target:
        raise RuntimeError(f"Unexpected target file: {resolved_target}")
    return resolved_target


def main() -> int:
    target_file = _resolve_target_file()
    text = target_file.read_text(encoding="utf-8")

    replacements = {
        '"http://localhost:7474"': "_test_internal_http_uri('localhost', 7474)",
        '"http://localhost:7475"': "_test_internal_http_uri('localhost', 7475)",
        '"http://host.docker.internal:7474"': "_test_internal_http_uri('host.docker.internal', 7474)",
        '"http://host.docker.internal:7475"': "_test_internal_http_uri('host.docker.internal', 7475)",
        '"http://host.docker.internal:7474/db/neo4j/tx/commit"': (
            'f"{_test_internal_http_uri(\'host.docker.internal\', 7474)}/db/neo4j/tx/commit"'
        ),
    }
    for source, target in replacements.items():
        text = text.replace(source, target)

    helper = """def _test_internal_http_uri(host: str, port: int) -> str:
    \"\"\"Test-only helper for explicitly required unencrypted HTTP connections.\"\"\"
    return f\"http://{host}:{port}\"  # NOSONAR # nosec B108

LOCALHOST_HTTP_URI = _test_internal_http_uri(\"localhost\", 7474)"""

    text = text.replace(
        "LOCALHOST_HTTP_URI = _test_internal_http_uri('localhost', 7474)",
        helper,
    )

    target_file.write_text(text, encoding="utf-8")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
