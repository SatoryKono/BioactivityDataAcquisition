# pyright: reportArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportCallIssue=false
# pyright: reportIndexIssue=false
# pyright: reportMissingTypeArgument=false
# pyright: reportGeneralTypeIssues=false
# pyright: reportOptionalMemberAccess=false
# pyright: reportOperatorIssue=false
# pyright: reportAbstractUsage=false
# PD5 test mock/fixture surface — product NewTypes/Ports stay strict (#6997+#6998+#6999+#7000).
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
# PD6 residual test mock/fixture surface — product NewTypes/Ports stay strict (#7048).
"""Sync checks for the PubChem chemical standardization enum catalog."""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from bioetl.domain.normalization.chemical_standardization_contract import (
    CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    CHEMICAL_STANDARDIZATION_STATUSES,
)
from bioetl.domain.pubchem_standardization_catalog import (
    PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION,
    PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES,
    PUBCHEM_STANDARDIZATION_ENUM_CATALOG,
)

pytestmark = pytest.mark.unit

ENUM_PATH = Path("configs/enums/pubchem.yaml")


def _load_enum_payload() -> dict[str, object]:
    payload = yaml.safe_load(ENUM_PATH.read_text(encoding="utf-8"))
    assert isinstance(payload, dict)
    return payload


def test_pubchem_yaml_statuses_match_domain_contract() -> None:
    payload = _load_enum_payload()
    statuses = tuple(payload["compound"]["chemical_standardization_statuses"])

    assert statuses == CHEMICAL_STANDARDIZATION_STATUSES
    assert statuses == PUBCHEM_CHEMICAL_STANDARDIZATION_STATUSES
    assert (
        statuses
        == PUBCHEM_STANDARDIZATION_ENUM_CATALOG["chemical_standardization_statuses"]
    )


def test_pubchem_yaml_policy_version_matches_domain_contract() -> None:
    payload = _load_enum_payload()
    versions = tuple(payload["compound"]["chemical_standardization_policy_versions"])

    assert versions == (CHEMICAL_STANDARDIZATION_POLICY_VERSION,)
    assert versions == (PUBCHEM_CHEMICAL_STANDARDIZATION_POLICY_VERSION,)
    assert (
        versions
        == PUBCHEM_STANDARDIZATION_ENUM_CATALOG[
            "chemical_standardization_policy_versions"
        ]
    )
