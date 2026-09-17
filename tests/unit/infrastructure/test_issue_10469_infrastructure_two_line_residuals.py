"""Focused low-line infrastructure coverage for #10469."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from bioetl.infrastructure.adapters._base_runtime import resolve_lazy_private_alias
from bioetl.infrastructure.adapters.chembl.models_common import (
    ChemblPublicationApiRecord,
)
from bioetl.infrastructure.config.contract_policy_validation import (
    _supported_versions,
    _validate_supported_rollout_versions,
)
from bioetl.infrastructure.config.converters import _extract_source_fields
from bioetl.infrastructure.config.staged_enforcement_policy_loader import (
    load_staged_enforcement_policies,
)
from bioetl.infrastructure.config.workflow_config_api import (
    load_workflow_config,
    resolve_workflow_config_path,
)
from bioetl.infrastructure.config_loader_filtering import (
    apply_hierarchical_filter_config,
)


pytestmark = pytest.mark.unit


def test_lazy_private_alias_reports_absent_http_client_and_logger() -> None:
    host = SimpleNamespace()

    assert resolve_lazy_private_alias(host, "_http_client") == (False, None)
    assert resolve_lazy_private_alias(host, "_logger") == (False, None)


def test_chembl_publication_normalizes_nullable_and_text_pubmed_ids() -> None:
    assert ChemblPublicationApiRecord._normalize_pubmed_id(None) is None
    assert ChemblPublicationApiRecord._normalize_pubmed_id("123") == "123"


def test_contract_policy_helpers_cover_missing_and_unsupported_versions() -> None:
    assert _supported_versions({}) == set()
    with pytest.raises(ValueError, match="Unsupported contract versions"):
        _validate_supported_rollout_versions(
            contract_ref="chembl.activity",
            rollout_versions={"2"},
            supported_versions={"1"},
        )


def test_source_field_converter_handles_scalar_field_names() -> None:
    config = SimpleNamespace(source=SimpleNamespace(fields=["id", 2]))

    assert _extract_source_fields(config) == ["id", "2"]


@pytest.mark.parametrize(
    "payload,match",
    [
        ("not_policies: true\n", "Expected 'policies' list"),
        ("policies:\n  - invalid\n", "Expected mapping policy row"),
    ],
)
def test_staged_policy_loader_rejects_invalid_shapes(
    tmp_path: Path, payload: str, match: str
) -> None:
    path = tmp_path / "policies.yaml"
    path.write_text(payload, encoding="utf-8")

    with pytest.raises(ValueError, match=match):
        load_staged_enforcement_policies(path)


def test_workflow_config_loader_rejects_missing_and_scalar_yaml(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="Workflow config not found"):
        resolve_workflow_config_path("missing", config_dir=tmp_path)

    (tmp_path / "scalar.yaml").write_text("value\n", encoding="utf-8")
    with pytest.raises(ValueError, match="expected top-level mapping"):
        load_workflow_config("scalar", config_dir=tmp_path)


def test_hierarchical_filter_config_ignores_missing_identity() -> None:
    loader = SimpleNamespace(load_as_dict=lambda *_args, **_kwargs: {})
    config: dict[str, object] = {}

    apply_hierarchical_filter_config(config, {}, filter_loader=loader)

    assert config == {}


def test_hierarchical_filter_config_merges_inline_filter_rules() -> None:
    seen: list[object] = []

    def load_as_dict(*args: object) -> dict[str, object]:
        seen.extend(args)
        return {}

    loader = SimpleNamespace(load_as_dict=load_as_dict)
    config: dict[str, object] = {"provider": "chembl", "entity_type": "activity"}

    apply_hierarchical_filter_config(
        config,
        {"filter_rules": {"input_filter": {"enabled": True}}},
        filter_loader=loader,
    )

    assert seen[2] == {"input_filter": {"enabled": True}}
