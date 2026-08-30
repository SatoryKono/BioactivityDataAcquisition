"""Fail-closed contracts for #9029 / #9031 / #9030."""

from __future__ import annotations

from pathlib import Path

import pytest

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_readme_mcp_env_example_has_no_neo4j_password_literal() -> None:
    readme = _read("README.md")
    assert "bioetl_secure_password" not in readme
    assert "NEO4J_AUTH=" in readme


def test_security_md_incorrect_example_is_not_credential_shaped() -> None:
    text = _read(".github/SECURITY.md")
    assert "sk-1234567890" not in text
    assert "sk-EXAMPLE_DO_NOT_USE" in text


def test_gitleaks_does_not_allowlist_live_sk_or_hex_tokens() -> None:
    text = _read(".gitleaks.toml")
    assert "'''sk-[a-zA-Z0-9]+'''" not in text
    assert "'''[a-f0-9]{40}'''" not in text
    assert "tests/fixtures/" in text
    assert "msk-[a-zA-Z0-9]+" in text


def test_commitlint_does_not_ignore_nonconventional_headers() -> None:
    text = _read("commitlint.config.mjs")
    assert "message.startsWith('Merge')" in text
    assert "historical commits that cannot be rewritten" not in text
    assert (
        "feat|fix|refactor|docs|test|chore|perf|ci|build|style|revert)[(:]" not in text
    )


def test_runtime_dockerfile_does_not_shadow_installed_wheel() -> None:
    text = _read("Dockerfile.bioetl")
    assert "PYTHONPATH=/app/src" not in text
    assert "COPY --chown=root:root src/ ./src/" not in text
    assert "COPY --chown=root:root configs/ ./configs/" in text
    assert 'ENTRYPOINT ["bioetl"]' in text


def test_getting_started_data_permissions_are_least_privilege() -> None:
    text = _read("docs/03-guides/getting-started.md")
    assert "chmod -R 755 data/" not in text
    assert "chmod -R u+rwX,go-rwx data/" in text


def test_date_handling_guide_uses_last_calendar_day() -> None:
    text = _read("docs/03-guides/date-handling.md")
    assert "2024-03-30" not in text
    assert "2024-03-31" in text


def test_pipeline_configuration_chembl_example_matches_live_rate_limit() -> None:
    text = _read("docs/03-guides/pipeline-configuration.md")
    assert "requests_per_second: 0.1" in text
    assert "burst: 1" in text
    assert "max_url_length: 1000" in text or "max_url_length: 2000" in text
