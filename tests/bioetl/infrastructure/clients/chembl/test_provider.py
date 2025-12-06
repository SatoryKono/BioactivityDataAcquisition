from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.domain.transform.contracts import NormalizationServiceABC
from bioetl.infrastructure.clients.chembl.provider import ChemblProviderComponents
from bioetl.infrastructure.config.models import ChemblSourceConfig


class _NormalizationServiceStub(NormalizationServiceABC):
    def normalize(self, raw):
        return {"raw": raw}

    def normalize_fields(self, df):
        return df

    def normalize_dataframe(self, df):
        return df

    def normalize_batch(self, df):
        return df

    def normalize_series(self, series, field_cfg):
        return series


@pytest.fixture()
def chembl_config() -> ChemblSourceConfig:
    return ChemblSourceConfig(
        base_url="https://example.com/api",
        timeout_sec=30,
        max_retries=1,
        rate_limit_per_sec=1.0,
    )


def test_create_normalization_service_uses_factory(monkeypatch, chembl_config):
    components = ChemblProviderComponents()
    pipeline_config = SimpleNamespace(normalization={}, fields=[])
    stub_service = _NormalizationServiceStub()

    factory = MagicMock(return_value=stub_service)
    monkeypatch.setattr(
        "bioetl.infrastructure.clients.chembl.provider.default_normalization_service",
        factory,
    )

    result = components.create_normalization_service(
        chembl_config, pipeline_config=pipeline_config
    )

    assert result is stub_service
    factory.assert_called_once_with(pipeline_config)


def test_create_normalization_service_requires_pipeline_config(chembl_config):
    components = ChemblProviderComponents()

    with pytest.raises(ValueError):
        components.create_normalization_service(chembl_config)
