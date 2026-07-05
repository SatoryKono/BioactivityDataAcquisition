"""Architecture guardrails for Pandera/Pandas schema boundary policy."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest


pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
DOMAIN_ROOT = ROOT / "src" / "bioetl" / "domain"
DOMAIN_README_PATH = DOMAIN_ROOT / "README.md"
ADR_PATH = (
    ROOT
    / "docs"
    / "02-architecture"
    / "decisions"
    / "ADR-048-domain-schema-boundary-and-runtime-pandera-compat.md"
)

_ALLOWED_DOMAIN_SCHEMA_PREFIXES = (
    "src/bioetl/domain/schemas/",
    "src/bioetl/domain/contracts/",
)
_DATAFRAME_SCHEMA_MODULES = {"pandas", "pandera"}
_DOMAIN_SCHEMA_HOTSPOT_PATHS = (
    "src/bioetl/domain/schemas/generated/registry.py",
    "src/bioetl/domain/schemas/chembl/activity.py",
    "src/bioetl/domain/schemas/_chembl_enum_catalog.py",
)
_DOMAIN_SCHEMA_HOTSPOT_OWNERSHIP_MARKERS = {
    "src/bioetl/domain/schemas/generated/registry.py": (
        "domain schema generated registry owner",
        "Split provider/entity registry shards",
        "No runtime bootstrap, I/O, adapter wiring, or service construction",
    ),
    "src/bioetl/domain/schemas/chembl/activity.py": (
        "ChEMBL activity schema contract owner",
        "Split field-group/schema helper modules",
        "No transforms, normalization workflow, runtime compatibility patching, I/O, or adapter wiring",
    ),
    "src/bioetl/domain/schemas/_chembl_enum_catalog.py": (
        "ChEMBL enum catalog owner",
        "Split provider/entity vocabulary modules",
        "No config loading, file/network access, runtime service ownership, or application orchestration",
    ),
}
_FORBIDDEN_SCHEMA_CONTRACT_RUNTIME_PREFIXES = (
    "bioetl.application",
    "bioetl.composition",
    "bioetl.infrastructure",
    "bioetl.interfaces",
)
_FORBIDDEN_SCHEMA_CONTRACT_IO_CALLS = {
    "open",
    "Path.open",
    "Path.read_bytes",
    "Path.read_text",
    "Path.write_bytes",
    "Path.write_text",
    "requests.delete",
    "requests.get",
    "requests.patch",
    "requests.post",
    "requests.put",
    "urlopen",
}


def _imports_dataframe_schema_module(path: Path) -> bool:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            if any(
                alias.name.split(".", 1)[0] in _DATAFRAME_SCHEMA_MODULES
                for alias in node.names
            ):
                return True
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            if module.split(".", 1)[0] in _DATAFRAME_SCHEMA_MODULES:
                return True
    return False


def _imported_modules(tree: ast.AST) -> set[str]:
    modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            modules.add(node.module)
    return modules


def _call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent_name = _call_name(node.value)
        if parent_name is None:
            return node.attr
        return f"{parent_name}.{node.attr}"
    return None


def _called_names(tree: ast.AST) -> set[str]:
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _call_name(node.func)
            if name is not None:
                names.add(name)
    return names


def test_domain_dataframe_schema_imports_are_confined_to_contract_packages() -> None:
    """Domain may model dataframe contracts but must not leak them into behavior."""
    offenders: list[str] = []
    for path in DOMAIN_ROOT.rglob("*.py"):
        if not _imports_dataframe_schema_module(path):
            continue
        rel_path = path.relative_to(ROOT).as_posix()
        if not rel_path.startswith(_ALLOWED_DOMAIN_SCHEMA_PREFIXES):
            offenders.append(rel_path)

    assert not offenders, (
        "Pandera/Pandas imports in domain are sanctioned only for schema-contract "
        "packages, not behavior/services/value objects:\n" + "\n".join(offenders)
    )


def test_domain_schema_contract_hotspots_remain_pure_contract_surfaces() -> None:
    """ADR-048 schema hotspots must not absorb runtime or I/O responsibilities."""
    import_offenders: list[str] = []
    io_offenders: list[str] = []

    for rel_path in _DOMAIN_SCHEMA_HOTSPOT_PATHS:
        path = ROOT / rel_path
        tree = ast.parse(path.read_text(encoding="utf-8"))

        for module in sorted(_imported_modules(tree)):
            if module.startswith(_FORBIDDEN_SCHEMA_CONTRACT_RUNTIME_PREFIXES):
                import_offenders.append(f"{rel_path} imports {module}")

        for name in sorted(_called_names(tree)):
            if name in _FORBIDDEN_SCHEMA_CONTRACT_IO_CALLS:
                io_offenders.append(f"{rel_path} calls {name}")

    assert not import_offenders, "\n".join(import_offenders)
    assert not io_offenders, "\n".join(io_offenders)


def test_domain_schema_contract_hotspot_ownership_is_documented() -> None:
    """ADR-048 hotspot ownership must stay explicit before split-on-touch work."""
    text = DOMAIN_README_PATH.read_text(encoding="utf-8")

    for rel_path, markers in _DOMAIN_SCHEMA_HOTSPOT_OWNERSHIP_MARKERS.items():
        assert rel_path in text
        for marker in markers:
            assert marker in text


def test_runtime_pandera_validation_is_not_package_import_side_effect() -> (
    None
):
    """Pandera runtime validation must remain an explicit bootstrap call."""
    top_level_init = (ROOT / "src" / "bioetl" / "__init__.py").read_text(
        encoding="utf-8"
    )
    runtime_init = (
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "bootstrap"
        / "runtime"
        / "__init__.py"
    ).read_text(encoding="utf-8")
    runtime_patch = (
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "bootstrap"
        / "runtime"
        / "pipeline.py"
    ).read_text(encoding="utf-8")
    retired_runtime_compat = (
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "bootstrap"
        / "runtime"
        / "compatibility.py"
    )
    retired_pandera_runtime = (
        ROOT
        / "src"
        / "bioetl"
        / "composition"
        / "bootstrap"
        / "runtime"
        / "pandera_runtime.py"
    )

    assert "validate_supported_pandera_runtime()" not in top_level_init
    assert "validate_supported_pandera_runtime()" not in runtime_init
    assert "apply_runtime_compatibility_patches" in runtime_init
    assert "validate_supported_pandera_runtime" not in runtime_patch
    assert "pandera_compat" not in runtime_patch
    assert not retired_runtime_compat.exists()
    assert not retired_pandera_runtime.exists()
    assert not (
        ROOT / "src" / "bioetl" / "infrastructure" / "compat" / "pandera_compat.py"
    ).exists()


def test_adr_048_records_schema_boundary_and_runtime_patch_decisions() -> None:
    """The Pandera boundary must stay backed by an accepted ADR."""
    text = ADR_PATH.read_text(encoding="utf-8")
    normalized_text = " ".join(text.split())

    for expected in (
        "Status: Accepted",
        "schema-contract representation",
        "schema-contract hotspot",
        "split on touch",
        "not adapter implementations",
        "No import-time runtime validation",
        "apply_runtime_compatibility_patches",
        "retained as a no-op",
        "Pandera-specific compatibility shim has been removed",
    ):
        assert expected in normalized_text
