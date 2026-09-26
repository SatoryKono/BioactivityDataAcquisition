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
from __future__ import annotations

from pathlib import Path

import pytest

from bioetl.infrastructure.config.entity_filter_metadata_registry import (
    apply_shared_filter_metadata,
    load_shared_filter_metadata,
)


pytestmark = pytest.mark.unit


def test_load_shared_filter_metadata_returns_deep_copied_profile_match(
    tmp_path: Path,
) -> None:
    registry_path = tmp_path / "quality" / "entity_filter_metadata_registry.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        """
profiles:
  ignored: not-a-dict
  shared_publication:
    applies_to:
      - configs/entities/chembl/publication.yaml
    filter_metadata:
      publication_filter_policy:
        enabled: true
        source: registry
""",
        encoding="utf-8",
    )

    result = load_shared_filter_metadata(
        configs_root=tmp_path,
        config_rel_path="configs/entities/chembl/publication.yaml",
    )
    result["publication_filter_policy"]["enabled"] = False

    reloaded = load_shared_filter_metadata(
        configs_root=tmp_path,
        config_rel_path="configs/entities/chembl/publication.yaml",
    )

    assert reloaded == {
        "publication_filter_policy": {
            "enabled": True,
            "source": "registry",
        }
    }


def test_apply_shared_filter_metadata_merges_registry_data_and_supports_external_paths(
    tmp_path: Path,
) -> None:
    external_config = tmp_path.parent / f"{tmp_path.name}_outside" / "publication.yaml"
    external_config.parent.mkdir(parents=True)
    external_config.write_text("version: '1.0.0'\n", encoding="utf-8")

    registry_path = tmp_path / "quality" / "entity_filter_metadata_registry.yaml"
    registry_path.parent.mkdir(parents=True)
    registry_path.write_text(
        f"""
profiles:
  external_profile:
    applies_to:
      - {external_config.as_posix()}
    filter_metadata:
      publication_filter_policy:
        enabled: true
        source: registry
""",
        encoding="utf-8",
    )

    payload = {
        "filters": {
            "metadata": {
                "publication_filter_policy": {
                    "enabled": False,
                    "owner": "entity",
                }
            }
        }
    }

    merged = apply_shared_filter_metadata(
        configs_root=tmp_path,
        config_path=external_config,
        payload=payload,
    )

    assert merged == {
        "filters": {
            "metadata": {
                "publication_filter_policy": {
                    "enabled": False,
                    "source": "registry",
                    "owner": "entity",
                }
            }
        }
    }


def test_apply_shared_filter_metadata_returns_payload_when_no_profile_matches(
    tmp_path: Path,
) -> None:
    payload = {"filters": {"metadata": {"unchanged": True}}}

    assert (
        apply_shared_filter_metadata(
            configs_root=tmp_path,
            config_path=tmp_path / "entities" / "missing.yaml",
            payload=payload,
        )
        == payload
    )
