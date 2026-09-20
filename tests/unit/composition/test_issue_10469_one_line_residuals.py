"""Behavior tests for one-line composition coverage residuals in #10469."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from bioetl.composition.bootstrap.runtime._composite_plan_runtime_support import (
    load_runtime_composite_config_impl,
)
from bioetl.composition.bootstrap.runtime.composite_support_runtime_context import (
    resolve_composite_support_runtime_context,
)
from bioetl.composition.factories.pipeline.registry_validation import (
    validate_registry_manifest,
)
from bioetl.composition.providers.registration_bio import _create_chembl_data_source


pytestmark = pytest.mark.unit


def test_runtime_composite_config_translates_validation_error(tmp_path: Path) -> None:
    validation_error = ValidationError.from_exception_data("CompositeConfig", [])
    with patch(
        "bioetl.composition.bootstrap.runtime._composite_plan_runtime_support."
        "_load_composite_config_impl",
        side_effect=validation_error,
    ):
        with pytest.raises(ValueError, match="Invalid composite config 'broken'"):
            load_runtime_composite_config_impl(
                "broken",
                resolve_config_path_fn=lambda _name: tmp_path / "broken.yaml",
                validate_payload=MagicMock(),
            )


def test_composite_runtime_context_builds_enabled_cross_validator(
    tmp_path: Path,
) -> None:
    config = SimpleNamespace(
        name="composite",
        cross_validation=SimpleNamespace(enabled=True),
    )
    infra = SimpleNamespace(
        logger=MagicMock(),
        settings=SimpleNamespace(data_dir=tmp_path),
    )
    bundle = SimpleNamespace(manifest_id="manifest-1")
    validator = object()
    with (
        patch(
            "bioetl.composition.bootstrap.runtime."
            "composite_support_runtime_context.build_composite_control_plane_bundle",
            return_value=bundle,
        ),
        patch(
            "bioetl.composition.bootstrap.runtime."
            "composite_support_runtime_context.bind_manifest_logger",
            return_value=infra.logger,
        ),
        patch(
            "bioetl.composition.bootstrap.runtime."
            "composite_support_runtime_context.DeltaReader",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.bootstrap.runtime."
            "composite_support_runtime_context.EnrichmentCrossValidator",
            return_value=validator,
        ),
    ):
        context = resolve_composite_support_runtime_context(
            config=config,
            runtime=MagicMock(),
            infra_context=infra,
            load_field_group_registry=lambda _name, _logger: None,
        )

    assert context.cross_validator is validator


def test_registry_validation_defaults_to_canonical_registry(tmp_path: Path) -> None:
    with (
        patch(
            "bioetl.composition.factories.pipeline.registry_validation."
            "resolve_configs_root",
            return_value=tmp_path / "configs",
        ),
        patch(
            "bioetl.composition.factories.pipeline.registry_validation.PIPELINE_CONFIGS",
            (),
        ),
        patch(
            "bioetl.composition.factories.pipeline.registry_validation."
            "_iter_entity_files",
            return_value=(),
        ),
    ):
        assert validate_registry_manifest(configs_root=tmp_path) == []


def test_chembl_subcellular_fraction_uses_derived_data_source() -> None:
    base_adapter = object()
    derived_adapter = object()
    support = MagicMock()
    support.create_http_client.return_value = object()
    support.create_adapter.return_value = base_adapter
    pipeline_config = SimpleNamespace(
        entity_type="subcellular_fraction",
        extraction_params={},
    )
    settings = SimpleNamespace(gold_path="gold")
    with (
        patch(
            "bioetl.composition.providers.registration_bio."
            "resolve_provider_assembly_support",
            return_value=support,
        ),
        patch(
            "bioetl.composition.providers.registration_bio._get_adapter_config",
            return_value=MagicMock(),
        ),
        patch(
            "bioetl.composition.providers.registration_bio."
            "SubcellularFractionDataSource",
            return_value=derived_adapter,
        ) as derived,
        patch(
            "bioetl.composition.providers.registration_bio._wrap_with_filter",
            side_effect=lambda adapter, *_args: adapter,
        ),
    ):
        result = _create_chembl_data_source(
            settings,
            pipeline_config,
            MagicMock(),
            assembly_support=support,
        )

    assert result is derived_adapter
    derived.assert_called_once_with(base_adapter)
