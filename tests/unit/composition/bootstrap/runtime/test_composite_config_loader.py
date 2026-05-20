"""Unit tests for composite config path resolution in runtime bootstrap."""

from __future__ import annotations

from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
import yaml

import bioetl.composition.bootstrap.runtime.composite as composite_runtime


def _build_composite_payload(name: str) -> dict[str, Any]:
    return {
        "schema_version": "2.0.0",
        "composite": {
            "name": name,
            "version": "1.0.0",
            "seed": {
                "pipeline": "chembl_publication",
                "output_keys": ["publication_id", "doi"],
                "silver_table": "silver/chembl/publication",
            },
            "enrichers": [
                {
                    "pipeline": "crossref_publication",
                    "join_keys": ["doi"],
                    "silver_table": "silver/crossref/publication",
                }
            ],
            "merge": {
                "output": {
                    "silver": "silver/composite/publication",
                    "gold": "gold/composite/publication",
                },
                "sort_by": {
                    "silver": ["entity_id", "publication_id"],
                    "gold": ["entity_id", "publication_id"],
                },
            },
        },
    }


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=False)


def _deep_merge_dicts(
    base: dict[str, Any],  # Any: test helper mirrors YAML merge semantics
    override: dict[str, Any],  # Any: test helper mirrors YAML merge semantics
) -> dict[str, Any]:
    merged = deepcopy(base)
    for key, value in override.items():
        current = merged.get(key)
        if isinstance(current, dict) and isinstance(value, dict):
            merged[key] = _deep_merge_dicts(current, value)
            continue
        merged[key] = deepcopy(value)
    return merged


class TestCompositeConfigPathResolution:
    """Tests for composite config path resolution."""

    def test_loads_from_canonical_composites_dir(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        new_dir = tmp_path / "configs" / "composites"

        _write_yaml(
            new_dir / "publication.yaml",
            _build_composite_payload("composite_publication_new"),
        )

        monkeypatch.setattr(composite_runtime, "DEFAULT_COMPOSITE_CONFIG_DIR", new_dir)

        config = composite_runtime.load_composite_config("publication")
        assert config.name == "composite_publication_new"

    def test_raises_file_not_found_for_missing_config(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        new_dir = tmp_path / "configs" / "composites"

        monkeypatch.setattr(composite_runtime, "DEFAULT_COMPOSITE_CONFIG_DIR", new_dir)

        with pytest.raises(FileNotFoundError) as exc_info:
            composite_runtime.load_composite_config("publication")

        message = str(exc_info.value)
        assert str(new_dir / "publication.yaml") in message


class TestCompositeConfigColumnGroups:
    """Tests for retired column_groups_file behavior in load_composite_config()."""

    def test_rejects_retired_column_groups_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config_path = tmp_path / "publication.yaml"
        _write_yaml(
            config_path,
            {
                "composite": {
                    "name": "publication",
                    "version": "1.0.0",
                    "seed": {
                        "pipeline": "chembl_publication",
                        "output_keys": ["publication_id", "doi"],
                        "silver_table": "silver/chembl/publication",
                    },
                    "enrichers": [
                        {
                            "pipeline": "crossref_publication",
                            "join_keys": ["doi"],
                            "silver_table": "silver/crossref/publication",
                        }
                    ],
                    "merge": {
                        "column_groups_file": "groups.yaml",
                        "output": {
                            "silver": "silver/composite/publication",
                            "gold": "gold/composite/publication",
                        },
                        "sort_by": {
                            "silver": ["entity_id", "publication_id"],
                            "gold": ["entity_id", "publication_id"],
                        },
                    },
                }
            },
        )

        monkeypatch.setattr(
            composite_runtime,
            "_resolve_composite_config_path",
            lambda _name: config_path,
        )

        with pytest.raises(ValueError, match="column_groups_file"):
            composite_runtime.load_composite_config("publication")

    def test_wraps_validation_error_as_value_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config_path = tmp_path / "broken.yaml"
        _write_yaml(config_path, {"composite": {"merge": {}}})

        def _raise_validation(_payload: dict[str, Any]) -> None:
            # Raise pydantic.ValidationError to match the expected exception type
            from pydantic import ValidationError

            raise ValidationError(
                [{"loc": ("composite",), "msg": "bad payload", "type": "value_error"}]
            )

        monkeypatch.setattr(
            composite_runtime,
            "_resolve_composite_config_path",
            lambda _name: config_path,
        )
        monkeypatch.setattr(
            composite_runtime,
            "validate_composite_config_payload",
            _raise_validation,
        )

        with pytest.raises(ValueError, match="Invalid composite config 'broken'"):
            composite_runtime.load_composite_config("broken")

    def test_rejects_missing_composite_version(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Composite runtime must fail fast when composite.version is omitted."""
        config_path = tmp_path / "missing-version.yaml"
        _write_yaml(
            config_path,
            {
                "schema_version": "2.0.0",
                "composite": {
                    "name": "publication",
                    "seed": {
                        "pipeline": "chembl_publication",
                        "output_keys": ["publication_id", "doi"],
                        "silver_table": "silver/chembl/publication",
                    },
                    "enrichers": [
                        {
                            "pipeline": "crossref_publication",
                            "join_keys": ["doi"],
                            "silver_table": "silver/crossref/publication",
                        }
                    ],
                    "merge": {
                        "output": {
                            "silver": "silver/composite/publication",
                            "gold": "gold/composite/publication",
                        },
                        "sort_by": {
                            "silver": ["entity_id", "publication_id"],
                            "gold": ["entity_id", "publication_id"],
                        },
                    },
                },
            },
        )

        monkeypatch.setattr(
            composite_runtime,
            "_resolve_composite_config_path",
            lambda _name: config_path,
        )

        with pytest.raises(
            ValueError,
            match="Invalid composite config 'missing-version'",
        ):
            composite_runtime.load_composite_config("missing-version")


class TestCompositeDQExternalization:
    """Tests for externalized composite DQ config loading.

    The external file is the canonical composite DQ source; inline keys are
    intentionally limited to pointer-style and last-mile override values.
    """

    def test_dq_config_file_inline_precedence(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """External DQ file provides the base payload; inline overrides win last."""
        configs_root = tmp_path / "configs"
        composites_dir = configs_root / "composites"
        quality_file = (
            configs_root / "quality" / "entities" / "composite" / "publication.yaml"
        )

        payload = _build_composite_payload("composite_precedence")
        composite_payload = payload["composite"]
        assert isinstance(composite_payload, dict)
        composite_payload["dq_overrides"] = {
            "dq_config_file": "../quality/entities/composite/publication.yaml",
            "soft_fail_threshold": 0.10,
            "enricher_overrides": {
                "crossref_publication": {
                    "hard_fail_threshold": 0.50,
                }
            },
        }

        _write_yaml(composites_dir / "publication.yaml", payload)
        _write_yaml(
            quality_file,
            {
                "dq_overrides": {
                    "soft_fail_threshold": 0.05,
                    "hard_fail_threshold": 0.25,
                    "required_fields": ["publication_id"],
                    "field_validations": [
                        {
                            "field": "publication_id",
                            "type": "required",
                            "nullable": False,
                        }
                    ],
                    "cross_field_validations": [
                        {
                            "name": "publication_identity_anchor",
                            "fields": ["doi", "pmid", "title"],
                            "condition": "any_present",
                        }
                    ],
                    "enricher_overrides": {
                        "crossref_publication": {
                            "soft_fail_threshold": 0.15,
                            "hard_fail_threshold": 0.30,
                        }
                    },
                }
            },
        )

        monkeypatch.setattr(
            composite_runtime, "DEFAULT_COMPOSITE_CONFIG_DIR", composites_dir
        )

        config = composite_runtime.load_composite_config("publication")

        assert config.dq.soft_fail_threshold == pytest.approx(0.10)
        assert config.dq.hard_fail_threshold == pytest.approx(0.25)
        assert config.dq.required_fields == ("publication_id",)
        assert config.dq.field_validations[0].field == "publication_id"
        assert config.dq.field_validations[0].validation_type == "required"
        assert config.dq.cross_field_validations[0].name == (
            "publication_identity_anchor"
        )
        override = config.dq.enricher_overrides["crossref_publication"]
        assert override.soft_fail_threshold == pytest.approx(0.15)
        assert override.hard_fail_threshold == pytest.approx(0.50)

    def test_rejects_legacy_dead_composite_dq_keys(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Legacy entity_* validation keys must fail instead of being ignored."""
        configs_root = tmp_path / "configs"
        composites_dir = configs_root / "composites"
        quality_file = (
            configs_root / "quality" / "entities" / "composite" / "publication.yaml"
        )

        payload = _build_composite_payload("composite_legacy_dead_keys")
        composite_payload = payload["composite"]
        assert isinstance(composite_payload, dict)
        composite_payload["dq_overrides"] = {
            "dq_config_file": "../quality/entities/composite/publication.yaml"
        }

        _write_yaml(composites_dir / "publication.yaml", payload)
        _write_yaml(
            quality_file,
            {
                "dq_overrides": {
                    "soft_fail_threshold": 0.05,
                    "hard_fail_threshold": 0.25,
                    "required_fields": ["publication_id"],
                    "entity_field_validations": {
                        "publication_id": {
                            "type": "required",
                            "nullable": False,
                        }
                    },
                }
            },
        )

        monkeypatch.setattr(
            composite_runtime, "DEFAULT_COMPOSITE_CONFIG_DIR", composites_dir
        )

        with pytest.raises(ValueError, match="entity_field_validations"):
            composite_runtime.load_composite_config("publication")

    @pytest.mark.parametrize(
        ("entity", "business_key"),
        [
            ("activity", "activity_id"),
            ("assay", "assay_id"),
            ("molecule", "molecule_id"),
            ("publication", "publication_id"),
            ("target", "target_id"),
        ],
    )
    def test_composite_resolved_config_golden_master_before_after(
        self,
        entity: str,
        business_key: str,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        current_path = Path(f"configs/composites/{entity}.yaml")
        external_path = Path(f"configs/quality/entities/composite/{entity}.yaml")

        current_payload = yaml.safe_load(current_path.read_text(encoding="utf-8"))
        external_payload = yaml.safe_load(external_path.read_text(encoding="utf-8"))

        assert isinstance(current_payload, dict)
        assert isinstance(external_payload, dict)
        external_dq = external_payload.get("dq_overrides", external_payload)
        assert isinstance(external_dq, dict)

        before_payload = deepcopy(current_payload)
        before_dq = before_payload["composite"]["dq_overrides"]
        assert isinstance(before_dq, dict)
        inline_dq = {
            key: value for key, value in before_dq.items() if key != "dq_config_file"
        }
        before_payload["composite"]["dq_overrides"] = _deep_merge_dicts(
            external_dq, inline_dq
        )

        after_payload = deepcopy(current_payload)
        for payload in (before_payload, after_payload):
            merge = payload["composite"]["merge"]
            assert isinstance(merge, dict)
            merge.setdefault(
                "sort_by",
                {
                    "silver": ["entity_id", business_key],
                    "gold": ["entity_id", business_key],
                },
            )

        configs_root = tmp_path / "configs"
        composites_dir = configs_root / "composites"
        quality_dir = configs_root / "quality" / "entities" / "composite"

        _write_yaml(composites_dir / f"{entity}_inline.yaml", before_payload)
        _write_yaml(composites_dir / f"{entity}_external.yaml", after_payload)
        _write_yaml(quality_dir / f"{entity}.yaml", external_payload)

        monkeypatch.setattr(
            composite_runtime, "DEFAULT_COMPOSITE_CONFIG_DIR", composites_dir
        )

        before_config = composite_runtime.load_composite_config(f"{entity}_inline")
        after_config = composite_runtime.load_composite_config(f"{entity}_external")

        assert after_config == before_config
