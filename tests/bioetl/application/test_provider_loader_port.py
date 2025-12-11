from __future__ import annotations

import pytest

from bioetl.domain.configs import DummyProviderConfig, HttpClientConfig, PipelineConfig

# Provider registry module was removed
# from bioetl.domain.provider_registry import InMemoryProviderRegistry


def _build_dummy_config() -> PipelineConfig:
    return PipelineConfig(
        id="dummy.pipeline",
        provider="dummy",
        entity="dummy",
        input_mode="auto_detect",
        input_path=None,
        output_path="out",
        batch_size=1,
        provider_config=DummyProviderConfig(
            base_url="https://example.com",
            client=HttpClientConfig(
                timeout_sec=1,
                max_retries=0,
                rate_limit_per_sec=1.0,
            ),
        ),
    )


@pytest.mark.skip(reason="Provider registry module was removed")
def test_orchestrator_uses_provider_loader_when_flag_enabled() -> None:
    """Legacy provider loader test disabled until registry returns."""
