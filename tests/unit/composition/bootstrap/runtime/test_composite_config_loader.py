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
                }
            },
        },
    }


def _write_yaml(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="\n") as f:
        yaml.safe_dump(payload, f, sort_keys=False, allow_unicode=False)


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

        monkeypatch.setattr(composite_runtime, "COMPOSITE_CONFIG_DIR", new_dir)

        config = composite_runtime.load_composite_config("publication")
        assert config.name == "composite_publication_new"

    def test_raises_file_not_found_for_missing_config(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        new_dir = tmp_path / "configs" / "composites"

        monkeypatch.setattr(composite_runtime, "COMPOSITE_CONFIG_DIR", new_dir)

        with pytest.raises(FileNotFoundError) as exc_info:
            composite_runtime.load_composite_config("publication")

        message = str(exc_info.value)
        assert str(new_dir / "publication.yaml") in message


class TestCompositeConfigColumnGroups:
    """Tests for column_groups_file loading branches in load_composite_config()."""

    def test_loads_column_groups_from_list_file(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config_path = tmp_path / "publication.yaml"
        groups_path = tmp_path / "groups.yaml"
        _write_yaml(
            config_path,
            {
                "composite": {
                    "merge": {"column_groups_file": "groups.yaml"},
                }
            },
        )
        _write_yaml(
            groups_path,
            {
                "column_groups": [
                    {"name": "ids", "columns": ["publication_id", "doi"]}
                ],
            },
        )

        captured: dict[str, Any] = {}

        class _Schema:
            def to_domain(self) -> str:
                return "ok"

        def _capture(payload: dict[str, Any]) -> _Schema:
            captured["payload"] = payload
            return _Schema()

        monkeypatch.setattr(
            composite_runtime,
            "_resolve_composite_config_path",
            lambda _name: config_path,
        )
        monkeypatch.setattr(
            composite_runtime,
            "validate_composite_config_payload",
            _capture,
        )

        result = composite_runtime.load_composite_config("publication")

        assert result == "ok"
        groups = captured["payload"]["composite"]["merge"]["column_groups"]
        assert groups == [{"name": "ids", "columns": ["publication_id", "doi"]}]

    def test_loads_column_groups_from_raw_list(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config_path = tmp_path / "publication.yaml"
        groups_path = tmp_path / "groups.yaml"
        _write_yaml(
            config_path,
            {
                "composite": {
                    "merge": {"column_groups_file": "groups.yaml"},
                }
            },
        )
        groups_path.write_text(
            "- name: docs\n  columns:\n    - publication_id\n    - title\n",
            encoding="utf-8",
        )

        captured: dict[str, Any] = {}

        class _Schema:
            def to_domain(self) -> str:
                return "ok"

        def _capture(payload: dict[str, Any]) -> _Schema:
            captured["payload"] = payload
            return _Schema()

        monkeypatch.setattr(
            composite_runtime,
            "_resolve_composite_config_path",
            lambda _name: config_path,
        )
        monkeypatch.setattr(
            composite_runtime,
            "validate_composite_config_payload",
            _capture,
        )

        composite_runtime.load_composite_config("publication")
        groups = captured["payload"]["composite"]["merge"]["column_groups"]
        assert groups == [{"name": "docs", "columns": ["publication_id", "title"]}]

    def test_wraps_validation_error_as_value_error(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        config_path = tmp_path / "broken.yaml"
        _write_yaml(config_path, {"composite": {"merge": {}}})

        class _DummyValidationError(Exception):
            pass

        def _raise_validation(_payload: dict[str, Any]) -> None:
            raise _DummyValidationError("bad payload")

        monkeypatch.setattr(
            composite_runtime,
            "_resolve_composite_config_path",
            lambda _name: config_path,
        )
        monkeypatch.setattr(
            composite_runtime,
            "ValidationError",
            _DummyValidationError,
        )
        monkeypatch.setattr(
            composite_runtime,
            "validate_composite_config_payload",
            _raise_validation,
        )

        with pytest.raises(ValueError, match="Invalid composite config 'broken'"):
            composite_runtime.load_composite_config("broken")


class TestCompositeDQExternalization:
    """Tests for externalized composite DQ config loading."""

    def test_dq_config_file_inline_precedence(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
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
                    "enricher_overrides": {
                        "crossref_publication": {
                            "soft_fail_threshold": 0.15,
                            "hard_fail_threshold": 0.30,
                        }
                    },
                }
            },
        )

        monkeypatch.setattr(composite_runtime, "COMPOSITE_CONFIG_DIR", composites_dir)

        config = composite_runtime.load_composite_config("publication")

        assert config.dq.soft_fail_threshold == 0.10
        assert config.dq.hard_fail_threshold == 0.25
        assert config.dq.required_fields == ("publication_id",)
        override = config.dq.enricher_overrides["crossref_publication"]
        assert override.soft_fail_threshold == 0.15
        assert override.hard_fail_threshold == 0.50

    def test_publication_resolved_config_golden_master_before_after(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        current_path = Path("configs/composites/publication.yaml")
        external_path = Path("configs/quality/entities/composite/publication.yaml")

        current_payload = yaml.safe_load(current_path.read_text(encoding="utf-8"))
        external_payload = yaml.safe_load(external_path.read_text(encoding="utf-8"))

        assert isinstance(current_payload, dict)
        assert isinstance(external_payload, dict)
        external_dq = external_payload.get("dq_overrides", {})
        assert isinstance(external_dq, dict)
        field_validations = external_dq.get("field_validations")
        assert isinstance(field_validations, dict)

        before_payload = deepcopy(current_payload)
        before_dq = before_payload["composite"]["dq_overrides"]
        assert isinstance(before_dq, dict)
        before_dq.pop("dq_config_file", None)
        before_dq["field_validations"] = deepcopy(field_validations)

        after_payload = deepcopy(current_payload)

        configs_root = tmp_path / "configs"
        composites_dir = configs_root / "composites"
        quality_dir = configs_root / "quality" / "entities" / "composite"

        _write_yaml(composites_dir / "publication_inline.yaml", before_payload)
        _write_yaml(composites_dir / "publication_external.yaml", after_payload)
        _write_yaml(quality_dir / "publication.yaml", external_payload)

        monkeypatch.setattr(composite_runtime, "COMPOSITE_CONFIG_DIR", composites_dir)

        before_config = composite_runtime.load_composite_config("publication_inline")
        after_config = composite_runtime.load_composite_config("publication_external")

        assert after_config == before_config
