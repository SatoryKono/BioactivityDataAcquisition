"""Smoke coverage for modules missing from the July coverage XML snapshot."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

pytestmark = [pytest.mark.unit]


def test_chembl_policy_family_mapping_indexes_by_name() -> None:
    from bioetl.domain.normalization.profiles._chembl_policy_family_mapping import (
        family_mapping_by_name,
    )

    family = SimpleNamespace(family_name="activity")
    mapping = family_mapping_by_name([family])
    assert mapping["activity"] is family


def test_normalization_helpers_identity_and_hash_refs() -> None:
    from bioetl.domain.normalization.profiles import _normalization_helpers as helpers

    assert helpers._identity("x") == "x"
    assert helpers._normalizer_ref(helpers._identity).endswith(":_identity")
    assert len(helpers._sha256_hex({"a": 1})) == 64
    assert helpers._stable_value({"b": 2, "a": 1}) == {"a": 1, "b": 2}


def test_profile_validation_normalizes_and_rejects_shadow_aliases() -> None:
    from bioetl.domain.normalization.profiles._profile_validation import (
        _normalize_field_aliases,
        _normalize_profile_contract,
        _validate_field_aliases,
    )
    from bioetl.domain.normalization.profiles.base import FieldRule

    rule = FieldRule(field_name="chembl_id")
    field_rules = {"chembl_id": rule}
    aliases = {"molecule_chembl_id": "chembl_id"}
    normalized_rules, normalized_aliases = _normalize_profile_contract(
        field_rules=field_rules,
        field_aliases=aliases,
        meta_fields=frozenset(),
    )
    assert normalized_rules == field_rules
    assert normalized_aliases == _normalize_field_aliases(aliases)
    with pytest.raises(ValueError, match="cannot shadow"):
        _validate_field_aliases(
            field_rules=field_rules,
            field_aliases={"chembl_id": "chembl_id"},
        )


def test_workflow_config_fk_helpers_validate_pairs() -> None:
    from bioetl.infrastructure.schemas import workflow_config_fk as fk

    assert fk._normalize_fk_required_name(" molecule_id ", "source_key") == "molecule_id"
    assert fk._normalize_fk_optional_name(None, "source_key") is None
    assert fk._normalize_fk_required_names(["a", "b"], "source_keys") == ["a", "b"]
    with pytest.raises(ValueError, match="cannot contain duplicates"):
        fk._normalize_fk_required_names(["a", "a"], "source_keys")
    fk._require_fk_key_pairs_present(
        source_key="a",
        reference_key="b",
        source_keys=None,
        reference_keys=None,
    )
    with pytest.raises(ValueError, match="together"):
        fk._require_fk_key_pairs_together(
            source_key="a",
            reference_key=None,
            source_keys=None,
            reference_keys=None,
        )
    fk._require_matching_key_prefix("a", ["a", "b"], field_label="source_key")


def test_health_failure_handling_delegates_to_boundary_policy() -> None:
    from bioetl.interfaces.cli.commands.domains.health import failure_handling as fh

    with (
        patch.object(fh, "build_target_cli_boundary_policy") as build_policy,
        patch.object(fh, "handle_boundary_cli_failure") as handle_failure,
    ):
        build_policy.return_value = MagicMock(name="policy")
        fh.handle_health_failure(
            RuntimeError("boom"),
            reason_code="HEALTH_PROBE_DOMAIN_ERROR",
            target="health",
            domain_error_title="domain",
            unexpected_error_title="unexpected",
            interrupted_message="interrupted",
        )
        build_policy.assert_called_once()
        handle_failure.assert_called_once()
        assert handle_failure.call_args.kwargs["reason_suffix"] == "DOMAIN_ERROR"


def test_observability_backend_startup_types_are_importable() -> None:
    # Protocol/TypedDict module: exercise import-time definitions.
    from bioetl.interfaces.cli.commands.domains.health import (
        _observability_backend_startup_types as types,
    )

    assert types._MessagePrinter is not None
    assert types._StartFn is not None


def test_pipeline_bootstrap_lazy_dependencies_delegate() -> None:
    from bioetl.composition.bootstrap.runtime import (
        _pipeline_bootstrap_lazy_dependencies as lazy,
    )
    from pathlib import Path

    with patch(
        "bioetl.composition.bootstrap.runtime.normalization_policy_init."
        "initialize_chembl_policy_registry"
    ) as init_chembl:
        lazy.initialize_chembl_policy_registry(Path("configs"))
        init_chembl.assert_called_once_with(Path("configs"))

    with patch(
        "bioetl.composition.factories.pipeline.registry.register_all_pipelines"
    ) as register_all:
        lazy.register_all_pipelines()
        register_all.assert_called_once()
