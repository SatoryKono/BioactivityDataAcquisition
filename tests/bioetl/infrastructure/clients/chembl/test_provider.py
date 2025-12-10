from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from bioetl.domain.configs import ChemblSourceConfig, ClientConfig
from bioetl.domain.transform.contracts import NormalizationServiceABC
from bioetl.infrastructure.clients.chembl.provider import (
    ChemblProviderComponentsFactory,
)


class _NormalizationServiceStub(NormalizationServiceABC):
    def normalize(self, df):
        return df

    def normalize_record(self, record):
        return record

    def ensure_numeric_columns(self, df):
        return df

    def apply_normalize(self, raw):
        return {"raw": raw}

    def apply_normalize_fields(self, df):
        return df

    def apply_normalize_dataframe(self, df):
        return df

    def apply_normalize_batch(self, df):
        return df

    def apply_normalize_series(self, series, field_cfg):
        return series


@pytest.fixture()
def chembl_config() -> ChemblSourceConfig:
    return ChemblSourceConfig(
        base_url="https://example.com/api",
        client=ClientConfig(
            timeout_sec=30,
            max_retries=1,
            rate_limit_per_sec=1.0,
        ),
    )


def test_create_normalization_service_uses_factory(monkeypatch, chembl_config):
    components = ChemblProviderComponentsFactory()
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
    components = ChemblProviderComponentsFactory()

    with pytest.raises(ValueError):
        components.create_normalization_service(chembl_config)
