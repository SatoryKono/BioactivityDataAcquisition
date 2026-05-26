"""Unit tests for exemptions_registry_paths module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from bioetl.infrastructure.quality.exemptions_registry_paths import (
    build_module_path_key,
    is_module_path_key,
    normalize_path_text,
    project_root,
    resolve_registry_path,
)


class TestProjectRoot:
    """Tests for project_root."""

    def test_returns_path(self) -> None:
        """Should return a Path object."""
        result = project_root()
        assert isinstance(result, Path)

    def test_is_absolute(self) -> None:
        """Returned path should be absolute."""
        assert project_root().is_absolute()

    def test_is_directory(self) -> None:
        """Returned path should be an existing directory."""
        assert project_root().is_dir()


class TestResolveRegistryPath:
    """Tests for resolve_registry_path."""

    def test_none_returns_default(self) -> None:
        """None input should return default path resolved against project root."""
        result = resolve_registry_path(None)
        assert isinstance(result, Path)
        # Should end with the default filename
        assert result.name == "architecture_metric_exemptions.yaml"

    def test_absolute_path_returned_as_is__test_resolve_registry_path_infrastructure_quality_test_exemptions_registry_paths_46(
        self,
    ) -> None:
        """Absolute path should be returned unchanged (resolved for platform)."""
        abs_path = Path(tempfile.gettempdir(), "test.yaml").resolve()
        result = resolve_registry_path(abs_path)
        assert result == abs_path

    def test_relative_path_resolved_against_root(self) -> None:
        """Relative path should be resolved against project root."""
        rel_path = Path("configs/quality/test.yaml")
        result = resolve_registry_path(rel_path)
        assert result.is_absolute()
        assert str(result).endswith("test.yaml")

    def test_string_path_accepted(self) -> None:
        """String path should be accepted."""
        result = resolve_registry_path("configs/quality/test.yaml")
        assert isinstance(result, Path)


class TestNormalizePathText:
    """Tests for normalize_path_text."""

    def test_backslashes_converted(self) -> None:
        """Backslashes should be converted to forward slashes."""
        result = normalize_path_text("src\\bioetl\\module.py")
        assert result == "src/bioetl/module.py"

    def test_leading_dotslash_stripped(self) -> None:
        """Leading './' should be stripped."""
        result = normalize_path_text("./src/bioetl/module.py")
        assert result == "src/bioetl/module.py"

    def test_already_normalized__test_normalize_path_text_infrastructure_quality_test_exemptions_registry_paths_78(
        self,
    ) -> None:
        """Already normalized path should be unchanged."""
        result = normalize_path_text("src/bioetl/module.py")
        assert result == "src/bioetl/module.py"

    def test_mixed_slashes(self) -> None:
        """Mixed slash path should be fully normalized."""
        result = normalize_path_text("./src\\bioetl/module.py")
        assert result == "src/bioetl/module.py"

    def test_empty_string(self) -> None:
        """Empty string should return empty string."""
        result = normalize_path_text("")
        assert result == ""


class TestIsModulePathKey:
    """Tests for is_module_path_key."""

    def test_canonical_key(self) -> None:
        """Canonical src/bioetl/.../module.py key should be valid."""
        assert is_module_path_key("src/bioetl/infrastructure/quality/scoring.py")

    def test_non_bioetl_prefix(self) -> None:
        """Path not starting with src/bioetl/ should be invalid."""
        assert not is_module_path_key("src/other/module.py")

    def test_not_ending_py(self) -> None:
        """Path not ending in .py should be invalid."""
        assert not is_module_path_key("src/bioetl/module.txt")

    def test_bare_filename(self) -> None:
        """Bare filename (no path) should be invalid."""
        assert not is_module_path_key("module.py")

    def test_backslash_path_normalized(self) -> None:
        """Backslash path should be normalized before checking."""
        assert is_module_path_key("src\\bioetl\\module.py")

    def test_with_leading_dotslash(self) -> None:
        """Leading './' should be stripped before checking."""
        assert is_module_path_key("./src/bioetl/module.py")


class TestBuildModulePathKey:
    """Tests for build_module_path_key."""

    def test_already_canonical_key(self) -> None:
        """Canonical key should be returned as-is."""
        canonical = "src/bioetl/infrastructure/quality/scoring.py"
        result = build_module_path_key(canonical)
        assert result == canonical

    def test_absolute_path_under_src(self) -> None:
        """Absolute path under project's src/ should produce canonical key."""
        root = project_root()
        abs_path = root / "src" / "bioetl" / "infrastructure" / "quality" / "scoring.py"
        result = build_module_path_key(abs_path)
        assert result == "src/bioetl/infrastructure/quality/scoring.py"

    def test_bioetl_prefix_path(self) -> None:
        """Path starting with 'bioetl/' should get 'src/' prefix."""
        result = build_module_path_key("bioetl/infrastructure/quality/scoring.py")
        assert result == "src/bioetl/infrastructure/quality/scoring.py"

    def test_raises_for_unresolvable_path(self) -> None:
        """Path not under src/ or bioetl/ should raise ValueError."""
        with pytest.raises(ValueError, match="canonical"):
            build_module_path_key("/totally/unrelated/path/module.py")

    def test_string_input_accepted(self) -> None:
        """String input should be accepted."""
        result = build_module_path_key("src/bioetl/domain/types.py")
        assert result == "src/bioetl/domain/types.py"
