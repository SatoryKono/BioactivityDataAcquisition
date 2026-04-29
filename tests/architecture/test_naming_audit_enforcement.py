"""Architecture tests for naming audit enforcement behavior."""

from __future__ import annotations

import importlib.util
from pathlib import Path
import sys
from types import ModuleType


REPO_ROOT = Path(__file__).resolve().parents[2]


def _load_naming_audit_module() -> ModuleType:
    script = REPO_ROOT / "scripts" / "engineering" / "qa" / "naming_audit.py"
    spec = importlib.util.spec_from_file_location(
        "naming_audit_enforcement_runtime",
        str(script),
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["naming_audit_enforcement_runtime"] = module
    spec.loader.exec_module(module)
    return module


def _clone_registry(registry: object, **overrides: object) -> object:
    payload = {
        field: getattr(registry, field) for field in registry.__dataclass_fields__
    }
    payload.update(overrides)
    return registry.__class__(**payload)


def test_naming_audit_reports_missing_suffix_for_public_class(tmp_path: Path) -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    src_path = tmp_path / "src"
    application_path = src_path / "application"
    application_path.mkdir(parents=True)
    (application_path / "bad_module.py").write_text(
        "class MissingRole:\n    pass\n",
        encoding="utf-8",
    )

    results = mod.run_audit(src_path, tmp_path / "docs", tmp_path / "configs", registry)

    assert any(
        violation.current_name == "MissingRole"
        and violation.issue is mod.ViolationType.MISSING_SUFFIX
        for violation in results["classes"]
    )


def test_naming_audit_reports_unregistered_exported_alias(tmp_path: Path) -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    src_path = tmp_path / "src"
    src_path.mkdir()
    (src_path / "alias_module.py").write_text(
        '__all__ = ["CanonicalResult", "Canonical"]\n\n'
        "class CanonicalResult:\n"
        "    pass\n\n"
        "Canonical = CanonicalResult\n",
        encoding="utf-8",
    )

    results = mod.run_audit(src_path, tmp_path / "docs", tmp_path / "configs", registry)

    assert any(
        violation.current_name == "Canonical"
        and violation.issue is mod.ViolationType.UNREGISTERED_ALIAS
        for violation in results["aliases"]
    )


def test_naming_audit_accepts_registered_exported_alias(tmp_path: Path) -> None:
    mod = _load_naming_audit_module()
    registry = mod.load_naming_registry()

    src_path = tmp_path / "src"
    src_path.mkdir()
    alias_module = src_path / "compat_alias.py"
    alias_module.write_text(
        '__all__ = ["CanonicalResult", "Canonical"]\n\n'
        "class CanonicalResult:\n"
        "    pass\n\n"
        "Canonical = CanonicalResult\n",
        encoding="utf-8",
    )

    alias_entry = mod.PublicSymbolAlias(
        alias_name="Canonical",
        canonical_name="CanonicalResult",
        defining_surface=str(alias_module),
        export_surfaces=(str(alias_module),),
        reason="test shim",
        remove_after="v-test",
    )
    augmented_registry = _clone_registry(
        registry,
        public_symbol_aliases=(*registry.public_symbol_aliases, alias_entry),
    )

    results = mod.run_audit(
        src_path,
        tmp_path / "docs",
        tmp_path / "configs",
        augmented_registry,
    )

    assert not results["aliases"]
