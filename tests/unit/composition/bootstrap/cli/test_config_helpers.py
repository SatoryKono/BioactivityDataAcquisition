"""Tests for CLI bootstrap config helpers."""

from __future__ import annotations

import pytest

from bioetl.composition.bootstrap.cli.config_helpers import get_pipeline_yaml_for_dq

pytestmark = pytest.mark.unit


class _ModelDumpConfig:
    def model_dump(self) -> dict[str, object]:
        return {"provider": "chembl", "entity": "activity"}


def test_get_pipeline_yaml_for_dq_uses_model_dump_when_available() -> None:
    payload = get_pipeline_yaml_for_dq(
        "chembl_activity",
        pipeline_config_loader=lambda _: _ModelDumpConfig(),
    )

    assert payload == {"provider": "chembl", "entity": "activity"}


def test_get_pipeline_yaml_for_dq_copies_mapping_payload() -> None:
    source = {"provider": "pubmed", "entity": "publication"}

    payload = get_pipeline_yaml_for_dq(
        "pubmed_publication",
        pipeline_config_loader=lambda _: source,
    )

    assert payload == source
    assert payload is not source


def test_get_pipeline_yaml_for_dq_rejects_unsupported_config_types() -> None:
    with pytest.raises(
        TypeError,
        match="Pipeline YAML config must provide model_dump\\(\\) or be a mapping",
    ):
        get_pipeline_yaml_for_dq(
            "invalid",
            pipeline_config_loader=lambda _: object(),
        )
