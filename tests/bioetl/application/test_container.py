from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from bioetl.application.container import PipelineContainer
from bioetl.application.pipelines.hooks_impl import (
    FailFastErrorPolicyImpl,
    LoggingPipelineHookImpl,
)
from bioetl.domain.provider_registry import (
    ProviderAlreadyRegisteredError,
    ProviderNotRegisteredError,
    list_providers,
    register_provider,
    reset_provider_registry,
    restore_provider_registry,
)
from bioetl.domain.providers import (
    ProviderComponents,
    ProviderDefinition,
    ProviderId,
)
from bioetl.infrastructure.clients.chembl.provider import register_chembl_provider
from bioetl.infrastructure.config import provider_registry_loader as config_provider_registry
from bioetl.infrastructure.config.models import (
    ChemblSourceConfig,
    DummyProviderConfig,
    PipelineConfig,
)

sys.modules.setdefault("tqdm", SimpleNamespace(tqdm=lambda *args, **kwargs: None))


class DummyComponents(ProviderComponents):
    def create_client(self, config: DummyProviderConfig) -> dict[str, str]:
        return {"provider": config.provider, "base_url": str(config.base_url)}

    def create_extraction_service(
        self,
        config: DummyProviderConfig,
        *,
        client: dict[str, str] | None = None,
    ) -> tuple[str, str]:
        resolved_client = client or self.create_client(config)
        return resolved_client["provider"], resolved_client["base_url"]


@pytest.fixture(autouse=True)
def _restore_registry() -> Any:
    snapshot = list_providers()
    yield
    restore_provider_registry(snapshot)
    config_provider_registry.clear_provider_registry_cache()


@pytest.fixture(autouse=True)
def _patch_provider_registry(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Any:
    """
    Point provider registry to a temp file that includes chembl and dummy.

    This ensures PipelineConfig validation (which reads configs/providers.yaml)
    accepts the dummy provider used in these tests.
    """

    providers_file = tmp_path / "providers.yaml"
    providers_file.write_text(
        (
            "providers:\n"
            "  - id: chembl\n"
            "    module: tests.dummy\n"
            "    factory: create_chembl\n"
            "    active: true\n"
            "  - id: dummy\n"
            "    module: tests.dummy\n"
            "    factory: create_dummy\n"
            "    active: true\n"
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        config_provider_registry, "DEFAULT_PROVIDERS_REGISTRY_PATH", providers_file
    )
    config_provider_registry.clear_provider_registry_cache()
    yield
    config_provider_registry.clear_provider_registry_cache()


def _register_dummy_provider(
    *,
    config_type: type[Any] = DummyProviderConfig,
) -> ProviderDefinition:
    definition = ProviderDefinition(
        id=ProviderId.DUMMY,
        config_type=config_type,
        components=DummyComponents(),
        description="Dummy provider for container tests",
    )
    try:
        register_provider(definition)
    except ProviderAlreadyRegisteredError:
        pass
    return definition


def _build_dummy_pipeline_config(
    provider_config: DummyProviderConfig,
) -> PipelineConfig:
    return PipelineConfig(
        id="dummy.entity",
        provider="dummy",
        entity="entity",
        input_mode="auto_detect",
        input_path=None,
        output_path="/tmp/out",
        batch_size=10,
        provider_config=provider_config,
    )


def test_get_extraction_service_for_registered_providers() -> None:
    reset_provider_registry()
    register_chembl_provider()
    _register_dummy_provider()

    chembl_container = PipelineContainer(
        PipelineConfig(
            id="chembl.activity",
            provider="chembl",
            entity="activity",
            input_mode="auto_detect",
            input_path=None,
            output_path="/tmp/out",
            batch_size=10,
            provider_config=ChemblSourceConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
            ),
        )
    )
    dummy_container = PipelineContainer(
        _build_dummy_pipeline_config(
            DummyProviderConfig(
                base_url="https://example.com",  # type: ignore[arg-type]
                timeout_sec=1,
                max_retries=0,
                rate_limit_per_sec=1.0,
            )
        )
    )

    chembl_service = chembl_container.get_extraction_service()
    dummy_service = dummy_container.get_extraction_service()

    from bioetl.infrastructure.clients.chembl.impl import ChemblExtractionServiceImpl

    assert isinstance(chembl_service, ChemblExtractionServiceImpl)
    assert dummy_service == ("dummy", "https://example.com/")


def test_unknown_provider_raises() -> None:
    reset_provider_registry()
    dummy_container = PipelineContainer(
        _build_dummy_pipeline_config(
            DummyProviderConfig(
                base_url="https://example.com",  # type: ignore[arg-type]
                timeout_sec=1,
                max_retries=0,
                rate_limit_per_sec=1.0,
            )
        )
    )

    with pytest.raises(ProviderNotRegisteredError):
        dummy_container.get_extraction_service()


def test_config_validation_error_is_propagated() -> None:
    with pytest.raises(ValidationError):
        PipelineConfig(
            id="chembl.activity",
            provider="chembl",
            entity="activity",
            input_mode="auto_detect",
            input_path=None,
            output_path="/tmp/out",
            batch_size=10,
            provider_config=ChemblSourceConfig(
                base_url="https://www.ebi.ac.uk/chembl/api/data",
                timeout_sec=30,
                max_retries=3,
                rate_limit_per_sec=10.0,
                max_url_length=0,
            ),
        )


def test_type_mismatch_raises_type_error() -> None:
    reset_provider_registry()
    _register_dummy_provider(config_type=ChemblSourceConfig)

    dummy_config = DummyProviderConfig(
        base_url="https://example.com",  # type: ignore[arg-type]
        timeout_sec=1,
        max_retries=0,
        rate_limit_per_sec=1.0,
    )
    container = PipelineContainer(_build_dummy_pipeline_config(dummy_config))

    with pytest.raises(TypeError):
        container.get_extraction_service()


def test_container_provides_hooks_and_error_policy() -> None:
    dummy_config = DummyProviderConfig(
        base_url="https://example.com",  # type: ignore[arg-type]
        timeout_sec=1,
        max_retries=0,
        rate_limit_per_sec=1.0,
    )
    container = PipelineContainer(_build_dummy_pipeline_config(dummy_config))

    logger = container.get_logger()
    hooks = container.get_hooks()
    policy = container.get_error_policy()

    assert hooks
    assert any(isinstance(hook, LoggingPipelineHookImpl) for hook in hooks)
    assert isinstance(policy, FailFastErrorPolicyImpl)
    hook_logger = next(
        hook._logger  # type: ignore[attr-defined]
        for hook in hooks
        if isinstance(hook, LoggingPipelineHookImpl)
    )
    assert hook_logger is logger


def test_hash_service_singleton_scope() -> None:
    dummy_config = DummyProviderConfig(
        base_url="https://example.com",  # type: ignore[arg-type]
        timeout_sec=1,
        max_retries=0,
        rate_limit_per_sec=1.0,
    )
    container = PipelineContainer(_build_dummy_pipeline_config(dummy_config))

    first_instance = container.get_hash_service()
    second_instance = container.get_hash_service()

    assert first_instance is second_instance


def test_hash_service_override_propagates_to_transformers() -> None:
    dummy_config = DummyProviderConfig(
        base_url="https://example.com",  # type: ignore[arg-type]
        timeout_sec=1,
        max_retries=0,
        rate_limit_per_sec=1.0,
    )
    custom_hash_service = MagicMock()
    container = PipelineContainer(
        _build_dummy_pipeline_config(dummy_config),
        hash_service=custom_hash_service,
    )

    post_transformer = container.get_post_transformer(version_provider=lambda: "v1")
    transformer_hashes = {
        transformer.__class__.__name__: getattr(transformer, "_hash_service", None)
        for transformer in post_transformer._transformers  # type: ignore[attr-defined] # noqa: E501
    }

    assert transformer_hashes
    assert all(
        service is custom_hash_service for service in transformer_hashes.values()
    )
