"""Unit tests for lightweight composition config catalog helpers."""

from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.composition.config_catalog import list_configured_pipeline_names

pytestmark = pytest.mark.unit


def test_list_configured_pipeline_names_reads_entity_config_tree(
    tmp_path: Path,
) -> None:
    configs_root = tmp_path / "configs"
    (configs_root / "entities" / "chembl").mkdir(parents=True)
    (configs_root / "entities" / "composite").mkdir(parents=True)
    (configs_root / "entities" / "pubchem").mkdir(parents=True)
    (configs_root / "entities" / "chembl" / "activity.yaml").write_text(
        "provider: chembl\nentity_type: activity\n",
        encoding="utf-8",
    )
    (configs_root / "entities" / "pubchem" / "compound.yaml").write_text(
        "provider: pubchem\nentity_type: compound\n",
        encoding="utf-8",
    )
    (configs_root / "entities" / "composite" / "activity.yaml").write_text(
        "provider: composite\nentity_type: activity\n",
        encoding="utf-8",
    )

    assert list_configured_pipeline_names(configs_root=configs_root) == [
        "chembl_activity",
        "pubchem_compound",
    ]


def test_list_configured_pipeline_names_missing_root_is_empty(
    tmp_path: Path,
) -> None:
    assert list_configured_pipeline_names(configs_root=tmp_path / "configs") == []
