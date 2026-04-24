"""Architecture tests for the naming ambiguity classifier."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType

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


def test_build_ambiguity_groups_reports_expected_ok_families() -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    groups = mod.build_ambiguity_groups(
        REPO_ROOT / "src" / "bioetl",
        REPO_ROOT / "configs",
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


def test_build_ambiguity_groups_is_deterministic() -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    first = mod.build_ambiguity_groups(
        REPO_ROOT / "src" / "bioetl",
        REPO_ROOT / "configs",
        registry,
    )
    second = mod.build_ambiguity_groups(
        REPO_ROOT / "src" / "bioetl",
        REPO_ROOT / "configs",
        registry,
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
