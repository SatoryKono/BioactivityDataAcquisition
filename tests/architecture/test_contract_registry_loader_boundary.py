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
"""Architecture guardrails for canonical contract-registry access."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC_ROOT = ROOT / "src"
REGISTRY_PATH_LITERAL = "configs/base/contract_registry.yaml"
ALLOWED_LITERAL_OWNERS = {
    "src/bioetl/infrastructure/config/contract_registry_loader.py",
}


@pytest.mark.architecture
def test_contract_registry_path_literal_is_confined_to_reviewed_surfaces() -> None:
    """Avoid silent growth of ad hoc contract-registry readers in src."""
    offenders: list[str] = []
    for path in sorted(SRC_ROOT.rglob("*.py")):
        rel = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        if REGISTRY_PATH_LITERAL in text and rel not in ALLOWED_LITERAL_OWNERS:
            offenders.append(rel)

    assert not offenders, (
        "Unreviewed src surfaces reference contract_registry.yaml directly:\n"
        + "\n".join(offenders)
    )


@pytest.mark.architecture
def test_src_registry_readers_use_canonical_loader_family() -> None:
    """Direct YAML parsing for the contract registry must stay centralized."""
    offenders: list[str] = []
    for rel in sorted(ALLOWED_LITERAL_OWNERS):
        if rel == "src/bioetl/infrastructure/config/contract_registry_loader.py":
            continue
        path = ROOT / rel
        tree = ast.parse(path.read_text(encoding="utf-8"))
        imports_yaml = False
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                imports_yaml |= any(alias.name == "yaml" for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                imports_yaml |= node.module == "yaml"
        text = path.read_text(encoding="utf-8")
        if imports_yaml and REGISTRY_PATH_LITERAL in text:
            offenders.append(rel)

    assert not offenders, (
        "Contract-registry YAML parsing must stay in the canonical loader:\n"
        + "\n".join(offenders)
    )
