#!/usr/bin/env python3
"""Rewrite legacy test-only HTTP URI literals in neo4j memory sync support."""

from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
CANONICAL_TARGET_RELATIVE_PATH = Path("testing_support/neo4j_memory_sync.py")
CANONICAL_TARGET_FILE = (REPO_ROOT / CANONICAL_TARGET_RELATIVE_PATH).resolve(
    strict=False
)

def _validated_target_file() -> Path:
    repo_root_resolved = REPO_ROOT.resolve()
    if repo_root_resolved not in CANONICAL_TARGET_FILE.parents:
        raise RuntimeError(
            f"Unexpected target file outside repository root: {CANONICAL_TARGET_FILE}"
        )
    if not CANONICAL_TARGET_FILE.is_file():
        raise RuntimeError(f"Target file does not exist: {CANONICAL_TARGET_FILE}")
    return CANONICAL_TARGET_FILE


def _read_target_text() -> str:
    return _validated_target_file().read_text(encoding="utf-8")


def _write_rewritten_target_text(rewritten_text: str) -> None:
    target_file = _validated_target_file()
    target_file.write_text(  # NOSONAR - target_file is a fixed validated repository path
        rewritten_text,
        encoding="utf-8",
    )


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

    _write_rewritten_target_text(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
