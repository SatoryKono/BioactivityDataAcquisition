"""Architecture tests for the naming ambiguity classifier."""

from __future__ import annotations

import pytest

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

pytestmark = [pytest.mark.architecture, pytest.mark.slow]

REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_naming_audit_module() -> ModuleType:
    script = REPO_ROOT / "scripts" / "engineering" / "qa" / "naming_audit.py"
    spec = importlib.util.spec_from_file_location(
        "naming_audit_ambiguity_runtime",
        str(script),
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["naming_audit_ambiguity_runtime"] = module
    spec.loader.exec_module(module)
    return module


def _write_module(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _write_pipeline_config(path: Path, pipeline_name: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"pipeline:\n  pipeline_name: {pipeline_name}\n", encoding="utf-8")


def _write_minimal_ambiguity_fixture(tmp_path: Path) -> tuple[Path, Path]:
    src_path = tmp_path / "src" / "bioetl"
    configs_path = tmp_path / "configs"

    _write_module(
        src_path / "domain" / "entities" / "canonical.py",
        """
class PubchemMolecule:
    pass


class UniprotTarget:
    pass


class ChemblPublication:
    pass
""",
    )
    _write_module(
        src_path / "application" / "pipelines" / "pubchem" / "compound.py",
        """
class PubChemCompoundPipeline:
    pass


class PubChemCompoundTransformer:
    pass
""",
    )
    _write_module(
        src_path / "application" / "pipelines" / "uniprot" / "protein.py",
        """
class UniProtProteinPipeline:
    pass


class UniProtProteinTransformer:
    pass
""",
    )
    _write_module(
        src_path / "domain" / "contracts" / "gold" / "stable_public.py",
        """
class PubChemCompoundGoldSchema:
    pass


class UniProtProteinGoldSchema:
    pass
""",
    )

    _write_pipeline_config(
        configs_path / "entities" / "pubchem" / "compound.yaml",
        "pubchem_compound",
    )
    _write_pipeline_config(
        configs_path / "entities" / "uniprot" / "protein.yaml",
        "uniprot_protein",
    )
    _write_pipeline_config(
        configs_path / "entities" / "chembl" / "publication.yaml",
        "chembl_publication",
    )
    _write_pipeline_config(
        configs_path / "entities" / "chembl" / "publication_similarity.yaml",
        "chembl_publication_similarity",
    )
    _write_pipeline_config(
        configs_path / "entities" / "chembl" / "publication_term.yaml",
        "chembl_publication_term",
    )
    return src_path, configs_path


def test_build_ambiguity_groups_reports_expected_ok_families(
    tmp_path: Path,
) -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()
    src_path, configs_path = _write_minimal_ambiguity_fixture(tmp_path)

    groups = mod.build_ambiguity_groups(
        src_path,
        configs_path,
        registry,
    )
    by_family = {group.normalized_stem: group for group in groups}

    assert (
        by_family["pubchem:molecule"].classification == mod.AmbiguityClassification.OK
    )
    assert by_family["uniprot:target"].classification == mod.AmbiguityClassification.OK
    assert (
        by_family["chembl:publication"].classification == mod.AmbiguityClassification.OK
    )


def test_classify_ambiguity_group_marks_unregistered_overlap_as_duplicate() -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    symbols = (
        mod.SymbolSurface(
            name="AlphaCanonical",
            kind="domain_entity",
            location="src/example/domain.py",
            semantic_family="candidate:alpha",
            source="code",
        ),
        mod.SymbolSurface(
            name="AlphaLegacyAlias",
            kind="pipeline_class",
            location="src/example/pipeline.py",
            semantic_family="candidate:alpha",
            source="code",
        ),
    )

    group = mod.classify_ambiguity_group("candidate:alpha", symbols, registry)

    assert group.classification == mod.AmbiguityClassification.DUPLICATE
    assert "registry-backed distinction" in group.rationale


def test_classify_ambiguity_group_marks_forbidden_alias_export_as_conflict() -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    symbols = (
        mod.SymbolSurface(
            name="ChemblPublication",
            kind="domain_export",
            location="src/bioetl/domain/entities/__init__.py",
            semantic_family="chembl:publication",
            source="code",
        ),
        mod.SymbolSurface(
            name="Document",
            kind="forbidden_alias",
            location="src/bioetl/domain/entities/__init__.py",
            semantic_family="chembl:publication",
            source="code",
        ),
    )

    group = mod.classify_ambiguity_group("chembl:publication", symbols, registry)

    assert group.classification == mod.AmbiguityClassification.CONFLICT
    assert "Forbidden ADR-024 alias" in group.rationale


def test_build_ambiguity_groups_is_deterministic(tmp_path: Path) -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()
    src_path, configs_path = _write_minimal_ambiguity_fixture(tmp_path)
    module_trees = mod._build_python_module_tree_cache(src_path)

    first = mod.build_ambiguity_groups(
        src_path,
        configs_path,
        registry,
        module_trees=module_trees,
    )
    second = mod.build_ambiguity_groups(
        src_path,
        configs_path,
        registry,
        module_trees=module_trees,
    )

    first_snapshot = [
        (
            group.normalized_stem,
            group.classification.value,
            [(symbol.name, symbol.kind, symbol.location) for symbol in group.symbols],
        )
        for group in first
    ]
    second_snapshot = [
        (
            group.normalized_stem,
            group.classification.value,
            [(symbol.name, symbol.kind, symbol.location) for symbol in group.symbols],
        )
        for group in second
    ]

    assert first_snapshot == second_snapshot
