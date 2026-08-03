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
"""RunManifest payload immutability tests."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

import pytest

from bioetl.domain.control_plane.run_manifest import RunCodeProvenance, RunManifest
from bioetl.domain.types import RunID, RunType


pytestmark = pytest.mark.unit


def _make_manifest(
    *,
    launch_context: dict[str, object] | None = None,
    runtime_config: dict[str, object] | None = None,
    resolved_config: dict[str, object] | None = None,
) -> RunManifest:
    return RunManifest(
        manifest_id="manifest_immutable",
        execution_fingerprint="exec_fingerprint_immutable",
        schema_version="1.0",
        created_at=datetime(2023, 1, 1, 12, 0, 0),
        run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
        run_type=RunType.INCREMENTAL,
        pipeline_name="chembl_activity",
        provider="chembl",
        entity="activity",
        launch_context=launch_context or {},
        runtime_config=runtime_config or {},
        resolved_config=resolved_config or {},
        code_provenance=RunCodeProvenance(config_hash="config_hash_123"),
    )


def test_run_manifest_payloads_are_isolated_from_caller_mutation() -> None:
    launch_context = {
        "argv": ["run", "chembl_activity"],
        "flags": {"exact_replay": True},
    }
    runtime_config = {
        "pipeline": {
            "steps": ["extract", "transform"],
            "thresholds": {"soft": 5},
        },
        "profiles": {"local", "replay"},
    }
    resolved_config = {
        "providers": [{"name": "chembl", "enabled": True}],
    }

    manifest = _make_manifest(
        launch_context=launch_context,
        runtime_config=runtime_config,
        resolved_config=resolved_config,
    )
    snapshot = manifest.to_dict()

    launch_context["argv"].append("--debug")
    launch_context["flags"]["exact_replay"] = False  # type: ignore[index]
    runtime_config["pipeline"]["steps"].append("load")  # type: ignore[index, union-attr]
    runtime_config["pipeline"]["thresholds"]["soft"] = 99  # type: ignore[index]
    runtime_config["profiles"].add("mutated")  # type: ignore[union-attr]
    resolved_config["providers"][0]["enabled"] = False  # type: ignore[index]

    assert manifest.to_dict() == snapshot


def test_run_manifest_payloads_reject_mutation_through_manifest() -> None:
    manifest = _make_manifest(
        runtime_config={
            "pipeline": {
                "steps": ["extract"],
                "thresholds": {"soft": 5},
            },
            "profiles": {"local"},
        }
    )

    nested_pipeline = manifest.runtime_config["pipeline"]
    assert isinstance(nested_pipeline, dict)

    with pytest.raises(TypeError, match="immutable"):
        manifest.runtime_config["pipeline"] = {}
    with pytest.raises(TypeError, match="immutable"):
        nested_pipeline["steps"] = []
    with pytest.raises(AttributeError):
        manifest.runtime_config["pipeline"]["steps"].append("load")  # type: ignore[index, union-attr]
    with pytest.raises(AttributeError):
        manifest.runtime_config["profiles"].add("mutated")  # type: ignore[union-attr]


def test_run_manifest_to_dict_returns_mutable_json_shape_without_aliasing() -> None:
    manifest = _make_manifest(
        runtime_config={
            "pipeline": {
                "steps": ["extract"],
                "thresholds": {"soft": 5},
            }
        }
    )

    payload = manifest.to_dict()

    assert isinstance(payload["runtime_config"], dict)
    assert isinstance(payload["runtime_config"]["pipeline"], dict)  # type: ignore[index]
    assert isinstance(payload["runtime_config"]["pipeline"]["steps"], list)  # type: ignore[index]

    payload["runtime_config"]["pipeline"]["steps"].append("mutated")  # type: ignore[index, union-attr]
    assert manifest.to_dict()["runtime_config"]["pipeline"]["steps"] == ["extract"]  # type: ignore[index]


def test_run_manifest_round_trip_keeps_canonical_payload_snapshot() -> None:
    manifest = _make_manifest(
        launch_context={"resume": True},
        runtime_config={"pipeline": {"steps": ["extract"]}},
        resolved_config={"loading_strategy": "replace"},
    )
    payload = manifest.to_dict()

    loaded_manifest = RunManifest.from_dict(payload)

    assert loaded_manifest.to_dict() == payload
    assert loaded_manifest == manifest


@pytest.mark.parametrize(
    ("field_name", "value"),
    [
        ("manifest_id", ""),
        ("execution_fingerprint", " "),
        ("schema_version", ""),
        ("pipeline_name", ""),
        ("provider", ""),
        ("entity", ""),
    ],
)
def test_run_manifest_requires_mandatory_identity_fields(
    field_name: str,
    value: str,
) -> None:
    kwargs = {field_name: value}

    with pytest.raises(ValueError, match=f"RunManifest.{field_name}"):
        RunManifest(
            manifest_id=kwargs.get("manifest_id", "manifest_immutable"),
            execution_fingerprint=kwargs.get(
                "execution_fingerprint",
                "exec_fingerprint_immutable",
            ),
            schema_version=kwargs.get("schema_version", "1.0"),
            created_at=datetime(2023, 1, 1, 12, 0, 0),
            run_id=RunID(UUID("12345678-1234-5678-1234-567812345678")),
            run_type=RunType.INCREMENTAL,
            pipeline_name=kwargs.get("pipeline_name", "chembl_activity"),
            provider=kwargs.get("provider", "chembl"),
            entity=kwargs.get("entity", "activity"),
            launch_context={},
            runtime_config={},
            resolved_config={},
            code_provenance=RunCodeProvenance(config_hash="config_hash_123"),
        )
