"""Fail-closed contracts for #9029 / #9031 / #9030."""

from __future__ import annotations

import re
import json
import tomllib
from pathlib import Path

import pytest

from tests.helpers.secret_fingerprints import assert_no_historical_neo4j_passwords

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]


def _read(relative_path: str) -> str:
    return (ROOT / relative_path).read_text(encoding="utf-8")


def _docker_identity(raw: str) -> tuple[int, int]:
    parts = raw.split(":")
    assert len(parts) == 2

    def _component(value: str) -> int:
        if value == "root":
            return 0
        assert re.fullmatch(r"(?:0|[1-9][0-9]*)", value), value
        return int(value)

    return _component(parts[0]), _component(parts[1])


def test_readme_mcp_env_example_has_no_neo4j_password_literal() -> None:
    readme = _read("README.md")
    assert_no_historical_neo4j_passwords(readme)
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


def _precision_metadata_allowed(path: str, line: str) -> bool:
    rules = tomllib.loads(_read(".gitleaks.toml"))["rules"]
    generic = next(rule for rule in rules if rule["id"] == "generic-api-key")
    entries = [
        entry
        for entry in generic["allowlists"]
        if entry["description"].startswith("Reviewed #12474")
    ]
    assert len(entries) == 3
    for entry in entries:
        assert entry["condition"] == "AND"
        assert entry["regexTarget"] == "line"
    return any(
        any(re.search(pattern, path) for pattern in entry["paths"])
        and any(re.search(pattern, line) for pattern in entry["regexes"])
        for entry in entries
    )


def test_gitleaks_accepts_reviewed_source_identity_and_response_metadata() -> None:
    inventory_path = "configs/quality/external_resource_inventory.json"
    inventory = json.loads(_read(inventory_path))
    source = "src/bioetl/application/composite/dependency_key_resolvers.py"
    line = (
        json.dumps(source) + ": " + json.dumps(inventory["source_files"][source]) + ","
    )
    assert _precision_metadata_allowed(inventory_path, line)
    assert _precision_metadata_allowed(inventory_path, "\n" + line)
    assert not _precision_metadata_allowed(inventory_path, "prefix" + line)
    assert not _precision_metadata_allowed(inventory_path, line + "suffix")
    assert not _precision_metadata_allowed(
        inventory_path, line + '\n"api_key": "unexpected"'
    )
    assert not _precision_metadata_allowed("other/" + inventory_path, line)
    for filename, header in (
        ("uniprot_headers.txt", "x-api-deployment-date"),
        ("semanticscholar_headers.txt", "x-amz-apigw-id"),
    ):
        path = "reports/evidence/12461/" + filename
        actual = next(
            line
            for line in _read(path).splitlines()
            if line.lower().startswith(header + ":")
        )
        assert _precision_metadata_allowed(path, actual)
        assert _precision_metadata_allowed(path, "\n" + actual)
        assert not _precision_metadata_allowed("other/" + path, actual)


@pytest.mark.parametrize(
    "path",
    [
        "configs/quality/external_resource_inventory.json",
        "reports/evidence/12461/uniprot_headers.txt",
        "reports/evidence/12461/semanticscholar_headers.txt",
    ],
)
def test_gitleaks_precision_never_excludes_credential_assignments(path: str) -> None:
    value = "".join(
        ("7e91", "c4a6", "b308", "f2d5", "a947", "d10c", "e6b8", "039f", "2c75", "a461")
    )
    for name in ("api_key", "access_token", "authorization"):
        assert not _precision_metadata_allowed(
            path, json.dumps(name) + ': "' + value + '"'
        )
    # Even the allowed source-path key cannot hide an arbitrary 40-hex credential.
    source = "src/bioetl/application/composite/dependency_key_resolvers.py"
    assert not _precision_metadata_allowed(
        path, json.dumps(source) + ': "' + value + '"'
    )


def test_commitlint_does_not_ignore_nonconventional_headers() -> None:
    text = _read("commitlint.config.mjs")
    # Git-style merge subjects only (word-boundary, case-insensitive). Do not
    # swallow `mergeable` or other nonconventional types.
    assert "/^merge\\b/i" in text
    assert "historical commits that cannot be rewritten" not in text
    assert (
        "feat|fix|refactor|docs|test|chore|perf|ci|build|style|revert)[(:]" not in text
    )


def test_runtime_dockerfile_does_not_shadow_installed_wheel() -> None:
    text = _read("Dockerfile.bioetl")
    assert "PYTHONPATH=/app/src" not in text
    assert "COPY --chown=root:root src/ ./src/" not in text
    configs_copies = [
        line
        for line in text.splitlines()
        if line.startswith("COPY ") and " configs/ ./configs/" in line
    ]
    assert len(configs_copies) == 1
    configs_copy = configs_copies[0]
    owner = re.search(r"--chown=([^\s]+)", configs_copy)
    assert owner is not None
    assert _docker_identity(owner.group(1)) == (0, 0)
    with pytest.raises(AssertionError):
        _docker_identity("00:0")
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
