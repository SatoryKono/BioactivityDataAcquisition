"""Tests for ConfigPathResolver."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.application.config.resolution import ConfigPathResolver


class TestConfigPathResolver:
    """Tests for ConfigPathResolver class."""

    def test_infer_config_path_valid_pattern(self, tmp_path: Path) -> None:
        """Test config path inference from valid pipeline name."""
        resolver = ConfigPathResolver(tmp_path)
        result = resolver.infer_config_path("compound_chembl")

        assert result == Path("pipelines/chembl/compound.yaml")

    def test_infer_config_path_multiple_underscores(self, tmp_path: Path) -> None:
        """Test config path inference with multiple underscores in name."""
        resolver = ConfigPathResolver(tmp_path)
        result = resolver.infer_config_path("compound_chembl_extra")

        # Should use first two parts: entity=compound, provider=chembl
        assert result == Path("pipelines/chembl/compound.yaml")

    def test_infer_config_path_invalid_pattern(self, tmp_path: Path) -> None:
        """Test config path inference returns None for invalid pattern."""
        resolver = ConfigPathResolver(tmp_path)
        result = resolver.infer_config_path("nounderscore")

        assert result is None

    def test_resolve_config_path_explicit_exists(self, tmp_path: Path) -> None:
        """Test resolve with explicit path that exists."""
        config_file = tmp_path / "custom" / "my_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("id: test")

        resolver = ConfigPathResolver(tmp_path)
        result = resolver.resolve_config_path(
            "compound_chembl",
            explicit_path=config_file,
        )

        assert result == config_file.resolve()

    def test_resolve_config_path_explicit_relative_to_root(
        self, tmp_path: Path
    ) -> None:
        """Test resolve with explicit relative path resolved against configs root."""
        config_file = tmp_path / "custom" / "my_config.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("id: test")

        resolver = ConfigPathResolver(tmp_path)
        result = resolver.resolve_config_path(
            "compound_chembl",
            explicit_path=Path("custom/my_config.yaml"),
        )

        assert result == config_file.resolve()

    def test_resolve_config_path_explicit_not_found(self, tmp_path: Path) -> None:
        """Test resolve raises error when explicit path doesn't exist."""
        resolver = ConfigPathResolver(tmp_path)

        with pytest.raises(FileNotFoundError, match="Config file not found"):
            resolver.resolve_config_path(
                "compound_chembl",
                explicit_path=Path("nonexistent.yaml"),
            )

    def test_resolve_config_path_inferred(self, tmp_path: Path) -> None:
        """Test resolve with inferred path from pipeline name."""
        config_file = tmp_path / "pipelines" / "chembl" / "compound.yaml"
        config_file.parent.mkdir(parents=True, exist_ok=True)
        config_file.write_text("id: chembl.compound")

        resolver = ConfigPathResolver(tmp_path)
        result = resolver.resolve_config_path("compound_chembl")

        assert result == config_file.resolve()

    def test_resolve_config_path_inferred_not_found(self, tmp_path: Path) -> None:
        """Test resolve raises error when inferred path doesn't exist."""
        resolver = ConfigPathResolver(tmp_path)

        with pytest.raises(FileNotFoundError, match="inferred from pipeline"):
            resolver.resolve_config_path("compound_chembl")

    def test_resolve_config_path_invalid_pattern_no_explicit(
        self, tmp_path: Path
    ) -> None:
        """Test resolve raises error when pattern is invalid and no explicit path."""
        resolver = ConfigPathResolver(tmp_path)

        with pytest.raises(ValueError, match="Cannot infer config path"):
            resolver.resolve_config_path("nounderscore")

    def test_configs_root_property(self, tmp_path: Path) -> None:
        """Test configs_root property returns configured root."""
        resolver = ConfigPathResolver(tmp_path)
        assert resolver.configs_root == tmp_path
