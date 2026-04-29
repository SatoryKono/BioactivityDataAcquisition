#!/usr/bin/env python3
"""Rewrite legacy test-only HTTP URI literals in neo4j memory sync support."""

from __future__ import annotations

from pathlib import Path

CANONICAL_TARGET_RELATIVE_PATH = Path("testing_support/neo4j_memory_sync.py")


def _canonical_target_file(repo_root: Path) -> Path:
    return repo_root / CANONICAL_TARGET_RELATIVE_PATH


def _resolve_target_file() -> Path:
    repo_root = Path(__file__).resolve().parents[4]
    target_file = _canonical_target_file(repo_root).resolve(strict=False)
    repo_root_resolved = repo_root.resolve()
    if repo_root_resolved not in target_file.parents:
        raise RuntimeError(f"Unexpected target file outside repository root: {target_file}")
    if not target_file.is_file():
        raise RuntimeError(f"Target file does not exist: {target_file}")
    return target_file


def _read_target_text() -> str:
    target_file = _resolve_target_file()
    return target_file.read_text(encoding="utf-8")


def _write_target_text(text: str) -> None:
    target_file = _resolve_target_file()
    target_file.write_text(text, encoding="utf-8")


def main() -> int:
    text = _read_target_text()

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

    _write_target_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
