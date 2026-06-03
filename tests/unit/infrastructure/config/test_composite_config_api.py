"""Unit tests for the canonical infrastructure composite config API."""

from __future__ import annotations

from pathlib import Path
from typing import Any
from types import SimpleNamespace

import pytest
import yaml

from bioetl.domain.contracts.gold import CompositePublicationGoldSchema
from bioetl.infrastructure.config import (
    load_composite_config as public_load_composite_config,
)
from bioetl.infrastructure.config.composite_config_api import (
    load_composite_config,
    resolve_composite_config_dir,
    resolve_composite_config_path,
    resolve_composite_gold_schema,
)

ROOT = Path(__file__).resolve().parents[4]


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
    with path.open("w", encoding="utf-8", newline="\n") as handle:
        yaml.safe_dump(payload, handle, sort_keys=False, allow_unicode=False)


@pytest.mark.unit
def test_resolve_composite_config_path_uses_config_dir() -> None:
    config_dir = Path("configs/composites")

    result = resolve_composite_config_path("publication", config_dir=config_dir)

    assert result == ROOT / "configs" / "composites" / "publication.yaml"


@pytest.mark.unit
def test_resolve_composite_config_dir_uses_explicit_configs_root(
    tmp_path: Path,
) -> None:
    configs_root = tmp_path / "tracked-configs"

    result = resolve_composite_config_dir(configs_root=configs_root)

    assert result == configs_root / "composites"


@pytest.mark.unit
def test_load_composite_config_defaults_to_repo_root_when_cwd_differs(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.chdir(tmp_path)

    config = load_composite_config("activity")

    assert config.name == "composite_activity"


@pytest.mark.unit
def test_load_composite_config_missing_file_raises_file_not_found(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "configs" / "composites"

    with pytest.raises(FileNotFoundError, match="Composite config not found"):
        load_composite_config("publication", config_dir=config_dir)


@pytest.mark.unit
def test_load_composite_config_rejects_non_mapping_payload(tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "composites" / "publication.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("- one\n- two\n", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="expected top-level mapping",
    ):
        load_composite_config("publication", config_dir=config_path.parent)


@pytest.mark.unit
def test_load_composite_config_rejects_empty_yaml_payload(tmp_path: Path) -> None:
    config_path = tmp_path / "configs" / "composites" / "publication.yaml"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text("", encoding="utf-8")

    with pytest.raises(
        ValueError,
        match="expected top-level mapping",
    ):
        load_composite_config("publication", config_dir=config_path.parent)


@pytest.mark.unit
def test_load_composite_config_rejects_missing_composite_version(tmp_path: Path) -> None:
    config_dir = tmp_path / "configs" / "composites"
    payload = _build_composite_payload("composite_publication")
    del payload["composite"]["version"]
    _write_yaml(config_dir / "publication.yaml", payload)

    with pytest.raises(ValueError, match="Invalid composite config 'publication'"):
        load_composite_config("publication", config_dir=config_dir)


@pytest.mark.unit
def test_load_composite_config_propagates_missing_external_dq_override_path(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "configs" / "composites"
    payload = _build_composite_payload("composite_publication")
    payload["composite"]["dq_overrides"] = {
        "dq_config_file": "../quality/entities/composite/missing.yaml",
    }
    _write_yaml(config_dir / "publication.yaml", payload)

    with pytest.raises(
        FileNotFoundError,
        match="Composite DQ config not found",
    ):
        load_composite_config("publication", config_dir=config_dir)


@pytest.mark.unit
def test_load_composite_config_propagates_invalid_external_dq_payload_type(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "configs" / "composites"
    quality_path = (
        tmp_path
        / "configs"
        / "quality"
        / "entities"
        / "composite"
        / "publication.yaml"
    )
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    quality_path.write_text("[1]\n", encoding="utf-8")

    payload = _build_composite_payload("composite_publication")
    payload["composite"]["dq_overrides"] = {
        "dq_config_file": "../quality/entities/composite/publication.yaml"
    }
    _write_yaml(config_dir / "publication.yaml", payload)

    with pytest.raises(
        ValueError,
        match="Composite DQ config must be a mapping",
    ):
        load_composite_config("publication", config_dir=config_dir)


@pytest.mark.unit
def test_load_composite_config_uses_custom_validator_and_preserves_payload_mutation(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "configs" / "composites"
    payload = _build_composite_payload("composite_publication")
    payload["composite"]["dq_overrides"] = {
        "dq_config_file": "../quality/entities/composite/publication.yaml"
    }
    _write_yaml(config_dir / "publication.yaml", payload)

    quality_path = (
        tmp_path
        / "configs"
        / "quality"
        / "entities"
        / "composite"
        / "publication.yaml"
    )
    quality_path.parent.mkdir(parents=True, exist_ok=True)
    _write_yaml(quality_path, {"dq_overrides": {"hard_fail_threshold": 0.25}})

    seen_payload: dict[str, Any] | None = None

    def _validator(validated: dict[str, Any]) -> SimpleNamespace:
        nonlocal seen_payload
        seen_payload = validated
        return SimpleNamespace(to_domain=lambda: "ok")

    result = load_composite_config(
        "publication",
        config_dir=config_dir,
        validate_payload=_validator,
    )

    assert result == "ok"
    assert seen_payload is not None
    composite_dq = seen_payload["composite"]["dq_overrides"]
    assert isinstance(composite_dq, dict)
    assert composite_dq["hard_fail_threshold"] == 0.25


@pytest.mark.unit
def test_resolve_composite_gold_schema_supports_prefixed_names() -> None:
    assert (
        resolve_composite_gold_schema("publication") is CompositePublicationGoldSchema
    )
    assert (
        resolve_composite_gold_schema("composite_publication")
        is CompositePublicationGoldSchema
    )
    assert resolve_composite_gold_schema("composite_unknown") is None


@pytest.mark.unit
def test_load_composite_config_merges_external_dq_with_inline_precedence(
    tmp_path: Path,
) -> None:
    configs_root = tmp_path / "configs"
    composites_dir = configs_root / "composites"
    quality_file = (
        configs_root / "quality" / "entities" / "composite" / "publication.yaml"
    )

    payload = _build_composite_payload("composite_publication")
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

    config = load_composite_config("publication", config_dir=composites_dir)

    assert config.name == "composite_publication"
    assert config.dq.soft_fail_threshold == pytest.approx(0.10)
    assert config.dq.hard_fail_threshold == pytest.approx(0.25)
    assert config.dq.required_fields == ("publication_id",)
    override = config.dq.enricher_overrides["crossref_publication"]
    assert override.soft_fail_threshold == pytest.approx(0.15)
    assert override.hard_fail_threshold == pytest.approx(0.50)


@pytest.mark.unit
def test_public_config_package_reexports_load_composite_config(
    tmp_path: Path,
) -> None:
    composites_dir = tmp_path / "configs" / "composites"
    _write_yaml(
        composites_dir / "publication.yaml",
        _build_composite_payload("composite_publication"),
    )

    config = public_load_composite_config("publication", config_dir=composites_dir)

    assert public_load_composite_config is load_composite_config
    assert config.name == "composite_publication"
