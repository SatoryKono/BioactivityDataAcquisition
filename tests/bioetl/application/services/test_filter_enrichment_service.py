"""Tests for FilterEnrichmentService."""

from unittest.mock import Mock

from bioetl.application.services import FilterEnrichmentService, NullFilterEnricher
from bioetl.domain.ports.providers import DefaultFieldProviderABC


class TestFilterEnrichmentService:
    """Tests for FilterEnrichmentService."""

    def test_enrich_filters_with_provider(self):
        """Test that fields are added when provider returns fields."""
        mock_provider = Mock(spec=DefaultFieldProviderABC)
        mock_provider.get_default_fields.return_value = ["field1", "field2", "field3"]

        enricher = FilterEnrichmentService(mock_provider)
        result = enricher.enrich_filters("assay", {"limit": 100})

        assert result == {"limit": 100, "fields": "field1,field2,field3"}
        mock_provider.get_default_fields.assert_called_once_with("assay")

    def test_enrich_filters_skips_if_fields_present(self):
        """Test that existing fields are not overwritten."""
        mock_provider = Mock(spec=DefaultFieldProviderABC)
        mock_provider.get_default_fields.return_value = ["field1", "field2"]

        enricher = FilterEnrichmentService(mock_provider)
        result = enricher.enrich_filters("assay", {"fields": "custom_field"})

        assert result == {"fields": "custom_field"}
        mock_provider.get_default_fields.assert_not_called()

    def test_enrich_filters_without_provider(self):
        """Test that filters pass through when no provider is set."""
        enricher = FilterEnrichmentService(field_provider=None)
        original = {"limit": 50, "offset": 10}
        result = enricher.enrich_filters("activity", original)

        assert result == {"limit": 50, "offset": 10}
        assert result is original  # Same object returned

    def test_enrich_filters_empty_fields_from_provider(self):
        """Test that no fields key is added when provider returns empty list."""
        mock_provider = Mock(spec=DefaultFieldProviderABC)
        mock_provider.get_default_fields.return_value = []

        enricher = FilterEnrichmentService(mock_provider)
        result = enricher.enrich_filters("unknown_entity", {"limit": 100})

        assert result == {"limit": 100}
        assert "fields" not in result

    def test_enrich_filters_returns_new_dict(self):
        """Test that original dict is not mutated."""
        mock_provider = Mock(spec=DefaultFieldProviderABC)
        mock_provider.get_default_fields.return_value = ["field1"]

        enricher = FilterEnrichmentService(mock_provider)
        original = {"limit": 100}
        result = enricher.enrich_filters("assay", original)

        # Original should be unchanged
        assert original == {"limit": 100}
        # Result should have fields
        assert result == {"limit": 100, "fields": "field1"}
        assert result is not original


class TestNullFilterEnricher:
    """Tests for NullFilterEnricher."""

    def test_passes_through_unchanged(self):
        """Test that filters pass through unchanged."""
        enricher = NullFilterEnricher()
        filters = {"limit": 100, "offset": 50, "fields": "custom"}
        result = enricher.enrich_filters("assay", filters)

        assert result is filters

    def test_handles_empty_filters(self):
        """Test that empty filters work correctly."""
        enricher = NullFilterEnricher()
        result = enricher.enrich_filters("activity", {})

        assert result == {}

    def test_protocol_compliance(self):
        """Test that NullFilterEnricher satisfies FilterEnricherABC protocol."""
        from bioetl.domain.ports.filters import FilterEnricherABC

        enricher = NullFilterEnricher()
        # Protocol check via isinstance with runtime_checkable
        assert isinstance(enricher, FilterEnricherABC)
