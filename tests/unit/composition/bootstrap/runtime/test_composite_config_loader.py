"""Unit tests for composite config path resolution in runtime bootstrap."""

from __future__ import annotations

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
    """Tests for new composite config path with legacy fallback."""

    def test_prefers_new_path_over_legacy(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        new_dir = tmp_path / "configs" / "composites"
        legacy_dir = tmp_path / "configs" / "pipelines" / "composite"

        _write_yaml(
            new_dir / "publication.yaml",
            _build_composite_payload("composite_publication_new"),
        )
        _write_yaml(
            legacy_dir / "publication.yaml",
            _build_composite_payload("composite_publication_legacy"),
        )

        monkeypatch.setattr(composite_runtime, "COMPOSITE_CONFIG_DIR", new_dir)
        monkeypatch.setattr(
            composite_runtime,
            "LEGACY_COMPOSITE_CONFIG_DIR",
            legacy_dir,
        )

        config = composite_runtime.load_composite_config("publication")
        assert config.name == "composite_publication_new"

    def test_falls_back_to_legacy_path(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        new_dir = tmp_path / "configs" / "composites"
        legacy_dir = tmp_path / "configs" / "pipelines" / "composite"

        _write_yaml(
            legacy_dir / "publication.yaml",
            _build_composite_payload("composite_publication_legacy"),
        )

        monkeypatch.setattr(composite_runtime, "COMPOSITE_CONFIG_DIR", new_dir)
        monkeypatch.setattr(
            composite_runtime,
            "LEGACY_COMPOSITE_CONFIG_DIR",
            legacy_dir,
        )

        config = composite_runtime.load_composite_config("publication")
        assert config.name == "composite_publication_legacy"

    def test_raises_file_not_found_with_both_paths(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        new_dir = tmp_path / "configs" / "composites"
        legacy_dir = tmp_path / "configs" / "pipelines" / "composite"

        monkeypatch.setattr(composite_runtime, "COMPOSITE_CONFIG_DIR", new_dir)
        monkeypatch.setattr(
            composite_runtime,
            "LEGACY_COMPOSITE_CONFIG_DIR",
            legacy_dir,
        )

        with pytest.raises(FileNotFoundError) as exc_info:
            composite_runtime.load_composite_config("publication")

        message = str(exc_info.value)
        assert str(new_dir / "publication.yaml") in message
        assert str(legacy_dir / "publication.yaml") in message
