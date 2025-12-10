"""Tests for ConfigMigrator."""

from copy import deepcopy
import warnings

from bioetl.domain.configs.migration import ConfigMigrator


class TestVersionDetection:
    """Tests for version detection logic."""

    def test_detects_v2_when_identity_present(self) -> None:
        """Config with identity section is detected as v2."""
        data = {"identity": {"provider": "dummy", "entity": "test"}}
        assert ConfigMigrator._detect_version(data) == 2

    def test_detects_v1_with_flat_entity_and_provider(self) -> None:
        """Flat entity + provider without identity is detected as v1."""
        data = {"entity": "test", "provider": "chembl"}
        assert ConfigMigrator._detect_version(data) == 1

    def test_detects_v1_with_entity_name_alias(self) -> None:
        """entity_name + provider without identity is detected as v1."""
        data = {"entity_name": "test", "provider": "chembl"}
        assert ConfigMigrator._detect_version(data) == 1

    def test_detects_v1_with_sources_section(self) -> None:
        """entity + sources section is detected as v1."""
        data = {"entity": "test", "sources": {"chembl": {}}}
        assert ConfigMigrator._detect_version(data) == 1

    def test_defaults_to_v2_for_minimal_config(self) -> None:
        """Minimal config defaults to v2."""
        data = {"some_field": "value"}
        assert ConfigMigrator._detect_version(data) == 2

    def test_defaults_to_v2_for_empty_config(self) -> None:
        """Empty config defaults to v2."""
        assert ConfigMigrator._detect_version({}) == 2


class TestV1Migration:
    """Tests for v1 -> v2 migration."""

    def test_migrates_entity_name_to_entity(self) -> None:
        """entity_name is migrated to entity."""
        data = {"entity_name": "test", "provider": "dummy"}
        result = ConfigMigrator.migrate(data)
        assert "entity_name" not in result
        assert result["identity"]["entity"] == "test"

    def test_generates_id_from_provider_entity(self) -> None:
        """id is generated as provider.entity if not present."""
        data = {"entity": "molecule", "provider": "chembl"}
        result = ConfigMigrator.migrate(data)
        assert result["identity"]["pipeline_id"] == "chembl.molecule"

    def test_generates_id_from_pipeline_name(self) -> None:
        """id is taken from pipeline.name if present."""
        data = {
            "entity": "test",
            "provider": "dummy",
            "pipeline": {"name": "custom-pipeline"},
        }
        result = ConfigMigrator.migrate(data)
        assert result["identity"]["pipeline_id"] == "custom-pipeline"

    def test_extracts_output_path_from_storage(self) -> None:
        """output_path is extracted from storage section."""
        data = {
            "entity": "test",
            "provider": "dummy",
            "storage": {"output_path": "/data/output"},
        }
        result = ConfigMigrator.migrate(data)
        assert result["sink"]["output_path"] == "/data/output"

    def test_extracts_batch_size_from_sources(self) -> None:
        """batch_size is extracted from sources section."""
        data = {
            "entity": "test",
            "provider": "chembl",
            "sources": {"chembl": {"batch_size": 50}},
        }
        result = ConfigMigrator.migrate(data)
        assert result["source"]["batch_size"] == 50

    def test_extracts_provider_config_from_sources(self) -> None:
        """provider_config is extracted from sources section."""
        data = {
            "entity": "test",
            "provider": "chembl",
            "sources": {
                "chembl": {
                    "base_url": "https://api.example.com",
                    "timeout_sec": 60,
                }
            },
        }
        result = ConfigMigrator.migrate(data)
        assert result["provider_config"]["provider"] == "chembl"
        assert result["provider_config"]["base_url"] == "https://api.example.com"
        assert result["provider_config"]["timeout_sec"] == 60

    def test_removes_sources_section(self) -> None:
        """sources section is removed after migration."""
        data = {
            "entity": "test",
            "provider": "chembl",
            "sources": {"chembl": {"batch_size": 25}},
        }
        result = ConfigMigrator.migrate(data)
        assert "sources" not in result

    def test_migrates_api_base_url_to_provider_config(self) -> None:
        """api_base_url is migrated to provider_config.base_url."""
        data = {
            "entity": "test",
            "provider": "dummy",
            "api_base_url": "https://example.com",
            "provider_config": {"provider": "dummy"},
        }
        result = ConfigMigrator.migrate(data)
        assert "api_base_url" not in result
        assert result["provider_config"]["base_url"] == "https://example.com"

    def test_v1_migration_emits_deprecation_warning(self) -> None:
        """v1 format triggers deprecation warning."""
        data = {"entity": "test", "provider": "dummy"}
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ConfigMigrator.migrate(data)
            assert len(w) == 1
            assert issubclass(w[0].category, DeprecationWarning)
            assert "Legacy v1 config format" in str(w[0].message)


class TestV2Normalization:
    """Tests for v2 format normalization (always applied)."""

    def test_packs_identity_section(self) -> None:
        """Flat identity fields are packed into identity section."""
        data = {"id": "test-pipeline", "provider": "dummy", "entity": "test"}
        result = ConfigMigrator.migrate(data)
        assert result["identity"]["pipeline_id"] == "test-pipeline"
        assert result["identity"]["provider"] == "dummy"
        assert result["identity"]["entity"] == "test"

    def test_packs_source_section(self) -> None:
        """Flat source fields are packed into source section."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "input_mode": "csv",
            "input_path": "/tmp/input.csv",
            "batch_size": 100,
        }
        result = ConfigMigrator.migrate(data)
        assert result["source"]["input_mode"] == "csv"
        assert result["source"]["input_path"] == "/tmp/input.csv"
        assert result["source"]["batch_size"] == 100

    def test_packs_sink_section(self) -> None:
        """Flat sink fields are packed into sink section."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "output_path": "/tmp/output",
            "dry_run": True,
        }
        result = ConfigMigrator.migrate(data)
        assert result["sink"]["output_path"] == "/tmp/output"
        assert result["sink"]["dry_run"] is True

    def test_packs_runtime_section(self) -> None:
        """Flat runtime fields are packed into runtime section."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "pagination": {"limit": 50},
            "client": {"timeout_sec": 30},
        }
        result = ConfigMigrator.migrate(data)
        assert result["runtime"]["pagination"] == {"limit": 50}
        assert result["runtime"]["client"] == {"timeout_sec": 30}

    def test_packs_observability_section(self) -> None:
        """Flat observability fields are packed into observability section."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "logging": {"level": "DEBUG"},
            "metrics": {"enabled": False},
        }
        result = ConfigMigrator.migrate(data)
        assert result["observability"]["logging"] == {"level": "DEBUG"}
        assert result["observability"]["metrics"] == {"enabled": False}

    def test_packs_quality_section(self) -> None:
        """Flat quality fields are packed into quality section."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "hashing": {"algorithm": "sha256"},
            "normalization": {"id_fields": ["id"]},
        }
        result = ConfigMigrator.migrate(data)
        assert result["quality"]["hashing"] == {"algorithm": "sha256"}
        assert result["quality"]["normalization"] == {"id_fields": ["id"]}

    def test_packs_features_section(self) -> None:
        """Flat feature fields are packed into features section."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "interface_features": {"rest_interface_enabled": True},
        }
        result = ConfigMigrator.migrate(data)
        assert result["features"]["interface_features"] == {
            "rest_interface_enabled": True
        }

    def test_migrates_csv_options_to_source(self) -> None:
        """csv_options at root is moved to source.csv."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "csv_options": {"delimiter": ";"},
        }
        result = ConfigMigrator.migrate(data)
        assert result["source"]["csv"] == {"delimiter": ";"}

    def test_extracts_stages_from_pipeline_dict(self) -> None:
        """stages are extracted from pipeline dict."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "pipeline": {"extract": True, "transform": True, "load": False},
        }
        result = ConfigMigrator.migrate(data)
        assert result["stages"]["extract"] is True
        assert result["stages"]["transform"] is True
        assert result["stages"]["load"] is False
        assert "pipeline" not in result

    def test_extracts_primary_key_from_pipeline_to_identity(self) -> None:
        """primary_key in pipeline dict is moved to identity."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "pipeline": {"primary_key": "molecule_chembl_id"},
        }
        result = ConfigMigrator.migrate(data)
        assert result["identity"]["primary_key"] == ["molecule_chembl_id"]

    def test_coerces_primary_key_string_to_list(self) -> None:
        """String primary_key is coerced to list."""
        data = {
            "id": "test",
            "provider": "dummy",
            "entity": "test",
            "primary_key": "id",
        }
        result = ConfigMigrator.migrate(data)
        assert result["identity"]["primary_key"] == ["id"]


class TestLegacyClientKeyMigration:
    """Tests for legacy client config key migration."""

    def test_migrates_timeout_to_timeout_sec(self) -> None:
        """timeout in client is renamed to timeout_sec."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "runtime": {"client": {"timeout": 30}},
        }
        result = ConfigMigrator.migrate(data)
        assert result["runtime"]["client"]["timeout_sec"] == 30
        assert "timeout" not in result["runtime"]["client"]

    def test_migrates_rate_limit_to_rate_limit_per_sec(self) -> None:
        """rate_limit in client is renamed to rate_limit_per_sec."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "runtime": {"client": {"rate_limit": 5}},
        }
        result = ConfigMigrator.migrate(data)
        assert result["runtime"]["client"]["rate_limit_per_sec"] == 5
        assert "rate_limit" not in result["runtime"]["client"]

    def test_migrates_backoff_to_backoff_factor(self) -> None:
        """backoff in client is renamed to backoff_factor."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "runtime": {"client": {"backoff": 2.0}},
        }
        result = ConfigMigrator.migrate(data)
        assert result["runtime"]["client"]["backoff_factor"] == 2.0
        assert "backoff" not in result["runtime"]["client"]

    def test_preserves_new_key_if_both_present(self) -> None:
        """New key is preserved if both old and new are present."""
        data = {
            "identity": {"provider": "dummy", "entity": "test", "pipeline_id": "test"},
            "runtime": {"client": {"timeout": 30, "timeout_sec": 60}},
        }
        result = ConfigMigrator.migrate(data)
        assert result["runtime"]["client"]["timeout_sec"] == 60
        assert "timeout" not in result["runtime"]["client"]


class TestIdempotency:
    """Tests that migration is idempotent."""

    def test_migration_is_idempotent(self) -> None:
        """Running migration twice produces same result."""
        data = {
            "entity": "test",
            "provider": "dummy",
            "input_mode": "csv",
            "output_path": "/tmp/output",
            "logging": {"level": "DEBUG"},
        }
        result1 = ConfigMigrator.migrate(data)
        result2 = ConfigMigrator.migrate(deepcopy(result1))
        assert result1 == result2

    def test_already_migrated_v2_unchanged(self) -> None:
        """v2 config is not modified."""
        data = {
            "identity": {"pipeline_id": "test", "provider": "dummy", "entity": "test"},
            "source": {"input_mode": "csv"},
            "sink": {"output_path": "/tmp/output"},
            "runtime": {"pagination": {"limit": 100}},
        }
        original = deepcopy(data)
        result = ConfigMigrator.migrate(data)
        assert result == original

    def test_v2_does_not_emit_deprecation_warning(self) -> None:
        """v2 format does not trigger deprecation warning."""
        data = {
            "identity": {"pipeline_id": "test", "provider": "dummy", "entity": "test"},
        }
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            ConfigMigrator.migrate(data)
            assert len(w) == 0


class TestEdgeCases:
    """Tests for edge cases."""

    def test_handles_non_dict_data(self) -> None:
        """Non-dict data is returned unchanged."""
        assert ConfigMigrator.migrate("not a dict") == "not a dict"  # type: ignore[arg-type]
        assert ConfigMigrator.migrate(None) is None  # type: ignore[arg-type]
        assert ConfigMigrator.migrate([1, 2, 3]) == [1, 2, 3]  # type: ignore[arg-type]

    def test_handles_empty_dict(self) -> None:
        """Empty dict is handled gracefully."""
        result = ConfigMigrator.migrate({})
        assert result == {}

    def test_preserves_existing_identity_section(self) -> None:
        """Existing identity section is not overwritten."""
        data = {
            "identity": {"pipeline_id": "existing", "provider": "dummy", "entity": "e"},
            "id": "should-be-ignored",
            "provider": "should-be-ignored",
        }
        result = ConfigMigrator.migrate(data)
        assert result["identity"]["pipeline_id"] == "existing"
        assert result["identity"]["provider"] == "dummy"
        # Flat fields should still exist (not packed since identity exists)
        assert "id" in result
        assert "provider" in result

    def test_preserves_existing_source_section(self) -> None:
        """Existing source section is not overwritten."""
        data = {
            "identity": {"pipeline_id": "test", "provider": "dummy", "entity": "test"},
            "source": {"input_mode": "existing"},
            "input_mode": "should-be-ignored",
        }
        result = ConfigMigrator.migrate(data)
        assert result["source"]["input_mode"] == "existing"

    def test_handles_sources_with_single_provider(self) -> None:
        """Single provider in sources is extracted correctly."""
        data = {
            "entity": "test",
            "sources": {
                "chembl": {"base_url": "https://example.com", "batch_size": 10}
            },
        }
        result = ConfigMigrator.migrate(data)
        assert result["provider_config"]["base_url"] == "https://example.com"
        assert result["source"]["batch_size"] == 10

    def test_handles_null_primary_key(self) -> None:
        """Null primary_key is coerced to empty list."""
        data = {
            "id": "test",
            "provider": "dummy",
            "entity": "test",
            "primary_key": None,
        }
        result = ConfigMigrator.migrate(data)
        assert result["identity"]["primary_key"] == []

    def test_handles_list_primary_key(self) -> None:
        """List primary_key is preserved."""
        data = {
            "id": "test",
            "provider": "dummy",
            "entity": "test",
            "primary_key": ["id", "version"],
        }
        result = ConfigMigrator.migrate(data)
        assert result["identity"]["primary_key"] == ["id", "version"]
