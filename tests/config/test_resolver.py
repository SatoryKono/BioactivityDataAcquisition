"""
Tests for ConfigResolver.
"""
from bioetl.config.resolver import ConfigResolver


def test_resolver_simple(tmp_path):
    """Test simple config resolution."""
    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        "entity_name: test\nprovider: chembl",
        encoding="utf-8"
    )

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
        "qc:\n  min_coverage: 0.5\nentity_name: base\nprovider: test_provider",
        encoding="utf-8"
    )

    config_file = tmp_path / "config.yaml"
    config_file.write_text(
        """extends: base
entity_name: override""",
        encoding="utf-8"
    )

    resolver = ConfigResolver(profiles_dir=str(profiles_dir))
    config = resolver.resolve(str(config_file))

    assert config.entity_name == "override"  # Overridden
    assert config.qc.min_coverage == 0.5  # Inherited


def test_deep_merge(tmp_path):
    """Test deep dictionary merge."""
    # Using private method via public resolve to verify behavior or test directly
    resolver = ConfigResolver(profiles_dir=str(tmp_path))
    base = {"a": {"x": 1}}
    update = {"a": {"y": 2}, "b": 3}

    # pylint: disable=protected-access
    result = resolver._deep_merge(base, update)
    assert result["a"]["x"] == 1
    assert result["a"]["y"] == 2
    assert result["b"] == 3
