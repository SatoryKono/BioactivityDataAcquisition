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
"""Architecture checks for MCP token loading, validation, and docs."""

from __future__ import annotations

from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def test_repo_env_loaders_preserve_mcp_token_aliases() -> None:
    shell_loader = _read("scripts/ops/support/load_repo_env.sh")
    powershell_loader = _read("scripts/ai/mcp/support/load_repo_env.ps1")

    for text in (shell_loader, powershell_loader):
        assert "GITHUB_PERSONAL_ACCESS_TOKEN" in text
        assert "GITHUB_TOKEN" in text
        assert "BRAVE_SEARCH_API_KEY" in text
        assert "BRAVE_API_KEY1" in text
        assert "BRAVE_API_KEY" in text
        assert "GRAFANA_SERVICE_ACCOUNT_TOKEN" in text
        assert "HUB_PAT_TOKEN" in text

    assert 'export OPENROUTER_API_KEY="${OPENAI_API_KEY}"' not in shell_loader
    assert "$env:OPENROUTER_API_KEY = $env:OPENAI_API_KEY" not in powershell_loader


def test_token_validation_helpers_are_used_by_token_bearing_wrappers() -> None:
    assert (ROOT / "scripts/ai/mcp/support/token_validation.sh").exists()
    assert (ROOT / "scripts/ai/mcp/support/token_validation.ps1").exists()

    required_shell_wrappers = {
        "scripts/ai/mcp/github-mcp-wrapper.sh": "mcp_validate_required_token",
        "scripts/ai/mcp/mcp_brave_search_wrapper.sh": "mcp_validate_required_token",
        "scripts/ai/mcp/mcp_grafana_wrapper.sh": "mcp_validate_optional_token",
        "scripts/ai/mcp/mcp_prometheus_wrapper.sh": "mcp_validate_optional_token",
        "scripts/ai/mcp/mcp_neo4j_cypher_wrapper.sh": "mcp_validate_neo4j_credentials",
        "scripts/ai/mcp/mcp_neo4j_memory_wrapper.sh": "mcp_validate_neo4j_credentials",
    }
    for relative_path, expected_call in required_shell_wrappers.items():
        text = _read(relative_path)
        assert "support/token_validation.sh" in text
        assert expected_call in text
        assert "mcp_exit_if_validate_only" in text

    required_powershell_wrappers = {
        "scripts/ai/mcp/github-mcp-wrapper.ps1": "Test-McpRequiredToken",
        "scripts/ai/mcp/mcp_brave_search_wrapper.ps1": "Test-McpRequiredToken",
        "scripts/ai/mcp/mcp_grafana_wrapper.ps1": "Test-McpOptionalToken",
        "scripts/ai/mcp/mcp_prometheus_wrapper.ps1": "Test-McpOptionalToken",
        "scripts/ai/mcp/mcp_neo4j_cypher_wrapper.ps1": "Test-McpNeo4jCredentials",
        "scripts/ai/mcp/mcp_neo4j_memory_wrapper.ps1": "Test-McpNeo4jCredentials",
    }
    for relative_path, expected_call in required_powershell_wrappers.items():
        text = _read(relative_path)
        assert "support/token_validation.ps1" in text
        assert expected_call in text
        assert "Exit-McpValidateOnly" in text


def test_mcp_env_loading_smoke_redacts_secret_values() -> None:
    text = _read("scripts/ai/mcp/test_env_loading.sh")

    assert "NEO4J_PASSWORD=${NEO4J_PASSWORD" not in text
    assert "NEO4J_AUTH=${NEO4J_AUTH" not in text
    assert "SET" in text
    assert "NOT SET" in text
    assert "bolt://host.docker.internal:7687" not in text
    assert "(bolt|neo4j)" in text
    assert '[[ -z "${NEO4J_PASSWORD:-}" ]]' in text
    assert '[[ "${NEO4J_PASSWORD}" == *_secure_password ]]' in text
    assert "matches a legacy placeholder pattern" in text


def test_mcp_token_docs_cover_sources_rotation_validation_and_ci_stance() -> None:
    token_doc = _read("docs/00-project/ai/mcp-token-configuration.md")
    governance = _read("docs/00-project/ai/mcp-governance.md")
    runtime_config = _read(
        "docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md"
    )

    for needle in (
        "Token Matrix",
        "Wrapper Validation",
        "Historical Exposure Note",
        "Troubleshooting",
        "CI/CD Stance",
        "GITHUB_PERSONAL_ACCESS_TOKEN",
        "BRAVE_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "configured separately",
        "90 days",
        "historical `.env` / `.env.local` path entries",
        "treated as exposed and rotated before use",
    ):
        assert needle in token_doc

    assert "mcp-token-configuration.md" in governance
    assert "BIOETL_MCP_VALIDATE_ONLY=1" in governance
    assert "BIOETL_UVX_DIRECT_NETWORK=1" in governance
    assert "token_validation.sh" in runtime_config
    assert "CI must not require personal MCP tokens" in runtime_config
    assert "third-party service tokens" in runtime_config


def test_ref_uses_env_header_without_embedding_secret_in_url() -> None:
    setup_mcp = _read("scripts/ai/codex/setup_mcp.py")
    launcher = _read("scripts/ai/codex/helper/run-codex-impl.sh")

    assert 'REF_API_KEY_ENV_VAR = "REF_TOOL_API_KEY"' in setup_mcp
    assert '"x-ref-api-key": REF_API_KEY_ENV_VAR' in setup_mcp
    assert "REF_TOOL_API_KEY" in launcher
    assert "load_repo_env_if_present" in launcher
    assert "?apiKey=" not in setup_mcp


def test_deepwiki_uses_env_headers_without_embedding_secrets() -> None:
    setup_mcp = _read("scripts/ai/codex/setup_mcp.py")

    assert 'DEEPWIKI_API_KEY_ENV_VAR = "DEEPWIKI_API_KEY"' in setup_mcp
    assert 'DEEPWIKI_ORGANISATION_ID_ENV_VAR = "DEEPWIKI_ORGANISATION_ID"' in setup_mcp
    assert '"x-deepwiki-api-key": DEEPWIKI_API_KEY_ENV_VAR' in setup_mcp
    assert '"x-deepwiki-organisation-id": DEEPWIKI_ORGANISATION_ID_ENV_VAR' in setup_mcp


def test_env_example_documents_mcp_token_sources_without_real_tokens() -> None:
    text = _read(".env.example")

    for needle in (
        "Token status markers",
        "GITHUB_PERSONAL_ACCESS_TOKEN=",
        "BRAVE_API_KEY=",
        "PROMETHEUS_TOKEN=",
        "GRAFANA_SERVICE_ACCOUNT_TOKEN=",
        "HUB_PAT_TOKEN=",
        "NEO4J_AUTH=neo4j/bioetl_secure_password",
        "Never commit real token values",
    ):
        assert needle in text

    assert "ghp_" not in text
    assert "github_pat_" not in text


def test_readme_mcp_env_block_does_not_embed_neo4j_password() -> None:
    readme = _read("README.md")
    assert "bioetl_secure_password" not in readme
