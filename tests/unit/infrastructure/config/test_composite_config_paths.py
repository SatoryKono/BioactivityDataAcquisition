"""Negative and canonical-path tests for composite config discovery."""

from pathlib import Path

import pytest

from bioetl.infrastructure.config._composite_config_paths import (
    list_composite_config_names,
    resolve_composite_config_dir,
    resolve_composite_config_path,
)

pytestmark = pytest.mark.unit


def test_resolve_composite_config_path_and_missing_error(tmp_path: Path) -> None:
    config_dir = tmp_path / "composites"
    config_dir.mkdir()
    expected = config_dir / "publication.yaml"
    expected.write_text("composite: {}\n", encoding="utf-8")

    assert resolve_composite_config_dir(config_dir=config_dir) == config_dir
    assert (
        resolve_composite_config_path("publication", config_dir=config_dir) == expected
    )
    with pytest.raises(FileNotFoundError, match="missing.yaml"):
        resolve_composite_config_path("missing", config_dir=config_dir)


def test_list_composite_config_names_excludes_sidecars_malformed_and_unreadable(
    tmp_path: Path,
) -> None:
    config_dir = tmp_path / "composites"
    config_dir.mkdir()
    (config_dir / "valid.yaml").write_text("composite: {}\n", encoding="utf-8")
    (config_dir / "sidecar.yaml").write_text("policy: {}\n", encoding="utf-8")
    (config_dir / "malformed.yaml").write_text("- not-a-mapping\n", encoding="utf-8")
    (config_dir / "unreadable.yaml").mkdir()

    assert list_composite_config_names(config_dir=config_dir) == ("valid",)
