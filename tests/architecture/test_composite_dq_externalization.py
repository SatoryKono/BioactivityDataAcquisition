"""Architecture tests for ADR-027 composite DQ externalization."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest
import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
COMPOSITES_DIR = PROJECT_ROOT / "configs" / "composites"
COMPOSITE_QUALITY_DIR = PROJECT_ROOT / "configs" / "quality" / "entities" / "composite"

ALLOWED_INLINE_DQ_KEYS = frozenset({"dq_config_file", "enricher_overrides"})


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        return {}
    return data


def _externalized_composite_entities() -> tuple[str, ...]:
    """Discover composite entities that declare ``composite.dq_overrides``."""
    entities: list[str] = []
    for config_path in sorted(COMPOSITES_DIR.glob("*.yaml")):
        payload = _load_yaml(config_path)
        composite = payload.get("composite")
        if not isinstance(composite, dict):
            continue
        if isinstance(composite.get("dq_overrides"), dict):
            entities.append(config_path.stem)
    return tuple(entities)


EXTERNALIZED_COMPOSITE_ENTITIES = _externalized_composite_entities()


def _load_composite_dq_overrides(entity: str) -> dict[str, Any]:
    config_path = COMPOSITES_DIR / f"{entity}.yaml"
    data = _load_yaml(config_path)
    composite = data.get("composite")
    assert isinstance(composite, dict), f"Missing 'composite' section: {config_path}"
    dq_overrides = composite.get("dq_overrides")
    assert isinstance(dq_overrides, dict), f"Missing dq_overrides: {config_path}"
    return dq_overrides


class TestCompositeDQExternalization:
    """Enforce consistent DQ externalization for composite entities.

    The architecture intentionally keeps one external DQ file per composite
    entity. Rich validation content must live in the external per-entity file
    rather than collapsing back to threshold-only stubs.
    """

    def test_externalized_entity_list_is_not_empty(self) -> None:
        assert EXTERNALIZED_COMPOSITE_ENTITIES, (
            "No composite entities with dq_overrides found under configs/composites/"
        )

    @pytest.mark.parametrize("entity", EXTERNALIZED_COMPOSITE_ENTITIES)
    def test_composite_uses_standard_dq_config_pointer(self, entity: str) -> None:
        dq_overrides = _load_composite_dq_overrides(entity)
        expected = f"../quality/entities/composite/{entity}.yaml"
        assert dq_overrides.get("dq_config_file") == expected

        config_path = COMPOSITES_DIR / f"{entity}.yaml"
        resolved = (config_path.parent / expected).resolve()
        expected_path = (COMPOSITE_QUALITY_DIR / f"{entity}.yaml").resolve()

        assert resolved == expected_path
        assert resolved.exists(), f"Missing external DQ config for {entity}: {resolved}"

    @pytest.mark.parametrize("entity", EXTERNALIZED_COMPOSITE_ENTITIES)
    def test_composite_has_no_inline_field_validations(self, entity: str) -> None:
        dq_overrides = _load_composite_dq_overrides(entity)
        assert "field_validations" not in dq_overrides
        assert "cross_field_validations" not in dq_overrides

    @pytest.mark.parametrize("entity", EXTERNALIZED_COMPOSITE_ENTITIES)
    def test_composite_keeps_only_minimal_inline_dq_overrides(
        self, entity: str
    ) -> None:
        """Composite YAML keeps only pointer-style inline DQ overrides.

        Rich validation content belongs in the external per-entity DQ file, not
        in configs/composites/*.yaml.
        """
        dq_overrides = _load_composite_dq_overrides(entity)
        extra_keys = set(dq_overrides) - ALLOWED_INLINE_DQ_KEYS
        assert not extra_keys, (
            f"Unexpected inline DQ keys in configs/composites/{entity}.yaml: "
            f"{sorted(extra_keys)}"
        )

    @pytest.mark.parametrize("entity", EXTERNALIZED_COMPOSITE_ENTITIES)
    def test_external_composite_dq_bundle_is_not_threshold_only(
        self, entity: str
    ) -> None:
        external_path = COMPOSITE_QUALITY_DIR / f"{entity}.yaml"
        payload = _load_yaml(external_path)
        dq_overrides = payload.get("dq_overrides", payload)
        assert isinstance(dq_overrides, dict), f"Missing dq_overrides: {external_path}"

        required_fields = dq_overrides.get("required_fields")
        field_validations = dq_overrides.get("field_validations")
        cross_field_validations = dq_overrides.get("cross_field_validations")

        assert isinstance(required_fields, list) and required_fields, (
            f"Composite DQ config must declare non-empty required_fields: {external_path}"
        )
        assert (isinstance(field_validations, list) and field_validations) or (
            isinstance(cross_field_validations, list) and cross_field_validations
        ), (
            "Composite DQ config must declare field or cross-field validation "
            f"bundles: {external_path}"
        )
