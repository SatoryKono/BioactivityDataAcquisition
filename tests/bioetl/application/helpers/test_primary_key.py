"""Unit tests for primary key resolution helper."""

from bioetl.application.helpers import (
    resolve_primary_key,
    resolve_primary_key_with_filter,
)
from bioetl.domain.configs import (
    DataFlowConfig,
    DataSinkConfig,
    DataSourceConfig,
    PipelineConfig,
    PipelineIdentityConfig,
)


def _make_config(
    *,
    entity: str = "activity",
    primary_key: str | list[str] | None = None,
) -> PipelineConfig:
    """Helper to create a minimal PipelineConfig for testing.

    Args:
        entity: Entity name.
        primary_key: Primary key - string or list of strings
            (will be converted to list).
    """
    # Convert string to list for new format
    pk_list: list[str] = []
    if primary_key is not None:
        if isinstance(primary_key, str):
            pk_list = [primary_key]
        else:
            pk_list = list(primary_key)

    identity = PipelineIdentityConfig(
        pipeline_id=f"chembl.{entity}",
        provider="chembl",
        entity=entity,
        primary_key=pk_list,
    )
    data_flow = DataFlowConfig(
        source=DataSourceConfig(
            input_mode="auto_detect",
            input_path=None,
            batch_size=100,
        ),
        sink=DataSinkConfig(
            output_path="C:/tmp/out",
            dry_run=True,
        ),
    )
    return PipelineConfig(
        identity=identity,
        data_flow=data_flow,
    )


class TestResolvePrimaryKey:
    """Tests for resolve_primary_key function."""

    def test_explicit_primary_key_field(self) -> None:
        """Primary key from identity.primary_key takes precedence."""
        config = _make_config(entity="activity", primary_key="custom_pk")
        assert resolve_primary_key(config) == "custom_pk"

    def test_primary_key_list_uses_first_element(self) -> None:
        """First element of primary_key list is used."""
        config = _make_config(entity="activity", primary_key=["pk1", "pk2"])
        assert resolve_primary_key(config) == "pk1"

    def test_entity_based_default(self) -> None:
        """Falls back to {entity_name}_id convention."""
        config = _make_config(entity="assay", primary_key=None)
        assert resolve_primary_key(config) == "assay_id"

    def test_empty_primary_key_falls_back_to_entity(self) -> None:
        """Empty primary_key list falls back to entity convention."""
        config = _make_config(entity="molecule", primary_key=[])
        assert resolve_primary_key(config) == "molecule_id"

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

    def test_none_primary_key_uses_entity_default(self) -> None:
        """None primary_key falls back to entity_id convention."""
        config = _make_config(entity="activity", primary_key=None)
        assert resolve_primary_key(config) == "activity_id"

    def test_empty_string_primary_key_uses_fallback(self) -> None:
        """Empty string primary_key triggers fallback logic."""
        config = _make_config(entity="activity", primary_key="")
        # Empty string is filtered out in list, so entity_name_id should be used
        assert resolve_primary_key(config) == "activity_id"
