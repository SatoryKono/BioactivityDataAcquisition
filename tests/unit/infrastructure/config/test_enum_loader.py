# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# pyright: reportUndefinedVariable=false
# pyright: reportPossiblyUnboundVariable=false
# pyright: reportTypedDictNotRequiredAccess=false
# pyright: reportOptionalSubscript=false
# pyright: reportOptionalOperand=false
# pyright: reportOptionalCall=false
# pyright: reportOptionalIterable=false
# pyright: reportIncompatibleMethodOverride=false
# pyright: reportIncompatibleVariableOverride=false
# pyright: reportUninitializedInstanceVariable=false
# pyright: reportReturnType=false
# pyright: reportInvalidCast=false
# pyright: reportAssignmentType=false
# pyright: reportImplicitAbstractClass=false
# pyright: reportFunctionMemberAccess=false
# pyright: reportConstantRedefinition=false
# pyright: reportInvalidTypeForm=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
"""Tests for filesystem-backed enum registry loading."""

from __future__ import annotations

import pytest

import yaml

from bioetl.domain.schemas.uniprot import (
    ENTRY_TYPES,
    PROTEIN_EXISTENCE_LEVELS,
    PROTEIN_FLAGS,
)
from bioetl.domain.schemas.uniprot.idmapping import MAPPING_STATUSES
from bioetl.infrastructure.config.enum_file_loader import (
    load_provider_enums_from_file,
)
from bioetl.infrastructure.config.enum_loader_adapter import FileSystemEnumLoader


pytestmark = pytest.mark.unit


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


def test_uniprot_enum_registry_matches_domain_contract_literals() -> None:
    enums = load_provider_enums_from_file("uniprot")

    assert enums["protein"]["entry_types"] == ENTRY_TYPES
    assert enums["protein"]["protein_flags"] == PROTEIN_FLAGS
    assert enums["protein"]["protein_existence_levels"] == (PROTEIN_EXISTENCE_LEVELS)
    assert enums["idmapping"]["mapping_statuses"] == MAPPING_STATUSES
