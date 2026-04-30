"""Unit tests for transformer dependency assembly helpers."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from bioetl.composition.factories.pipeline.transformer_dependencies import (
    build_transformer_dependencies,
)
from bioetl.domain.ports.noop import (
    NoOpMetrics,
    NoOpPiiHasher,
    NoOpTracing,
)
from bioetl.domain.services import EntityIdentityGenerator
from bioetl.domain.services.data_normalization_service import (
    DefaultDataNormalizer,
)


@pytest.mark.unit
class TestBuildTransformerDependencies:
    """Behavioural tests for transformer dependency assembly."""

    def test_preserves_explicit_collaborators(self) -> None:
        """Assembly should forward injected collaborators without replacement."""
        tracer = MagicMock(name="tracer")
        metrics = MagicMock(name="metrics")
        identity_service = MagicMock(name="identity_service")
        pii_hasher = MagicMock(name="pii_hasher")
        data_normalizer = MagicMock(name="data_normalizer")
        contract_policy = MagicMock(name="contract_policy")

        result = build_transformer_dependencies(
            provider="chembl",
            entity_type="activity",
            tracer=tracer,
            metrics=metrics,
            identity_service=identity_service,
            pii_hasher=pii_hasher,
            data_normalizer=data_normalizer,
            contract_policy=contract_policy,
        )

        assert result.tracer is tracer
        assert result.metrics is metrics
        assert result.identity_service is identity_service
        assert result.pii_hasher is pii_hasher
        assert result.data_normalizer is data_normalizer
        assert result.contract_policy is contract_policy

    def test_builds_default_collaborators_and_loader_fallback(self) -> None:
        """Assembly should create safe defaults when no collaborators are injected."""
        result = build_transformer_dependencies(
            provider="crossref",
            entity_type="publication",
            content_hash_include_fields=("doi", "title"),
            content_hash_exclude_fields=("tmp",),
            contract_policy_loader=MagicMock(side_effect=ValueError("missing policy")),
        )

        assert isinstance(result.tracer, NoOpTracing)
        assert isinstance(result.metrics, NoOpMetrics)
        assert isinstance(result.identity_service, EntityIdentityGenerator)
        assert result.identity_service._content_hash_include_fields == {"doi", "title"}
        assert result.identity_service._content_hash_exclude_fields == {"tmp"}
        assert isinstance(result.pii_hasher, NoOpPiiHasher)
        assert isinstance(result.data_normalizer, DefaultDataNormalizer)
        assert result.contract_policy.primary_key == ["entity_id"]
