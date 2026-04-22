"""Tests for filesystem-backed enum registry loading."""

from __future__ import annotations

import yaml

from bioetl.infrastructure.config.enum_file_loader import (
    load_provider_enums_from_file,
)
from bioetl.infrastructure.config.enum_loader_adapter import FileSystemEnumLoader


def test_filesystem_enum_loader_loads_non_chembl_provider(tmp_path) -> None:
    enum_path = tmp_path / "configs" / "enums"
    enum_path.mkdir(parents=True)
    (enum_path / "uniprot.yaml").write_text(
        yaml.safe_dump(
            {
                "version": "test",
                "protein": {
                    "entry_types": [
                        "UniProtKB reviewed (Swiss-Prot)",
                        "UniProtKB unreviewed (TrEMBL)",
                    ]
                },
            },
            sort_keys=True,
        ),
        encoding="utf-8",
    )

    loader = FileSystemEnumLoader(base_path=tmp_path)

    assert loader.load_provider_enums("uniprot")["protein"]["entry_types"] == [
        "UniProtKB reviewed (Swiss-Prot)",
        "UniProtKB unreviewed (TrEMBL)",
    ]


def test_provider_file_loader_rejects_path_like_provider_names() -> None:
    try:
        load_provider_enums_from_file("../chembl")
    except ValueError as exc:
        assert "path separators" in str(exc)
    else:  # pragma: no cover - assertion helper branch
        raise AssertionError("Expected path-like provider to be rejected")
