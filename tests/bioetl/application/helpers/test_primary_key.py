"""Unit tests for primary key resolution helper."""

from bioetl.application.helpers import (
    resolve_primary_key,
    resolve_primary_key_with_filter,
)
from bioetl.infrastructure.config.models import (
    ChemblSourceConfig,
    ClientConfig,
    PipelineConfig,
)


def _make_config(
    *,
    entity: str = "activity",
    primary_key: str | None = None,
    pipeline: dict | None = None,
) -> PipelineConfig:
    """Helper to create a minimal PipelineConfig for testing."""
    return PipelineConfig(
        id=f"chembl.{entity}",
        provider="chembl",
        entity=entity,
        primary_key=primary_key,
        pipeline=pipeline or {},
        input_mode="auto_detect",
        input_path=None,
        output_path="/tmp/out",
        batch_size=100,
        provider_config=ChemblSourceConfig(
            base_url="https://www.ebi.ac.uk/chembl/api/data",
            client=ClientConfig(
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        ),
    )


class TestResolvePrimaryKey:
    """Tests for resolve_primary_key function."""

    def test_explicit_primary_key_field(self) -> None:
        """Primary key from config.primary_key takes precedence."""
        config = _make_config(entity="activity", primary_key="custom_pk")
        assert resolve_primary_key(config) == "custom_pk"

    def test_primary_key_from_pipeline_dict(self) -> None:
        """Fallback to pipeline dict when primary_key field is not set."""
        config = _make_config(
            entity="activity",
            primary_key=None,
            pipeline={"primary_key": "legacy_pk"},
        )
        assert resolve_primary_key(config) == "legacy_pk"

    def test_explicit_field_wins_over_pipeline_dict(self) -> None:
        """Explicit primary_key field takes precedence over pipeline dict."""
        config = _make_config(
            entity="activity",
            primary_key="explicit_pk",
            pipeline={"primary_key": "legacy_pk"},
        )
        assert resolve_primary_key(config) == "explicit_pk"

    def test_entity_based_default(self) -> None:
        """Falls back to {entity_name}_id convention."""
        config = _make_config(entity="assay", primary_key=None)
        assert resolve_primary_key(config) == "assay_id"

    def test_fallback_parameter_used_when_needed(self) -> None:
        """Fallback parameter is used if resolution fails."""
        # This case should not happen in practice since entity_name_id
        # is always generated, but test the fallback logic anyway.
        # We test that fallback doesn't override valid resolution.
        config = _make_config(entity="molecule", primary_key=None)
        result = resolve_primary_key(config, fallback="fallback_id")
        # entity_name_id should be used, not fallback
        assert result == "molecule_id"


class TestResolvePrimaryKeyWithFilter:
    """Tests for resolve_primary_key_with_filter function."""

    def test_returns_tuple(self) -> None:
        """Function returns (pk, filter_key) tuple."""
        config = _make_config(entity="target", primary_key="target_chembl_id")
        pk, filter_key = resolve_primary_key_with_filter(config)
        assert pk == "target_chembl_id"
        assert filter_key == "target_chembl_id__in"

    def test_filter_key_suffix(self) -> None:
        """Filter key is always pk + '__in'."""
        config = _make_config(entity="activity", primary_key=None)
        pk, filter_key = resolve_primary_key_with_filter(config)
        assert filter_key == f"{pk}__in"

    def test_with_fallback(self) -> None:
        """Fallback parameter is passed through."""
        config = _make_config(entity="publication", primary_key=None)
        pk, filter_key = resolve_primary_key_with_filter(config, fallback="doc_id")
        # Should use entity_name_id, not fallback
        assert pk == "publication_id"
        assert filter_key == "publication_id__in"


class TestEdgeCases:
    """Edge case tests for primary key resolution."""

    def test_empty_pipeline_dict(self) -> None:
        """Empty pipeline dict does not cause issues."""
        config = _make_config(entity="activity", primary_key=None, pipeline={})
        assert resolve_primary_key(config) == "activity_id"

    def test_pipeline_with_other_keys(self) -> None:
        """Other keys in pipeline dict are ignored."""
        config = _make_config(
            entity="activity",
            primary_key=None,
            pipeline={"some_key": "value", "another": 123},
        )
        assert resolve_primary_key(config) == "activity_id"

    def test_empty_string_primary_key_uses_fallback(self) -> None:
        """Empty string primary_key triggers fallback logic."""
        config = _make_config(entity="activity", primary_key="")
        # Empty string is falsy, so entity_name_id should be used
        assert resolve_primary_key(config) == "activity_id"
