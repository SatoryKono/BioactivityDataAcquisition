"""Contracts for catalog-driven MCP wrapper generation and dispatch."""

from __future__ import annotations

import json
import stat
from pathlib import Path

import pytest

from scripts.ai.mcp import wrappers
from scripts.engineering.common.platform import PlatformInfo, PlatformKind


pytestmark = [pytest.mark.unit, pytest.mark.repo_backed]


def test_catalog_has_unique_safe_wrapper_bindings() -> None:
    specs = wrappers.load_wrapper_specs()
    assert len(specs) == 19
    assert specs["context7"].wrapper_stem == "mcp_context7_wrapper"
    assert wrappers.validate_wrapper_catalog() == []


def test_wrapper_command_selects_platform_pair() -> None:
    windows = PlatformInfo(PlatformKind.WINDOWS, "nt", "win32", "fixture")
    linux = PlatformInfo(PlatformKind.LINUX, "posix", "linux", "fixture")

    windows_command = wrappers.wrapper_command("context7", host=windows)
    linux_command = wrappers.wrapper_command("context7", host=linux)

    assert windows_command[-1].endswith("mcp_context7_wrapper.ps1")
    assert windows_command[:2] == ["powershell", "-NoLogo"]
    assert linux_command[0] == "bash"
    assert linux_command[1].endswith("mcp_context7_wrapper.sh")


def test_ast_grep_windows_wrapper_preserves_runtime_contract() -> None:
    windows = PlatformInfo(PlatformKind.WINDOWS, "nt", "win32", "fixture")
    spec = wrappers.load_wrapper_specs()["ast-grep"]
    wrapper = wrappers.wrapper_path(spec, host=windows)

    assert wrapper == wrappers.MCP_DIR / "mcp_ast_grep_wrapper.ps1"
    body = wrapper.read_text(encoding="utf-8")
    assert 'Exit-McpValidateOnly -ServerName "ast-grep"' in body
    assert 'npx -y "@notprolands/ast-grep-mcp" --stdio @args' in body
    assert 'npx -y "@chousyn/ast-grep-mcp" --stdio @args' in body
    assert wrappers.wrapper_command("ast-grep", host=windows)[-1] == str(wrapper)


def test_unknown_server_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown MCP server"):
        wrappers.wrapper_command("../../escape")


def test_generate_wrapper_shims_is_deterministic(tmp_path: Path) -> None:
    first = wrappers.generate_wrapper_shims(tmp_path)
    first_payloads = {path.name: path.read_bytes() for path in first}
    second = wrappers.generate_wrapper_shims(tmp_path)
    second_payloads = {path.name: path.read_bytes() for path in second}

    assert first_payloads == second_payloads
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["catalog"] == "scripts/ops/runtime/mcp/shared-servers.json"
    assert len(manifest["servers"]) == 19
    assert len(manifest["generated_files"]) == 38
    assert (tmp_path / "context7.sh").stat().st_mode & stat.S_IXUSR
    assert "--no-upload" not in (tmp_path / "context7.sh").read_text(encoding="utf-8")


def test_unsafe_catalog_wrapper_is_rejected(tmp_path: Path) -> None:
    catalog = tmp_path / "shared-servers.json"
    catalog.write_text(
        json.dumps({"servers": {"safe": {"wrapper": "../escape", "wrapper_order": 1}}}),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="unsafe wrapper stem"):
        wrappers.load_wrapper_specs(catalog)
