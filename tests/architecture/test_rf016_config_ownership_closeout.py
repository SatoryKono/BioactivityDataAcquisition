"""Closeout ratchets for RF-016 config ownership seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

DOMAIN_CONFIG_RESOLVER_PATH = (
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "domain_config_resolver.py"
)
CONFIG_LOADER_PORT_PATH = (
    ROOT / "src" / "bioetl" / "domain" / "ports" / "config" / "config_loader_port.py"
)

DOMAIN_CONFIG_RESOLVER_MAX_LINES = 120
CONFIG_LOADER_PORT_MAX_LINES = 55

REQUIRED_DOMAIN_CONFIG_RESOLVER_IMPORTS = {
    "bioetl.infrastructure.config.converters",
    "bioetl.infrastructure.config.dq_config_loader",
    "bioetl.infrastructure.config.pipeline_config_api",
    "bioetl.infrastructure.config.pipeline_dq_resolution",
}

FORBIDDEN_DOMAIN_CONFIG_RESOLVER_PREFIXES = (
    "bioetl.composition",
    "bioetl.interfaces",
    "bioetl.infrastructure.config.filter_config_loader",
)

FORBIDDEN_CONFIG_LOADER_PORT_PREFIXES = (
    "bioetl.application",
    "bioetl.composition",
    "bioetl.infrastructure",
    "bioetl.interfaces",
)


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


@pytest.mark.architecture
def test_domain_config_resolver_stays_bounded_and_canonical() -> None:
    """DomainConfigResolver should remain the canonical config-resolution seam."""
    source = DOMAIN_CONFIG_RESOLVER_PATH.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= DOMAIN_CONFIG_RESOLVER_MAX_LINES, (
        "domain_config_resolver.py regrew to "
        f"{line_count} lines (max {DOMAIN_CONFIG_RESOLVER_MAX_LINES}). "
        "Keep canonical config-resolution ownership narrow."
    )

    imported_modules = _imports(DOMAIN_CONFIG_RESOLVER_PATH)
    missing_modules = REQUIRED_DOMAIN_CONFIG_RESOLVER_IMPORTS - imported_modules
    assert not missing_modules, (
        "domain_config_resolver.py no longer imports required canonical helper "
        "owners:\n" + "\n".join(sorted(missing_modules))
    )

    violations = {
        module_name
        for module_name in imported_modules
        if module_name.startswith(FORBIDDEN_DOMAIN_CONFIG_RESOLVER_PREFIXES)
    }
    assert not violations, (
        "domain_config_resolver.py reintroduced forbidden ownership imports:\n"
        + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_domain_config_resolver_exposes_only_expected_public_surface() -> None:
    """DomainConfigResolver module should stay focused on config-resolution seams."""
    tree = ast.parse(DOMAIN_CONFIG_RESOLVER_PATH.read_text(encoding="utf-8"))
    top_level_defs = {
        node.name
        for node in tree.body
        if isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert top_level_defs == {
        "DomainConfigMapper",
        "PipelineConfigDQResolverProvider",
        "DomainConfigResolver",
        "resolve_domain_pipeline_config",
        "load_domain_pipeline_config",
    }, (
        "domain_config_resolver.py should stay focused on the canonical "
        "config-resolution contracts and entrypoints. Found:\n"
        + "\n".join(sorted(top_level_defs))
    )


@pytest.mark.architecture
def test_config_loader_port_stays_small_and_domain_only() -> None:
    """config_loader_port should remain a tiny domain-only protocol surface."""
    source = CONFIG_LOADER_PORT_PATH.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= CONFIG_LOADER_PORT_MAX_LINES, (
        "config_loader_port.py regrew to "
        f"{line_count} lines (max {CONFIG_LOADER_PORT_MAX_LINES}). "
        "Keep the domain config port surface narrow."
    )

    imported_modules = _imports(CONFIG_LOADER_PORT_PATH)
    violations = {
        module_name
        for module_name in imported_modules
        if module_name.startswith(FORBIDDEN_CONFIG_LOADER_PORT_PREFIXES)
    }
    assert not violations, (
        "config_loader_port.py must stay domain-only and avoid higher/lower "
        "layer imports:\n" + "\n".join(sorted(violations))
    )


@pytest.mark.architecture
def test_config_loader_port_exports_only_protocols() -> None:
    """config_loader_port should expose only the three protocol seams."""
    tree = ast.parse(CONFIG_LOADER_PORT_PATH.read_text(encoding="utf-8"))
    protocol_defs = [node.name for node in tree.body if isinstance(node, ast.ClassDef)]
    assert protocol_defs == [
        "SettingsLoaderPort",
        "PipelineConfigLoaderPort",
        "DomainConfigMapperPort",
    ], (
        "config_loader_port.py should expose only the expected protocol "
        f"contracts. Found: {protocol_defs}"
    )
