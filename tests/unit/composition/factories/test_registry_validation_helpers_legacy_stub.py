"""ARCH-CR-02: legacy composite stub detection is path-based only."""

from __future__ import annotations

from pathlib import Path

from bioetl.composition.factories.pipeline_support.registry_validation_helpers import (
    _is_legacy_composite_entity_stub,
)


def test_legacy_stub_detected_by_parent_directory_only(tmp_path: Path) -> None:
    composite_dir = tmp_path / "entities" / "composite"
    composite_dir.mkdir(parents=True)
    stub = composite_dir / "activity.yaml"
    # Provider field intentionally missing/misleading must not matter.
    stub.write_text("entity: activity\nprovider: chembl\n", encoding="utf-8")
    assert _is_legacy_composite_entity_stub(stub) is True


def test_non_legacy_provider_composite_yaml_is_not_stub(tmp_path: Path) -> None:
    chembl_dir = tmp_path / "entities" / "chembl"
    chembl_dir.mkdir(parents=True)
    impostor = chembl_dir / "activity.yaml"
    impostor.write_text("entity: activity\nprovider: composite\n", encoding="utf-8")
    assert _is_legacy_composite_entity_stub(impostor) is False
