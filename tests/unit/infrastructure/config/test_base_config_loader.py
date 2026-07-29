# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for base config loader functionality."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.base_config_loader import (
    BaseConfigLoader,
    _load_yaml_file,
)

pytestmark = pytest.mark.timeout(120)  # Extended timeout for heavy imports


class ConcreteConfigLoader(BaseConfigLoader[dict]):
    """Concrete implementation for testing BaseConfigLoader."""

    def load(
        self,
        provider: str,
        entity: str,
        inline_overrides: dict | None = None,
    ) -> dict:
        """Load config for testing."""
        base_path = self._configs_root / provider / f"{entity}.yaml"
        base = self._load_yaml(base_path)
        if inline_overrides:
            return self._deep_merge_base(base, inline_overrides, frozenset())
        return base


class TestLoadYamlFile:
    """Test _load_yaml_file utility function."""

    def test_load_yaml_file_nonexistent(self, tmp_path: Path) -> None:
        """Test that non-existent file returns empty dict."""
        result = _load_yaml_file(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_load_yaml_file_empty(self, tmp_path: Path) -> None:
        """Test that empty file returns empty dict."""
        file_path = tmp_path / "empty.yaml"
        file_path.write_text("", encoding="utf-8")
        result = _load_yaml_file(file_path)
        assert result == {}

    def test_load_yaml_file_valid_yaml(self, tmp_path: Path) -> None:
        """Test that valid YAML is parsed correctly."""
        file_path = tmp_path / "config.yaml"
        file_path.write_text(
            "key: value\nlist:\n  - item1\n  - item2\n", encoding="utf-8"
        )
        result = _load_yaml_file(file_path)
        assert result == {"key": "value", "list": ["item1", "item2"]}

    def test_load_yaml_file_null_content(self, tmp_path: Path) -> None:
        """Test that YAML with null content returns empty dict."""
        file_path = tmp_path / "null.yaml"
        file_path.write_text("null\n", encoding="utf-8")
        result = _load_yaml_file(file_path)
        assert result == {}

    def test_load_yaml_file_os_error(self, tmp_path: Path) -> None:
        """Test that OSError is handled gracefully."""
        # Create a directory instead of a file
        dir_path = tmp_path / "not_a_file"
        dir_path.mkdir()
        result = _load_yaml_file(dir_path)
        assert result == {}


class TestBaseConfigLoader:
    """Test BaseConfigLoader abstract class."""

    def test_base_config_loader_initialization(self, tmp_path: Path) -> None:
        """Test that loader initializes with configs root."""
        loader = ConcreteConfigLoader(tmp_path)
        assert loader._configs_root == tmp_path
        assert loader._cache == {}

    def test_base_config_loader_clear_cache(self, tmp_path: Path) -> None:
        """Test that cache can be cleared."""
        loader = ConcreteConfigLoader(tmp_path)
        loader._cache["test"] = {"data": "value"}
        loader.clear_cache()
        assert loader._cache == {}

    def test_load_yaml_missing_file(self, tmp_path: Path) -> None:
        """Test that missing YAML file returns empty dict."""
        loader = ConcreteConfigLoader(tmp_path)
        result = loader._load_yaml(tmp_path / "missing.yaml")
        assert result == {}

    def test_load_yaml_valid_file(self, tmp_path: Path) -> None:
        """Test that valid YAML file is loaded correctly."""
        file_path = tmp_path / "config.yaml"
        file_path.write_text("key: value\n", encoding="utf-8")
        loader = ConcreteConfigLoader(tmp_path)
        result = loader._load_yaml(file_path)
        assert result == {"key": "value"}

    def test_deep_merge_base_simple(self, tmp_path: Path) -> None:
        """Test simple deep merge without list concatenation."""
        loader = ConcreteConfigLoader(tmp_path)
        base = {"key1": "value1"}
        override = {"key2": "value2"}
        result = loader._deep_merge_base(base, override, frozenset())
        assert result == {"key1": "value1", "key2": "value2"}

    def test_deep_merge_base_override(self, tmp_path: Path) -> None:
        """Test that override values replace base values."""
        loader = ConcreteConfigLoader(tmp_path)
        base = {"key": "base_value"}
        override = {"key": "override_value"}
        result = loader._deep_merge_base(base, override, frozenset())
        assert result == {"key": "override_value"}

    def test_deep_merge_base_nested(self, tmp_path: Path) -> None:
        """Test deep merge with nested dictionaries."""
        loader = ConcreteConfigLoader(tmp_path)
        base = {"outer": {"inner1": "value1"}}
        override = {"outer": {"inner2": "value2"}}
        result = loader._deep_merge_base(base, override, frozenset())
        assert result == {"outer": {"inner1": "value1", "inner2": "value2"}}

    def test_merge_lists_string_deduplication(self, tmp_path: Path) -> None:
        """Test that string lists are merged with deduplication."""
        loader = ConcreteConfigLoader(tmp_path)
        base = ["item1", "item2"]
        override = ["item2", "item3"]
        result = loader._merge_lists(base, override, "test_key")
        assert result == ["item1", "item2", "item3"]

    def test_merge_lists_non_string_concatenation(self, tmp_path: Path) -> None:
        """Test that non-string lists are simply concatenated."""
        loader = ConcreteConfigLoader(tmp_path)
        base = [{"id": 1}]
        override = [{"id": 2}]
        result = loader._merge_lists(base, override, "test_key")
        assert result == [{"id": 1}, {"id": 2}]

    def test_merge_lists_empty_base(self, tmp_path: Path) -> None:
        """Test that empty base list returns override."""
        loader = ConcreteConfigLoader(tmp_path)
        base = []
        override = ["item1", "item2"]
        result = loader._merge_lists(base, override, "test_key")
        assert result == ["item1", "item2"]

    def test_merge_lists_empty_override(self, tmp_path: Path) -> None:
        """Test that empty override returns base."""
        loader = ConcreteConfigLoader(tmp_path)
        base = ["item1", "item2"]
        override = []
        result = loader._merge_lists(base, override, "test_key")
        assert result == ["item1", "item2"]

    def test_merge_lists_both_empty(self, tmp_path: Path) -> None:
        """Test that both empty lists return empty."""
        loader = ConcreteConfigLoader(tmp_path)
        result = loader._merge_lists([], [], "test_key")
        assert result == []

    def test_load_concrete_implementation(self, tmp_path: Path) -> None:
        """Test concrete loader implementation."""
        # Create provider/entity directory structure
        provider_dir = tmp_path / "chembl"
        provider_dir.mkdir(parents=True, exist_ok=True)
        config_file = provider_dir / "activity.yaml"
        config_file.write_text("key: value\n", encoding="utf-8")

        loader = ConcreteConfigLoader(tmp_path)
        result = loader.load("chembl", "activity")
        assert result == {"key": "value"}

    def test_load_with_inline_overrides(self, tmp_path: Path) -> None:
        """Test load with inline overrides."""
        provider_dir = tmp_path / "chembl"
        provider_dir.mkdir(parents=True, exist_ok=True)
        config_file = provider_dir / "activity.yaml"
        config_file.write_text("key1: value1\n", encoding="utf-8")

        loader = ConcreteConfigLoader(tmp_path)
        result = loader.load("chembl", "activity", {"key2": "value2"})
        assert result == {"key1": "value1", "key2": "value2"}

    def test_load_inline_override_base(self, tmp_path: Path) -> None:
        """Test that inline overrides replace base values."""
        provider_dir = tmp_path / "chembl"
        provider_dir.mkdir(parents=True, exist_ok=True)
        config_file = provider_dir / "activity.yaml"
        config_file.write_text("key: base_value\n", encoding="utf-8")

        loader = ConcreteConfigLoader(tmp_path)
        result = loader.load("chembl", "activity", {"key": "override_value"})
        assert result == {"key": "override_value"}
