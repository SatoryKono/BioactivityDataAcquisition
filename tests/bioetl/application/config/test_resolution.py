"""Tests for ConfigPathResolver and build_pipeline_config."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from bioetl.application.config.resolution import (
    ConfigPathResolver,
    _infer_configs_root,
    build_pipeline_config,
)


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


class TestBuildPipelineConfig:
    """Tests for build_pipeline_config function."""

    def test_build_pipeline_config_calls_loader(self, tmp_path: Path) -> None:
        """Test that build_pipeline_config delegates to loader."""
        config_path = tmp_path / "pipelines" / "chembl" / "compound.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("id: chembl.compound")

        mock_config = MagicMock()
        mock_loader = MagicMock()
        mock_loader.get_from_path.return_value = mock_config

        result = build_pipeline_config(
            config_path,
            loader=mock_loader,
            profile="development",
        )

        assert result == mock_config
        mock_loader.get_from_path.assert_called_once()
        call_kwargs = mock_loader.get_from_path.call_args
        assert call_kwargs[0][0] == config_path
        assert call_kwargs[1]["profile"] == "development"

    def test_build_pipeline_config_infers_configs_root(self, tmp_path: Path) -> None:
        """Test that configs_root is inferred from config path structure."""
        configs_root = tmp_path / "configs"
        config_path = configs_root / "pipelines" / "chembl" / "compound.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("id: chembl.compound")

        mock_config = MagicMock()
        mock_loader = MagicMock()
        mock_loader.get_from_path.return_value = mock_config

        build_pipeline_config(
            config_path,
            loader=mock_loader,
        )

        call_kwargs = mock_loader.get_from_path.call_args
        # profiles_root should be configs_root / "profiles"
        expected_profiles_root = configs_root / "profiles"
        assert call_kwargs[1]["profiles_root"] == expected_profiles_root

    def test_build_pipeline_config_explicit_configs_root(self, tmp_path: Path) -> None:
        """Test that explicit configs_root overrides inference."""
        config_path = tmp_path / "some" / "random" / "config.yaml"
        config_path.parent.mkdir(parents=True, exist_ok=True)
        config_path.write_text("id: test")

        explicit_root = tmp_path / "my_configs"

        mock_config = MagicMock()
        mock_loader = MagicMock()
        mock_loader.get_from_path.return_value = mock_config

        build_pipeline_config(
            config_path,
            configs_root=explicit_root,
            loader=mock_loader,
        )

        call_kwargs = mock_loader.get_from_path.call_args
        expected_profiles_root = explicit_root / "profiles"
        assert call_kwargs[1]["profiles_root"] == expected_profiles_root

    def test_build_pipeline_config_passes_overrides(self, tmp_path: Path) -> None:
        """Test that cli_overrides and env_overrides are passed through."""
        config_path = tmp_path / "config.yaml"
        config_path.write_text("id: test")

        mock_config = MagicMock()
        mock_loader = MagicMock()
        mock_loader.get_from_path.return_value = mock_config

        cli_overrides = {"batch_size": 100}
        env_overrides = {"output_path": "/tmp/out"}

        build_pipeline_config(
            config_path,
            loader=mock_loader,
            cli_overrides=cli_overrides,
            env_overrides=env_overrides,
        )

        call_kwargs = mock_loader.get_from_path.call_args
        assert call_kwargs[1]["cli_overrides"] == cli_overrides
        assert call_kwargs[1]["env_overrides"] == env_overrides


class TestInferConfigsRoot:
    """Tests for _infer_configs_root helper."""

    def test_infer_from_standard_structure(self, tmp_path: Path) -> None:
        """Test inference from standard pipelines directory structure."""
        # configs/pipelines/chembl/compound.yaml
        config_path = tmp_path / "configs" / "pipelines" / "chembl" / "compound.yaml"
        result = _infer_configs_root(config_path)

        assert result == tmp_path / "configs"

    def test_infer_fallback_to_default(self, tmp_path: Path) -> None:
        """Test fallback to 'configs' when structure doesn't match."""
        config_path = tmp_path / "some" / "random" / "path" / "config.yaml"
        result = _infer_configs_root(config_path)

        assert result == Path("configs")
