"""Second tranche of behavioral tests for composition coverage residuals."""

from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from bioetl.composition.bootstrap.runtime.pipeline import (
    _coerce_optional_str,
    _fail_fast_empty_explicit_cached_bronze,
)
from bioetl.composition.factories import transformer_dependencies
from bioetl.composition.factories.datasource.http_client import HttpClientFactory
from bioetl.composition.factories.pipeline import (
    transformer_dependencies as pipeline_transformer_dependencies,
)
from bioetl.composition.factories.pipeline_support import (
    checkpoint_metadata_resolution,
    contract_validation_helpers,
)
from bioetl.composition.factories.services import _record_processor_policy_support
from bioetl.composition.providers import (
    _chembl_target_protein_classification_helpers as protein_helpers,
)
from bioetl.composition.providers import _store
from bioetl.composition.runtime_builders import (
    _effective_config_graph_support as graph_support,
)
from bioetl.composition.runtime_builders import (
    _effective_config_secret_support as secret_support,
)
from bioetl.composition.runtime_builders import (
    _effective_config_source_refs_support as source_ref_support,
)
from bioetl.composition.runtime_builders import (
    _run_manifest_sink_policy as sink_policy,
)
from bioetl.domain.ports.noop import NoOpPiiHasher


pytestmark = pytest.mark.unit


def test_cached_bronze_preflight_ignores_disabled_context() -> None:
    context = SimpleNamespace(cached_bronze=SimpleNamespace(enabled=False))

    assert _fail_fast_empty_explicit_cached_bronze(context) is None
    assert _coerce_optional_str(None) is None


@pytest.mark.parametrize(
    "module",
    [transformer_dependencies, pipeline_transformer_dependencies],
)
def test_composition_default_pii_hasher__uses_configured_salt(
    module: object,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    expected = Mock()
    factory = Mock(return_value=expected)
    monkeypatch.setattr(
        module, "load_settings", lambda: SimpleNamespace(pii_salt_current="salt")
    )
    monkeypatch.setattr(module.Sha256PiiHasher, "from_settings", factory)

    assert module._default_pii_hasher() is expected
    factory.assert_called_once()


def test_pipeline_transformer_hasher_falls_back_without_salt(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        pipeline_transformer_dependencies,
        "load_settings",
        lambda: SimpleNamespace(pii_salt_current=None),
    )

    assert isinstance(
        pipeline_transformer_dependencies._default_pii_hasher(),
        NoOpPiiHasher,
    )


def test_http_api_key_mapping_rejects_non_key_setting() -> None:
    assert HttpClientFactory._api_key_setting_name("BIOETL_TOKEN") is None


def test_checkpoint_context_and_snapshots_are_empty_without_runtime_services(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pipeline = SimpleNamespace(services=None, runtime=None)
    monkeypatch.setattr(
        checkpoint_metadata_resolution,
        "resolve_manifest_input_snapshot_refs",
        lambda **_kwargs: (),
    )
    monkeypatch.setattr(
        checkpoint_metadata_resolution,
        "get_settings",
        lambda: SimpleNamespace(),
    )

    assert checkpoint_metadata_resolution._resolve_run_context_payload(pipeline) is None
    assert checkpoint_metadata_resolution._resolve_input_snapshot_refs(pipeline) == ()


def test_transformer_reference_rejects_incomplete_and_wrong_class() -> None:
    with pytest.raises(ValueError, match="Invalid transformer class reference"):
        contract_validation_helpers._resolve_transformer_class_ref("NoModule")
    with pytest.raises(TypeError, match="must resolve to BaseTransformer"):
        contract_validation_helpers._resolve_transformer_class_ref(
            "types.SimpleNamespace"
        )


def test_record_processor_policy_normalizes_non_iterable_and_version_fallbacks() -> (
    None
):
    assert _record_processor_policy_support.coerce_string_frozenset(42) == frozenset()
    policy = SimpleNamespace(
        active_version="v2",
        rollout=SimpleNamespace(write_versions=("v1",), affects_hash=True),
        hash_datetime_policy="unsupported",
    )
    pipeline = SimpleNamespace(
        transformer=SimpleNamespace(_contract_policy=policy),
        gold_schema_by_version={},
    )

    hash_policy = _record_processor_policy_support.extract_hash_policy_by_version(
        pipeline,
        include_fields=frozenset({"id"}),
        exclude_fields=frozenset(),
    )
    schema = object()
    gold_policy = (
        _record_processor_policy_support.extract_gold_schema_policy_by_version(
            pipeline,
            gold_schema=schema,
        )
    )

    assert hash_policy is not None
    assert [item.version for item in hash_policy.policies] == ["v2", "v1"]
    assert hash_policy.policies[0].datetime_policy == "v2_datetime_utc"
    assert gold_policy is not None
    assert [item.version for item in gold_policy.policies] == ["v2", "v1"]
    assert all(item.schema is schema for item in gold_policy.policies)


def test_secret_hash_returns_none_for_missing_and_empty_secret() -> None:
    value_hash = Mock(return_value="hash")

    assert secret_support._secret_value_hash(None, value_hash) is None
    assert (
        secret_support._secret_value_hash(
            SimpleNamespace(get_secret_value=lambda: ""),
            value_hash,
        )
        is None
    )
    value_hash.assert_not_called()


@pytest.mark.parametrize(
    ("raw_value", "base_dir", "expected"),
    [
        ("pyproject.toml", "configs/providers", "pyproject.toml"),
        ("/configs/base/pipeline.yaml", "configs", None),
        (
            "configs/base/pipeline.yaml",
            "configs/providers",
            "configs/base/pipeline.yaml",
        ),
        ("../base/quality.yaml", "configs/providers", "configs/base/quality.yaml"),
        ("../../outside.yaml", "configs/providers", None),
        ("notes.txt", "configs", None),
        ("https://example.test/config.yaml", "configs", None),
    ],
)
def test_config_graph_reference_resolution_is_repo_bounded(
    raw_value: str,
    base_dir: str,
    expected: str | None,
) -> None:
    assert (
        graph_support._resolve_config_graph_reference(
            raw_value=raw_value,
            base_dir=base_dir,
        )
        == expected
    )


def test_missing_config_source_has_no_hash_identity(tmp_path: Path) -> None:
    assert source_ref_support._compute_file_hashes(
        relative_path="configs/missing.yaml",
        path=tmp_path / "missing.yaml",
    ) == (None, None, None, None, None)


def test_sink_idempotency_helpers_handle_proof_and_unsupported_values() -> None:
    proof = {"stable_partition_keys": ["date"]}
    assert (
        sink_policy._sink_layer_idempotency_evidence({"idempotency_proof": proof})
        == proof
    )
    assert not sink_policy._append_idempotency_evidence_present(
        yaml_config=SimpleNamespace(),
        layer_config={},
        contract="unknown",
    )
    assert sink_policy._text_items(42) == ()


def test_protein_classification_helpers_handle_absent_and_invalid_values() -> None:
    assert protein_helpers.target_ids_from_component_record({"targets": None}) == ()
    assert protein_helpers.leaf_ids_from_classification_objects(None) == ()
    assert protein_helpers.leaf_ids_from_value(None) == ()
    assert protein_helpers.leaf_ids_from_value(42) == ()
    assert protein_helpers.coerce_positive_int(None) is None
    assert protein_helpers.coerce_positive_int(True) is None
    assert protein_helpers.coerce_positive_int(1.5) is None
    assert protein_helpers.coerce_positive_int(" ") is None
    assert protein_helpers.coerce_positive_int("bad") is None
    assert protein_helpers._component_ids_from_component_ids_value(42) == ()
    assert protein_helpers._load_json_if_needed(" ") is None


def test_target_index_skips_rows_without_target_identity() -> None:
    by_target, by_component = protein_helpers.build_target_component_indexes(
        [{"component_ids": [1]}]
    )

    assert by_target == {}
    assert by_component == {}


def test_provider_store_compatibility_functions_cover_success_and_failure() -> None:
    config = SimpleNamespace(name="chembl")
    providers: dict[str, object] = {}

    _store.register_provider_config(providers, "chembl", config)

    assert _store.get_provider_config(providers, "chembl") is config
    assert _store.is_provider_registered(providers, "chembl")
    assert _store.list_provider_names({"pubchem": config, "chembl": config}) == [
        "chembl",
        "pubchem",
    ]
    with pytest.raises(KeyError, match="Unknown provider: missing.*chembl"):
        _store.get_provider_config(providers, "missing")
