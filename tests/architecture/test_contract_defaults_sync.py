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
"""Verify that _DefaultContractPolicy stays in sync with configs/base/pipeline.yaml.

The YAML ``contract_defaults`` section is the SSOT.  The dataclass in
``contract_policy.py`` is a fallback for when no config is injected.  Both must
agree on ``rename_map`` and ``hash_exclude`` to avoid silent drift.
"""

from __future__ import annotations

import pytest

from pathlib import Path

import yaml

from bioetl.application.core.base_transformer.contract_policy import (
    _DefaultContractPolicy,
)

pytestmark = pytest.mark.architecture

_CONFIGS_ROOT = Path("configs")


def _load_yaml_contract_defaults() -> dict:
    base_path = _CONFIGS_ROOT / "base" / "pipeline.yaml"
    with open(base_path, encoding="utf-8") as f:
        raw = yaml.safe_load(f) or {}
    return raw.get("contract_defaults", {})


def test_rename_map_matches_yaml() -> None:
    yaml_defaults = _load_yaml_contract_defaults()
    code_defaults = _DefaultContractPolicy()

    assert code_defaults.rename_map == yaml_defaults["rename_map"], (
        "rename_map drift between _DefaultContractPolicy and "
        "configs/base/pipeline.yaml contract_defaults"
    )


def test_hash_exclude_matches_yaml() -> None:
    yaml_defaults = _load_yaml_contract_defaults()
    code_defaults = _DefaultContractPolicy()

    assert sorted(code_defaults.hash_exclude) == sorted(
        yaml_defaults["hash_exclude"]
    ), (
        "hash_exclude drift between _DefaultContractPolicy and "
        "configs/base/pipeline.yaml contract_defaults"
    )


def test_hash_include_matches_yaml() -> None:
    yaml_defaults = _load_yaml_contract_defaults()
    code_defaults = _DefaultContractPolicy()

    assert code_defaults.hash_include == yaml_defaults["hash_include"], (
        "hash_include drift between _DefaultContractPolicy and "
        "configs/base/pipeline.yaml contract_defaults"
    )
