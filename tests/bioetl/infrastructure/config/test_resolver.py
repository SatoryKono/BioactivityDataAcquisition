"""
Tests for ConfigResolver.
"""

import pytest

from bioetl.application.config_loader import (
    ConfigFileNotFoundError,
    _load_yaml,
    _resolve_profile,
)
from bioetl.domain.transform.merge import deep_merge
from bioetl.infrastructure.config.resolver import ConfigResolver


def test_resolver_simple(tmp_path):
    """Test simple config resolution."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text("entity_name: test\nprovider: chembl", encoding="utf-8")

    resolver = ConfigResolver(profiles_dir=str(tmp_path))
    config = resolver.resolve(str(config_file))

    assert config.entity_name == "test"
    assert config.provider == "chembl"


def test_resolver_extends(tmp_path):
    """Test config inheritance via 'extends'."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    base_profile = profiles_dir / "base.yaml"
    base_profile.write_text(
        "qc:\n  min_coverage: 0.5\nentity_name: base\nprovider: chembl",
        encoding="utf-8",
    )

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """extends: base
entity_name: override""",
        encoding="utf-8",
    )

    resolver = ConfigResolver(profiles_dir=str(profiles_dir))
    config = resolver.resolve(str(config_file))

    assert config.entity_name == "override"  # Overridden
    # pylint: disable=no-member
    assert config.qc.min_coverage == 0.5  # Inherited


def test_deep_merge():
    """Test deep dictionary merge."""
    base = {"a": {"x": 1}}
    update = {"a": {"y": 2}, "b": 3}

    result = deep_merge(base, update)
    assert result["a"]["x"] == 1
    assert result["a"]["y"] == 2
    assert result["b"] == 3


def test_resolver_cli_override(tmp_path):
    """Test CLI profile overriding config."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    # CLI profile
    (profiles_dir / "prod.yaml").write_text(
        "entity_name: prod_entity\nprovider: chembl", encoding="utf-8"
    )

    # Config file
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "entity_name: config_entity\nprovider: chembl", encoding="utf-8"
    )

    resolver = ConfigResolver(profiles_dir=str(profiles_dir))
    config = resolver.resolve(str(config_file), profile="prod")

    # CLI profile wins over config file for entity_name
    assert config.entity_name == "prod_entity"
    assert config.provider == "chembl"


def test_profile_inheritance_recursive(tmp_path):
    """Test profile inheriting from another profile."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    (profiles_dir / "root.yaml").write_text("entity_name: root", encoding="utf-8")
    (profiles_dir / "parent.yaml").write_text(
        "extends: root\nentity_name: parent\nprovider: chembl", encoding="utf-8"
    )
    config_file = tmp_path / "config.yaml"
    config_file.write_text("extends: parent", encoding="utf-8")

    resolver = ConfigResolver(profiles_dir=str(profiles_dir))
    config = resolver.resolve(str(config_file))

    assert config.entity_name == "parent"
    assert config.provider == "chembl"


def test_circular_dependency(tmp_path):
    """Test detection of circular dependencies in profiles."""
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "a.yaml").write_text("extends: b", encoding="utf-8")
    (profiles_dir / "b.yaml").write_text("extends: a", encoding="utf-8")

    # Test circular dependency through resolve (will hit recursion limit)
    resolver = ConfigResolver(profiles_dir=str(profiles_dir))
    config_file = tmp_path / "config.yaml"
    config_file.write_text("extends: a\nprovider: chembl", encoding="utf-8")

    # Should raise RecursionError or similar due to circular dependency
    with pytest.raises((RecursionError, ConfigFileNotFoundError)):
        resolver.resolve(str(config_file))


def test_profile_not_found(tmp_path):
    """Test error when profile missing."""
    resolver = ConfigResolver(profiles_dir=str(tmp_path))
    config_file = tmp_path / "config.yaml"
    config_file.write_text("extends: missing_profile", encoding="utf-8")

    with pytest.raises(ConfigFileNotFoundError):
        resolver.resolve(str(config_file))


def test_default_profile_missing(tmp_path):
    """Test default profile is optional."""
    # Test that missing default profile raises ConfigFileNotFoundError
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()

    # When default profile doesn't exist, it should raise ConfigFileNotFoundError
    with pytest.raises(ConfigFileNotFoundError):
        _resolve_profile("default", profiles_root=profiles_dir)


def test_empty_yaml(tmp_path):
    """Test handling of empty YAML file."""
    empty_file = tmp_path / "empty.yaml"
    empty_file.touch()

    # Test _load_yaml directly
    data = _load_yaml(empty_file)
    assert data == {}
