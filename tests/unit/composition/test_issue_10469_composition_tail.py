"""Behavioral coverage for residual composition guard branches."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import polars as pl
import pytest

from bioetl.composition.bootstrap.runtime._dependency_runner_support import (
    resolve_dependency_runner_limit,
)
from bioetl.composition.factories.pipeline._factory_method_runtime_support import (
    create_pipeline_instance_from_request,
)
from bioetl.composition.factories.pipeline._factory_method_types import (
    _PipelineFactoryContext,
)
from bioetl.composition.factories.pipeline.transformer_builder import TransformerBuilder
from bioetl.composition.factories.storage._helpers import (
    _has_provider_entity_suffix,
)
from bioetl.composition.runtime_builders import (
    _effective_config_runtime_snapshot_support as snapshot_support,
)
from bioetl.composition.runtime_builders.run_manifest_builder import (
    _maybe_create_ledger_service,
)


pytestmark = pytest.mark.unit


def test_dependency_runner_without_filters_has_no_implicit_limit() -> None:
    keys = pl.DataFrame({"id": ["a", "b"]})

    assert (
        resolve_dependency_runner_limit(
            keys=keys,
            filter_ids=None,
            multi_filter_ids=None,
        )
        is None
    )


def test_single_segment_storage_path_has_no_provider_entity_suffix() -> None:
    assert not _has_provider_entity_suffix(
        Path("silver"),
        provider="chembl",
        entity_type="activity",
    )


def test_blank_optional_setting_is_not_hashed() -> None:
    assert snapshot_support._hashed_optional_text("  ") is None


def test_disabled_run_ledger_does_not_construct_service() -> None:
    assert (
        _maybe_create_ledger_service(
            ledger_enabled=False,
            inputs=SimpleNamespace(),
            ctx=SimpleNamespace(),
        )
        is None
    )


def test_transformer_builder_skips_policy_when_entity_is_unknown() -> None:
    loader = Mock(side_effect=AssertionError("policy loader must not be called"))
    builder = TransformerBuilder(
        provider="chembl",
        pipeline_name="chembl",
        entity_type_extractor=lambda _pipeline: None,
        contract_policy_loader=loader,
    )

    assert builder._load_contract_policy(None) is None
    loader.assert_not_called()


@pytest.mark.parametrize(
    ("pipeline_class", "provider"),
    [(None, "chembl"), (object, None)],
)
def test_pipeline_creation_requires_class_and_provider(
    pipeline_class: type[object] | None,
    provider: str | None,
) -> None:
    context = _PipelineFactoryContext(
        pipeline_name="chembl_activity",
        create_data_source_fn=Mock(),
        pipeline_class=pipeline_class,
        provider=provider,
    )

    with pytest.raises(AssertionError, match="pipeline_class and provider"):
        create_pipeline_instance_from_request(
            factory_context=context,
            request=SimpleNamespace(),
            create_pipeline_with_services_fn=Mock(),
            apply_optional_control_plane_kwargs_fn=Mock(),
        )
