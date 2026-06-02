"""Unit tests for exemptions_registry module."""

from __future__ import annotations

from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from bioetl.infrastructure.quality.exemptions_registry import (
    EXEMPTION_REGISTRIES_ALLOW_EMPTY,
    REQUIRED_EXEMPTION_REGISTRIES,
    get_registry_values,
    load_exemptions_registry,
    resolve_registry_value,
    validate_exemption_key_normalization,
    validate_exemption_target_references,
    validate_exemptions_registry,
)

pytestmark = pytest.mark.unit


def _write_registry(tmp_path: Path, content: dict[str, object]) -> Path:
    """Write registry YAML to a temp file."""
    registry_file = tmp_path / "registry.yaml"
    registry_file.write_text(yaml.dump(content), encoding="utf-8")
    return registry_file


class TestLoadExemptionsRegistry:
    """Tests for load_exemptions_registry."""

    def test_exemptions_registry__loads_valid_yaml__07d01eb7(
        self, tmp_path: Path
    ) -> None:
        """Valid YAML mapping should be loaded as dict."""
        path = _write_registry(tmp_path, {"registries": {}})
        result = load_exemptions_registry(path)
        assert isinstance(result, dict)
        assert "registries" in result

    def test_exemptions_registry__not_found_raises__7ca99c65(self) -> None:
        """Non-existent file should raise FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_exemptions_registry("/nonexistent/registry.yaml")

    def test_exemptions_registry__non_mapping_raises__b7cd6df7(
        self, tmp_path: Path
    ) -> None:
        """Non-mapping YAML should raise ValueError."""
        registry_file = tmp_path / "registry.yaml"
        registry_file.write_text("- item1\n- item2\n", encoding="utf-8")
        with pytest.raises(ValueError, match="must be a mapping"):
            load_exemptions_registry(registry_file)

    def test_exemptions_registry__returns_empty_dict__5d86214b(
        self, tmp_path: Path
    ) -> None:
        """Empty YAML returns empty dict (safe_load returns None -> {})."""
        registry_file = tmp_path / "registry.yaml"
        registry_file.write_text("", encoding="utf-8")
        result = load_exemptions_registry(registry_file)
        assert result == {}


class TestGetRegistryValues:
    """Tests for get_registry_values."""

    def test_returns_values_for_valid_registry(self, tmp_path: Path) -> None:
        """Should return value-only mapping for valid entries."""
        raw = {
            "registries": {
                "file_size_limits": {
                    "src/bioetl/module.py": {
                        "value": 500,
                        "owner": "alice",
                    }
                }
            }
        }
        path = _write_registry(tmp_path, raw)
        result = get_registry_values("file_size_limits", path)
        assert result == {"src/bioetl/module.py": 500}

    def test_non_dict_registries_raises(self, tmp_path: Path) -> None:
        """Non-dict 'registries' should raise ValueError."""
        raw: dict[str, object] = {"registries": "not_a_dict"}
        path = _write_registry(tmp_path, raw)
        with pytest.raises(ValueError, match="must be a mapping"):
            get_registry_values("file_size_limits", path)

    def test_non_dict_registry_section_raises(self, tmp_path: Path) -> None:
        """Non-dict specific registry section should raise ValueError."""
        raw = {"registries": {"file_size_limits": "not_a_dict"}}
        path = _write_registry(tmp_path, raw)
        with pytest.raises(ValueError, match="expected mapping"):
            get_registry_values("file_size_limits", path)

    def test_entry_missing_value_raises(self, tmp_path: Path) -> None:
        """Entry without 'value' key should raise ValueError."""
        raw = {
            "registries": {
                "file_size_limits": {
                    "module.py": {"owner": "alice"}  # no 'value'
                }
            }
        }
        path = _write_registry(tmp_path, raw)
        with pytest.raises(ValueError, match="missing 'value'"):
            get_registry_values("file_size_limits", path)


class TestResolveRegistryValue:
    """Tests for resolve_registry_value."""

    def test_finds_by_full_path_with_symbol(self) -> None:
        """Should find value by full path with symbol."""
        values = {"src/bioetl/module.py::MyClass": 500}
        result = resolve_registry_value(
            values,
            module_path="src/bioetl/module.py",
            symbol_name="MyClass",
        )
        assert result == 500

    def test_finds_by_full_path_no_symbol(self) -> None:
        """Should find value by full path without symbol."""
        values = {"src/bioetl/module.py": 300}
        result = resolve_registry_value(
            values,
            module_path="src/bioetl/module.py",
        )
        assert result == 300

    def test_finds_by_symbol_only(self) -> None:
        """Should fall back to symbol-only key."""
        values = {"MyClass": 400}
        result = resolve_registry_value(
            values,
            module_path="src/bioetl/module.py",
            symbol_name="MyClass",
        )
        assert result == 400

    def test_finds_by_legacy_name(self) -> None:
        """Should fall back to legacy_name."""
        values = {"old_module_name": 200}
        result = resolve_registry_value(
            values,
            module_path="src/bioetl/module.py",
            legacy_name="old_module_name",
        )
        assert result == 200

    def test_finds_by_basename(self) -> None:
        """Should fall back to basename of module_path."""
        values = {"module.py": 100}
        result = resolve_registry_value(
            values,
            module_path="src/bioetl/module.py",
        )
        assert result == 100

    def test_returns_none_when_not_found(self) -> None:
        """Should return None when no candidate matches."""
        result = resolve_registry_value(
            {},
            module_path="src/bioetl/module.py",
            symbol_name="MyClass",
        )
        assert result is None

    def test_priority_path_with_symbol_over_path(self) -> None:
        """Path with symbol should take priority over path alone."""
        values = {
            "src/bioetl/module.py::MyClass": 500,
            "src/bioetl/module.py": 300,
        }
        result = resolve_registry_value(
            values,
            module_path="src/bioetl/module.py",
            symbol_name="MyClass",
        )
        assert result == 500


class TestValidateExemptionKeyNormalization:
    """Tests for validate_exemption_key_normalization."""

    def test_valid_canonical_keys(self, tmp_path: Path) -> None:
        """Canonical path keys that exist should produce no errors."""
        # Create a source file to reference
        src_dir = tmp_path / "src" / "bioetl" / "quality"
        src_dir.mkdir(parents=True)
        module_file = src_dir / "module.py"
        module_file.write_text("# test\n", encoding="utf-8")

        raw = {
            "registries": {
                "file_size_limits": {
                    "src/bioetl/quality/module.py": {
                        "value": 500,
                        "owner": "alice",
                    }
                }
            }
        }
        path = _write_registry(tmp_path, raw)

        # Mock project_root to return our tmp_path
        with patch(
            "bioetl.infrastructure.quality.exemptions_registry._project_root",
            return_value=tmp_path,
        ):
            errors = validate_exemption_key_normalization(path)

        assert errors == []

    def test_non_canonical_key_adds_error(self, tmp_path: Path) -> None:
        """Non-canonical key (bare module name) should add error."""
        raw = {
            "registries": {
                "file_size_limits": {
                    "just_a_module_name": {  # not canonical path
                        "value": 500,
                        "owner": "alice",
                    }
                }
            }
        }
        path = _write_registry(tmp_path, raw)
        with patch(
            "bioetl.infrastructure.quality.exemptions_registry._project_root",
            return_value=tmp_path,
        ):
            errors = validate_exemption_key_normalization(path)
        assert any("canonical path key" in e for e in errors)

    def test_non_existent_target_adds_error(self, tmp_path: Path) -> None:
        """Canonical key pointing to non-existent file should add error."""
        raw = {
            "registries": {
                "file_size_limits": {
                    "src/bioetl/nonexistent_module.py": {
                        "value": 500,
                        "owner": "alice",
                    }
                }
            }
        }
        path = _write_registry(tmp_path, raw)
        with patch(
            "bioetl.infrastructure.quality.exemptions_registry._project_root",
            return_value=tmp_path,
        ):
            errors = validate_exemption_key_normalization(path)
        assert any("does not exist" in e for e in errors)


class TestValidateExemptionsRegistry:
    """Tests for validate_exemptions_registry."""

    def _valid_raw(self) -> dict[str, object]:
        registries: dict[str, object] = {}
        for name in REQUIRED_EXEMPTION_REGISTRIES:
            registries[name] = {}  # empty (allowed for all required ones)
        return {
            "policy": {
                "required_fields": [
                    "value",
                    "owner",
                    "reason",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            },
            "registries": registries,
        }

    def test_valid_registry_no_metadata_errors(self, tmp_path: Path) -> None:
        """Valid registry with all required sections should produce no errors."""
        path = _write_registry(tmp_path, self._valid_raw())
        with (
            patch(
                "bioetl.infrastructure.quality.exemptions_registry.validate_exemption_key_normalization",
                return_value=[],
            ),
            patch(
                "bioetl.infrastructure.quality.exemptions_registry.validate_exemption_target_references",
                return_value=[],
            ),
        ):
            meta_errors, expired = validate_exemptions_registry(
                path, today=date(2025, 6, 15)
            )
        assert meta_errors == []
        assert expired == []

    def test_missing_registries_section(self, tmp_path: Path) -> None:
        """Missing 'registries' key should return error."""
        path = _write_registry(tmp_path, {"policy": {}})
        meta_errors, _ = validate_exemptions_registry(path, today=date(2025, 6, 15))
        assert any("registries" in e for e in meta_errors)

    def test_non_dict_registries_section(self, tmp_path: Path) -> None:
        """Non-dict 'registries' should return error."""
        path = _write_registry(
            tmp_path,
            {
                "policy": {
                    "required_fields": [
                        "owner",
                        "classification",
                        "linked_rf",
                        "expires_on",
                        "removal_step",
                    ]
                },
                "registries": "not_a_dict",
            },
        )
        meta_errors, _ = validate_exemptions_registry(path, today=date(2025, 6, 15))
        assert any("registries" in e for e in meta_errors)

    def test_missing_required_registry(self, tmp_path: Path) -> None:
        """Missing required registry should add error."""
        raw = self._valid_raw()
        assert isinstance(raw["registries"], dict)
        del raw["registries"]["god_object"]  # type: ignore[attr-defined]
        path = _write_registry(tmp_path, raw)
        with (
            patch(
                "bioetl.infrastructure.quality.exemptions_registry.validate_exemption_key_normalization",
                return_value=[],
            ),
            patch(
                "bioetl.infrastructure.quality.exemptions_registry.validate_exemption_target_references",
                return_value=[],
            ),
        ):
            meta_errors, _ = validate_exemptions_registry(path, today=date(2025, 6, 15))
        assert any("god_object" in e for e in meta_errors)

    def test_expired_entry_tracked(self, tmp_path: Path) -> None:
        """Entry with past expiry should be in expired_entries."""
        raw = self._valid_raw()
        assert isinstance(raw["registries"], dict)
        raw["registries"]["god_object"] = {  # type: ignore[index]
            "some_module.py": {
                "value": 15,
                "owner": "alice",
                "reason": "big class",
                "classification": "technical_debt",
                "linked_rf": "RF-001",
                "expires_on": "2020-01-01",
                "removal_step": "refactor",
            }
        }
        path = _write_registry(tmp_path, raw)
        with (
            patch(
                "bioetl.infrastructure.quality.exemptions_registry.validate_exemption_key_normalization",
                return_value=[],
            ),
            patch(
                "bioetl.infrastructure.quality.exemptions_registry.validate_exemption_target_references",
                return_value=[],
            ),
        ):
            _, expired = validate_exemptions_registry(path, today=date(2025, 6, 15))
        assert len(expired) >= 1

    def test_today_defaults_to_date_today(self, tmp_path: Path) -> None:
        """today=None should use date.today() without error."""
        path = _write_registry(tmp_path, self._valid_raw())
        with (
            patch(
                "bioetl.infrastructure.quality.exemptions_registry.validate_exemption_key_normalization",
                return_value=[],
            ),
            patch(
                "bioetl.infrastructure.quality.exemptions_registry.validate_exemption_target_references",
                return_value=[],
            ),
        ):
            meta_errors, _ = validate_exemptions_registry(path)
        assert isinstance(meta_errors, list)

    def test_constants_defined(self) -> None:
        """Constants should be properly defined."""
        assert isinstance(REQUIRED_EXEMPTION_REGISTRIES, tuple)
        assert "god_object" in REQUIRED_EXEMPTION_REGISTRIES
        assert isinstance(EXEMPTION_REGISTRIES_ALLOW_EMPTY, frozenset)


class TestValidateExemptionTargetReferences:
    """Tests for validate_exemption_target_references."""

    def test_valid_path_qualified_class_key(self, tmp_path: Path) -> None:
        """Path-qualified class keys should validate against live source files."""
        src_dir = tmp_path / "src" / "bioetl" / "application"
        src_dir.mkdir(parents=True)
        module_file = src_dir / "module.py"
        module_file.write_text(
            "class ExampleService:\n    pass\n",
            encoding="utf-8",
        )

        raw = {
            "policy": {
                "required_fields": [
                    "value",
                    "owner",
                    "reason",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            },
            "registries": {name: {} for name in REQUIRED_EXEMPTION_REGISTRIES},
        }
        registries = raw["registries"]
        assert isinstance(registries, dict)
        registries["class_size"] = {
            "src/bioetl/application/module.py::ExampleService": {
                "value": 350,
                "owner": "alice",
                "reason": "temporary hotspot",
                "classification": "technical_debt",
                "linked_rf": "RF-001",
                "expires_on": "2026-06-30",
                "removal_step": "split service",
            }
        }

        path = _write_registry(tmp_path, raw)
        with patch(
            "bioetl.infrastructure.quality.exemptions_registry._project_root",
            return_value=tmp_path,
        ):
            errors = validate_exemption_target_references(path)

        assert errors == []

    def test_missing_symbol_reports_error(self, tmp_path: Path) -> None:
        """Missing path-qualified symbols should raise target-reference errors."""
        src_dir = tmp_path / "src" / "bioetl" / "application"
        src_dir.mkdir(parents=True)
        module_file = src_dir / "module.py"
        module_file.write_text(
            "class ExampleService:\n    pass\n",
            encoding="utf-8",
        )

        raw = {
            "policy": {
                "required_fields": [
                    "value",
                    "owner",
                    "reason",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            },
            "registries": {name: {} for name in REQUIRED_EXEMPTION_REGISTRIES},
        }
        registries = raw["registries"]
        assert isinstance(registries, dict)
        registries["class_size"] = {
            "src/bioetl/application/module.py::MissingService": {
                "value": 350,
                "owner": "alice",
                "reason": "temporary hotspot",
                "classification": "technical_debt",
                "linked_rf": "RF-001",
                "expires_on": "2026-06-30",
                "removal_step": "split service",
            }
        }

        path = _write_registry(tmp_path, raw)
        with patch(
            "bioetl.infrastructure.quality.exemptions_registry._project_root",
            return_value=tmp_path,
        ):
            errors = validate_exemption_target_references(path)

        assert any("MissingService" in error for error in errors)

    def test_ambiguous_bare_function_symbol_reports_error(self, tmp_path: Path) -> None:
        """Bare function keys should be rejected when they match multiple modules."""
        app_dir = tmp_path / "src" / "bioetl" / "application"
        infra_dir = tmp_path / "src" / "bioetl" / "infrastructure"
        app_dir.mkdir(parents=True)
        infra_dir.mkdir(parents=True)
        (app_dir / "module_a.py").write_text(
            "def repeated_name():\n    return 1\n",
            encoding="utf-8",
        )
        (infra_dir / "module_b.py").write_text(
            "def repeated_name():\n    return 2\n",
            encoding="utf-8",
        )

        raw = {
            "policy": {
                "required_fields": [
                    "value",
                    "owner",
                    "reason",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            },
            "registries": {name: {} for name in REQUIRED_EXEMPTION_REGISTRIES},
        }
        registries = raw["registries"]
        assert isinstance(registries, dict)
        registries["function_complexity"] = {
            "repeated_name": {
                "value": 15,
                "owner": "alice",
                "reason": "temporary hotspot",
                "classification": "technical_debt",
                "linked_rf": "RF-001",
                "expires_on": "2026-06-30",
                "removal_step": "split function",
            }
        }

        path = _write_registry(tmp_path, raw)
        with patch(
            "bioetl.infrastructure.quality.exemptions_registry._project_root",
            return_value=tmp_path,
        ):
            errors = validate_exemption_target_references(path)

        assert any("bare symbol key is ambiguous" in error for error in errors)

    def test_path_qualified_symbol_requires_non_empty_name(
        self, tmp_path: Path
    ) -> None:
        """Path-qualified keys with an empty symbol suffix should fail clearly."""
        src_dir = tmp_path / "src" / "bioetl" / "application"
        src_dir.mkdir(parents=True)
        module_file = src_dir / "module.py"
        module_file.write_text("def some_fn():\n    return 1\n", encoding="utf-8")

        raw = {
            "policy": {
                "required_fields": [
                    "value",
                    "owner",
                    "reason",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            },
            "registries": {name: {} for name in REQUIRED_EXEMPTION_REGISTRIES},
        }
        registries = raw["registries"]
        assert isinstance(registries, dict)
        registries["function_complexity"] = {
            "src/bioetl/application/module.py::": {
                "value": 15,
                "owner": "alice",
                "reason": "temporary hotspot",
                "classification": "technical_debt",
                "linked_rf": "RF-001",
                "expires_on": "2026-06-30",
                "removal_step": "split function",
            }
        }

        path = _write_registry(tmp_path, raw)
        with patch(
            "bioetl.infrastructure.quality.exemptions_registry._project_root",
            return_value=tmp_path,
        ):
            errors = validate_exemption_target_references(path)

        assert any("must be non-empty" in error for error in errors)

    def test_domain_complexity_accepts_path_qualified_class_symbol(
        self, tmp_path: Path
    ) -> None:
        """Domain-complexity exemptions may target class symbols emitted by radon."""
        src_dir = tmp_path / "src" / "bioetl" / "domain" / "config"
        src_dir.mkdir(parents=True)
        module_file = src_dir / "memory.py"
        module_file.write_text(
            "class MemoryConfig:\n    pass\n",
            encoding="utf-8",
        )

        raw = {
            "policy": {
                "required_fields": [
                    "value",
                    "owner",
                    "reason",
                    "classification",
                    "linked_rf",
                    "expires_on",
                    "removal_step",
                ]
            },
            "registries": {name: {} for name in REQUIRED_EXEMPTION_REGISTRIES},
        }
        registries = raw["registries"]
        assert isinstance(registries, dict)
        registries["domain_complexity"] = {
            "src/bioetl/domain/config/memory.py::MemoryConfig": {
                "value": 6,
                "owner": "alice",
                "reason": "pydantic model complexity is analyzer noise",
                "classification": "intentional_exception",
                "linked_rf": "RF-001",
                "expires_on": "2026-06-30",
                "removal_step": "revisit when complexity analyzer is refined",
            }
        }

        path = _write_registry(tmp_path, raw)
        with patch(
            "bioetl.infrastructure.quality.exemptions_registry._project_root",
            return_value=tmp_path,
        ):
            errors = validate_exemption_target_references(path)

        assert errors == []
