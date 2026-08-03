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
"""Closeout ratchets for Wave 3 ownership and compatibility seams."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]

PIPELINE_CONFIG_LOADER_PATH = (
    ROOT / "src" / "bioetl" / "infrastructure" / "config" / "pipeline_config_loader.py"
)
REGISTRATION_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "registration.py"
)
LOADER_PATH = ROOT / "src" / "bioetl" / "composition" / "providers" / "loader.py"
DEFAULT_REGISTRY_PATH = (
    ROOT / "src" / "bioetl" / "composition" / "providers" / "_default_registry.py"
)

PIPELINE_CONFIG_LOADER_MAX_LINES = 150
REGISTRATION_MAX_LINES = 110
LOADER_MAX_LINES = 90
DEFAULT_REGISTRY_MAX_LINES = 120


def _imports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.module
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom) and node.module is not None
    }


def _top_level_defs(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    return {
        node.name
        for node in tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
    }


@pytest.mark.architecture
def test_pipeline_config_loader_stays_retained_convenience_seam() -> None:
    """PipelineConfigLoader should stay documented as a retained convenience facade."""
    source = PIPELINE_CONFIG_LOADER_PATH.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= PIPELINE_CONFIG_LOADER_MAX_LINES, (
        "pipeline_config_loader.py regrew to "
        f"{line_count} lines (max {PIPELINE_CONFIG_LOADER_MAX_LINES}). "
        "Keep the retained convenience seam thin and leave canonical ownership "
        "with the narrower config APIs."
    )
    for snippet in (
        "Wave 3 ownership classification: retain.",
        "pipeline_config_api.py",
        "domain_config_resolver.py",
        "not the canonical owner of pipeline config resolution",
    ):
        assert snippet in source, (
            "pipeline_config_loader.py must keep retained-seam ownership "
            f"guidance explicit: missing {snippet}"
        )

    imported_modules = _imports(PIPELINE_CONFIG_LOADER_PATH)
    for module_name in (
        "bioetl.infrastructure.config.pipeline_config_api",
        "bioetl.infrastructure.config.pipeline_dq_resolution",
    ):
        assert module_name in imported_modules, (
            "pipeline_config_loader.py must keep delegating to canonical helper "
            f"owners: missing {module_name}"
        )


@pytest.mark.architecture
def test_registration_module_stays_thin_after_wave3_simplify_now_closeout() -> None:
    """registration.py should remain a thin explicit entrypoint after Wave 3."""
    source = REGISTRATION_PATH.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= REGISTRATION_MAX_LINES, (
        f"registration.py regrew to {line_count} lines (max {REGISTRATION_MAX_LINES}). "
        "Keep provider assembly ownership in helper modules, not the public "
        "registration entrypoint."
    )
    for snippet in (
        "Wave 3 ownership classification: simplify-now closeout complete.",
        "_registration_contracts.py",
        "_config_helpers.py",
        "thin explicit bootstrap seam",
    ):
        assert snippet in source, (
            "registration.py must keep the Wave 3 simplify-now classification "
            f"explicit: missing {snippet}"
        )

    assert _top_level_defs(REGISTRATION_PATH) == {
        "register_all_providers",
        "_build_provider_configs",
        "_merge_provider_config_families",
        "_iter_provider_config_family_builders",
    }, (
        "registration.py should stay a thin ownership seam with only the "
        "expected assembly entrypoints."
    )


@pytest.mark.architecture
def test_loader_module_stays_retained_bootstrap_seam() -> None:
    """loader.py should remain a thin retained bootstrap seam."""
    source = LOADER_PATH.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= LOADER_MAX_LINES, (
        f"loader.py regrew to {line_count} lines (max {LOADER_MAX_LINES}). "
        "Keep provider bootstrap ownership in _loading.py and registry "
        "resolution in _registry_resolution.py."
    )
    for snippet in (
        "Wave 3 ownership classification: retain.",
        "_loading.py",
        "_registry_resolution.py",
    ):
        assert snippet in source, (
            "loader.py must keep retained bootstrap ownership guidance explicit: "
            f"missing {snippet}"
        )

    imported_modules = _imports(LOADER_PATH)
    assert {
        "bioetl.composition.providers._loading",
        "bioetl.composition.providers._registry_resolution",
    } <= imported_modules, (
        "loader.py must keep routing bootstrap work through the private loading "
        "and registry-resolution helpers."
    )


@pytest.mark.architecture
def test_default_registry_helper_stays_private_singleton_owner() -> None:
    """_default_registry.py should remain the private retained singleton owner."""
    source = DEFAULT_REGISTRY_PATH.read_text(encoding="utf-8")
    line_count = len(source.splitlines())
    assert line_count <= DEFAULT_REGISTRY_MAX_LINES, (
        "_default_registry.py regrew to "
        f"{line_count} lines (max {DEFAULT_REGISTRY_MAX_LINES}). "
        "Keep the retained default-registry seam small and private."
    )
    for snippet in (
        "Retained class-level compatibility helpers for the default provider registry.",
        "private owner of the lazy default registry singleton",
        "_registry_resolution.py",
        "explicit injection",
    ):
        assert snippet in source, (
            "_default_registry.py must keep retained ownership guidance explicit: "
            f"missing {snippet}"
        )
