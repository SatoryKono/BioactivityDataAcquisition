"""Architecture checks for naming exception registry and policy sync."""

from __future__ import annotations

import ast
import importlib.util
from pathlib import Path
import sys
from types import ModuleType

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
REGISTRY_PATH = REPO_ROOT / "configs" / "naming_exceptions.yaml"
NAMING_POLICY_PATH = (
    REPO_ROOT / "docs" / "00-project" / "governance" / "02-naming-policy.md"
)
GLOSSARY_PATH = REPO_ROOT / "docs" / "00-project" / "glossary.md"
DOMAIN_ENTITIES_INIT = (
    REPO_ROOT / "src" / "bioetl" / "domain" / "entities" / "__init__.py"
)


def _load_registry_payload() -> dict[str, object]:
    payload = yaml.safe_load(REGISTRY_PATH.read_text(encoding="utf-8")) or {}
    assert isinstance(payload, dict), "naming_exceptions.yaml must be a YAML mapping"
    return payload


def _load_naming_audit_module() -> ModuleType:
    script = REPO_ROOT / "scripts" / "engineering" / "qa" / "naming_audit.py"
    spec = importlib.util.spec_from_file_location("naming_audit_runtime", str(script))
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["naming_audit_runtime"] = module
    spec.loader.exec_module(module)
    return module


def _collect_class_names(src_root: Path) -> set[str]:
    names: set[str] = set()
    for py_file in src_root.rglob("*.py"):
        if "__pycache__" in py_file.parts:
            continue
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                names.add(node.name)
    return names


def _exported_names_from_all_assign(node: ast.Assign) -> set[str]:
    if not isinstance(node.value, (ast.List, ast.Tuple)):
        return set()
    return {
        elt.value
        for elt in node.value.elts
        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
    }


def _is_all_assignment(node: ast.AST) -> bool:
    if not isinstance(node, ast.Assign):
        return False
    return any(
        isinstance(target, ast.Name) and target.id == "__all__"
        for target in node.targets
    )


def _extract_all_exports(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    for node in tree.body:
        if _is_all_assignment(node):
            return _exported_names_from_all_assign(node)
    return set()


def test_stable_pipeline_id_exceptions_match_active_entity_configs() -> None:
    payload = _load_registry_payload()
    stable_public_surface = payload.get("stable_public_surface")
    assert isinstance(stable_public_surface, dict), "stable_public_surface must exist"

    pipeline_ids = stable_public_surface.get("pipeline_ids")
    assert isinstance(pipeline_ids, list) and pipeline_ids, (
        "pipeline_ids must be non-empty"
    )

    by_name = {
        entry["name"]: entry
        for entry in pipeline_ids
        if isinstance(entry, dict) and "name" in entry
    }

    for pipeline_name in ("pubchem_compound", "uniprot_protein"):
        assert pipeline_name in by_name, (
            f"{pipeline_name} missing from stable pipeline IDs"
        )
        entry = by_name[pipeline_name]
        location = entry.get("location")
        assert isinstance(location, str) and location, (
            f"{pipeline_name} must declare location"
        )
        config_path = REPO_ROOT / location
        assert config_path.exists(), f"{pipeline_name} location missing: {config_path}"
        raw = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
        assert raw["pipeline"]["pipeline_name"] == pipeline_name


def test_stable_public_surface_symbols_exist_in_code() -> None:
    payload = _load_registry_payload()
    stable_public_surface = payload["stable_public_surface"]
    class_names = _collect_class_names(REPO_ROOT / "src" / "bioetl")

    for section_name in ("pipeline_classes", "transformers", "gold_schemas"):
        section = stable_public_surface.get(section_name)
        assert isinstance(section, list) and section, (
            f"{section_name} must be non-empty"
        )
        for entry in section:
            assert isinstance(entry, dict), f"{section_name} entries must be mappings"
            name = entry.get("name")
            location = entry.get("location")
            reason = entry.get("reason")
            assert isinstance(name, str) and name, (
                f"{section_name} entry must have name"
            )
            assert isinstance(location, str) and location, (
                f"{name} must declare location"
            )
            assert isinstance(reason, str) and reason, f"{name} must declare reason"
            assert (REPO_ROOT / location).exists(), (
                f"{name} location missing: {location}"
            )
            assert name in class_names, f"{name} not found in codebase"


def test_forbidden_domain_aliases_are_not_exported_from_domain_entities() -> None:
    payload = _load_registry_payload()
    forbidden_aliases = payload.get("forbidden_domain_entity_aliases")
    assert isinstance(forbidden_aliases, list) and forbidden_aliases, (
        "forbidden_domain_entity_aliases must be declared"
    )

    exports = _extract_all_exports(DOMAIN_ENTITIES_INIT)
    assert exports, "Could not parse __all__ from domain entities facade"

    for entry in forbidden_aliases:
        assert isinstance(entry, dict), "forbidden alias entries must be mappings"
        legacy_name = entry.get("legacy_name")
        canonical_name = entry.get("canonical_name")
        export_surface = entry.get("export_surface")
        assert isinstance(legacy_name, str) and legacy_name
        assert isinstance(canonical_name, str) and canonical_name
        assert isinstance(export_surface, str) and export_surface
        assert canonical_name in exports, (
            f"{canonical_name} should be exported canonically"
        )
        assert legacy_name not in exports, f"{legacy_name} must not be re-exported"


def test_naming_audit_registry_loader_matches_policy_registry() -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    assert "README.md" in registry.documentation_exceptions
    assert "SKILL.md" in registry.documentation_exceptions
    assert "PubchemMolecule" in registry.class_suffix_exceptions
    assert "UniprotTarget" in registry.class_suffix_exceptions
    assert "Compound" not in registry.class_suffix_exceptions
    assert "Protein" not in registry.class_suffix_exceptions

    stable_ids = {entry.name for entry in registry.stable_pipeline_ids}
    assert {"pubchem_compound", "uniprot_protein"} <= stable_ids


def test_naming_audit_uses_registry_for_doc_exceptions(tmp_path: Path) -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    docs_path = tmp_path / "docs"
    docs_path.mkdir()
    (docs_path / "SKILL.md").write_text("# ok\n", encoding="utf-8")
    (docs_path / "bad_name_doc.md").write_text("# bad\n", encoding="utf-8")

    results = mod.run_audit(tmp_path / "src", docs_path, tmp_path / "configs", registry)
    doc_violations = results["docs"]

    assert all(violation.current_name != "SKILL.md" for violation in doc_violations)
    assert any(
        violation.current_name == "bad_name_doc.md" for violation in doc_violations
    )


def test_naming_policy_and_glossary_distinguish_canonical_and_stable_public_names() -> (
    None
):
    naming_policy = NAMING_POLICY_PATH.read_text(encoding="utf-8")
    glossary = GLOSSARY_PATH.read_text(encoding="utf-8")

    for text in (naming_policy, glossary):
        assert "{provider}_{entity}" in text
        assert "{provider}-{entity}" not in text

    assert "stable external" in naming_policy
    assert "canonical domain" in naming_policy
    assert "pubchem_compound" in naming_policy and "PubchemMolecule" in naming_policy
    assert "uniprot_protein" in naming_policy and "UniprotTarget" in naming_policy

    assert "stable external identifiers" in glossary
    assert "PubChemCompoundTransformer" in glossary
    assert "PubchemMolecule" in glossary
    assert "UniprotTarget" in glossary
