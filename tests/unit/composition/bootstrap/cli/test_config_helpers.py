"""Unit tests for CLI configuration bootstrap helpers."""

from __future__ import annotations

from collections.abc import Mapping

import pytest

from bioetl.composition.bootstrap.cli.config_helpers import get_pipeline_yaml_for_dq


@pytest.mark.unit
def test_get_pipeline_yaml_for_dq_prefers_model_dump() -> None:
    """Model-backed configs should be converted via model_dump()."""

    class _Config:
        def model_dump(self) -> dict[str, object]:
            return {"provider": "chembl", "version": 1}

    payload = {"provider": "chembl", "version": 1}
    assert get_pipeline_yaml_for_dq("chembl_activity", pipeline_config_loader=lambda _: _Config()) == payload


@pytest.mark.unit
def test_get_pipeline_yaml_for_dq_accepts_mapping_payload() -> None:
    """Mapping configs should be copied into a dict result."""

    payload = {"provider": "uniprot", "entity_type": "protein"}

    assert get_pipeline_yaml_for_dq(
        "uniprot_protein",
        pipeline_config_loader=lambda _: payload,
    ) == dict(payload)


@pytest.mark.unit
def test_get_pipeline_yaml_for_dq_rejects_non_mapping_payload() -> None:
    """Non-mapping and non-model configs must fail loudly."""

    with pytest.raises(TypeError, match="Pipeline YAML config must provide model_dump"):
        get_pipeline_yaml_for_dq("pubchem_compound", pipeline_config_loader=lambda _: object())


@pytest.mark.unit
def test_get_pipeline_yaml_for_dq_treats_empty_mapping_as_mapping() -> None:
    """Empty mappings should be accepted and returned as dict copy."""

    empty: Mapping[str, object] = {}

    assert get_pipeline_yaml_for_dq("pubmed_publication", pipeline_config_loader=lambda _: empty) == {}
