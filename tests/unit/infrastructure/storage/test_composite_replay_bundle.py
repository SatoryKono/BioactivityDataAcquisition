"""ADR-062: Fail-closed integrity checks for the parent envelope and verification receipt."""

from __future__ import annotations

import json

import pyarrow as pa
import pytest

from bioetl.infrastructure.storage.composite_replay_bundle import (
    canonical_table,
    confined_path,
    digest_bytes,
    implementation_fingerprint,
    load_verified_json,
    publish_bytes,
    publish_json,
    verify_bundle,
)
from bioetl.infrastructure.storage.composite_replay_evidence import (
    project_assay_replay,
    replay_artifacts,
)


pytestmark = pytest.mark.unit


def test_target_mapping_round_trip_uses_captured_lookup(monkeypatch):
    from bioetl.application.composite.helpers.replay_context import (
        freeze_target_mapping,
        restore_target_mapping,
    )
    from bioetl.domain.mapping import protein_class_target_type as mapping

    original = mapping.ProteinClassTargetTypeMappingData(
        "captured-custom-v1",
        (mapping.ProteinClassTopLevelMappingEntry("enzyme", "custom-enzyme", True),),
        frozenset({"custom-ignored"}),
    )
    monkeypatch.setattr(mapping, "_mapping_data", original)
    payload = json.loads(json.dumps(freeze_target_mapping()))
    monkeypatch.setattr(mapping, "_mapping_data", None)
    restored = restore_target_mapping(payload)
    mapping.initialize_protein_class_target_type_mapping(restored)
    assert mapping.current_protein_class_target_type_mapping() == original
    assert (
        mapping.normalize_protein_class_top_level("enzyme").canonical_l1
        == "custom-enzyme"
    )


@pytest.mark.parametrize(
    "damage", ["absent", "missing", "changed", "invalid_structure"]
)
def test_target_requires_digest_bound_mapping(bundle, damage):
    root, envelope, _ = bundle
    envelope.update(version="composite-parent-replay-v2", pipeline="composite_target")
    envelope["objects"]["field-groups.json"] = publish_json(
        root, "field-groups.json", {}
    )
    if damage != "absent":
        envelope["objects"]["target-mapping.json"] = publish_json(
            root,
            "target-mapping.json",
            {
                "mapping_version": "captured-v1",
                "entries": [
                    {
                        "raw_label": "enzyme",
                        "canonical_l1": "enzyme",
                        "counts_for_target_type": True,
                    }
                ],
                "non_counting_classes": [],
            }
            if damage != "invalid_structure"
            else {},
        )
    path = root / "parent.json"
    path.write_text(json.dumps(envelope))
    digest = digest_bytes(path.read_bytes())
    if damage not in {"absent", "invalid_structure"}:
        assert verify_bundle(root, digest)["pipeline"] == "composite_target"
        if damage == "missing":
            (root / "target-mapping.json").unlink()
        else:
            (root / "target-mapping.json").write_bytes(b"changed")
    with pytest.raises((ValueError, FileNotFoundError)):
        verify_bundle(root, digest)


@pytest.mark.parametrize(
    "damage", ["version", "empty", "duplicate", "ignored", "entry_type", "boolean"]
)
def test_sealed_target_mapping_must_restore_domain_invariants(bundle, damage):
    root, envelope, _ = bundle
    entry = {
        "raw_label": "enzyme",
        "canonical_l1": "enzyme",
        "counts_for_target_type": True,
    }
    mapping = {"mapping_version": "v1", "entries": [entry], "non_counting_classes": []}
    if damage == "version":
        mapping["mapping_version"] = " "
    elif damage == "empty":
        mapping["entries"] = []
    elif damage == "duplicate":
        mapping["entries"] = [entry, dict(entry, raw_label=" ENZYME ")]
    elif damage == "ignored":
        mapping["non_counting_classes"] = "not-an-array"
    elif damage == "entry_type":
        mapping["entries"] = ["not-an-object"]
    else:
        entry["counts_for_target_type"] = "false"
    envelope.update(version="composite-parent-replay-v2", pipeline="composite_target")
    for name, value in (("field-groups.json", {}), ("target-mapping.json", mapping)):
        envelope["objects"][name] = publish_json(root, name, value)
    (root / "parent.json").write_text(json.dumps(envelope))
    with pytest.raises(ValueError):
        verify_bundle(root, digest_bytes((root / "parent.json").read_bytes()))


@pytest.fixture
def bundle(tmp_path):
    root = tmp_path / "pipeline/composite_assay/run/replay"
    objects = {}
    for name in (
        "config.json",
        "uv.lock",
        "pipeline-settings.json",
        "expected/silver.arrow",
        "expected/gold.arrow",
        "inputs/inputs.json",
    ):
        objects[name] = publish_bytes(root, name, b"{}")
    envelope = {
        "version": "assay-parent-replay-v1",
        "pipeline": "composite_assay",
        "run_id": "run",
        "implementation": implementation_fingerprint(),
        "objects": objects,
        "input_snapshot_fingerprint": objects["inputs/inputs.json"],
    }
    digest = publish_json(root, "parent.json", envelope)
    output_hash = publish_bytes(
        root, "verification/output/table.parquet", b"physical output"
    )
    publish_json(
        root,
        "verification/verification.json",
        {
            "version": "assay-replay-verification-v1",
            "run_id": "run",
            "envelope_sha256": digest,
            "silver_equal": True,
            "gold_equal": True,
            "objects": {"output/table.parquet": output_hash},
        },
    )
    return root, envelope, digest


def test_v2_requires_captured_field_groups_and_preserves_their_digest(bundle):
    root, envelope, _ = bundle
    envelope.update(
        version="composite-parent-replay-v2", pipeline="composite_publication"
    )
    path = root / "parent.json"
    path.write_text(json.dumps(envelope))
    with pytest.raises(ValueError, match="required_object_missing"):
        verify_bundle(root, digest_bytes(path.read_bytes()))
    envelope["objects"]["field-groups.json"] = publish_json(
        root, "field-groups.json", {"registry": None}
    )
    path.write_text(json.dumps(envelope))
    digest = digest_bytes(path.read_bytes())
    assert verify_bundle(root, digest)["pipeline"] == "composite_publication"
    (root / "field-groups.json").write_text('{"registry":{}}')
    with pytest.raises(ValueError, match="object_digest_mismatch"):
        verify_bundle(root, digest)


def test_field_group_round_trip_keeps_custom_defaults_and_gold_filtering():
    from bioetl.application.composite.helpers.replay_context import (
        freeze_field_groups,
        restore_field_groups,
    )
    from bioetl.domain.composite.field_groups import (
        FieldGroupRegistry,
        FieldGroupId,
        FieldGroupDefinition,
        FieldMapping,
    )

    assert restore_field_groups(freeze_field_groups(None)) is None
    group_id = next(group for group in FieldGroupId if group != FieldGroupId.TRASH)
    original = FieldGroupRegistry(
        groups=(
            FieldGroupDefinition(
                group_id,
                "Excluded",
                False,
                (FieldMapping("title", ("chembl.publication.title",), group_id),),
            ),
        ),
        provider_order=("openalex", "chembl"),
        default_group=group_id,
    )
    restored = restore_field_groups(
        json.loads(json.dumps(freeze_field_groups(original)))
    )
    assert restored.groups == original.groups
    assert restored.provider_order == original.provider_order
    assert restored.default_group == original.default_group
    assert restored.get_gold_columns(
        ["chembl.publication.title", "unmapped", "_run_id"]
    ) == ["_run_id"]


@pytest.mark.parametrize(
    "path,layer,expected",
    [
        ("data/output/silver/composite/activity", "silver", "composite/activity"),
        ("gold\\composite\\target", "gold", "composite/target"),
        ("composite/molecule", "gold", "composite/molecule"),
    ],
)
def test_replay_output_path_matches_writer(path, layer, expected):
    from bioetl.application.composite.helpers.replay_context import (
        output_table_name,
    )

    assert output_table_name(path, layer) == expected


@pytest.mark.parametrize(
    "damage",
    [
        "version",
        "pipeline",
        "objects",
        "required",
        "fingerprint",
        "implementation",
        "object_digest",
        "missing",
        "envelope_digest",
        "escape",
    ],
)
def test_envelope_damage_never_admits(bundle, damage):
    root, envelope, digest = bundle
    if damage in {"version", "pipeline", "implementation"}:
        envelope[damage] = "invalid"
    elif damage == "objects":
        envelope["objects"] = {}
    elif damage == "required":
        del envelope["objects"]["uv.lock"]
    elif damage == "fingerprint":
        envelope["input_snapshot_fingerprint"] = "wrong"
    elif damage == "object_digest":
        envelope["objects"]["uv.lock"] = "wrong"
    elif damage == "escape":
        envelope["objects"]["../foreign"] = "wrong"
    elif damage == "missing":
        (root / "uv.lock").unlink()
    content = json.dumps(envelope).encode()
    (root / "parent.json").write_bytes(content)
    digest = "wrong" if damage == "envelope_digest" else digest_bytes(content)
    with pytest.raises((ValueError, FileNotFoundError)):
        verify_bundle(root, digest)


@pytest.mark.parametrize(
    "damage",
    [
        "missing_receipt",
        "bad_receipt",
        "missing_output",
        "changed_output",
        "parent_identity",
        "duplicate_parent",
        "absent_manifest",
    ],
)
def test_http_projection_rechecks_every_replay_object(bundle, damage):
    root, _, _ = bundle
    artifacts = replay_artifacts(root.parents[3], "composite_assay", "run")
    assert artifacts
    manifest = {"objects": {"effective_config_hash": False}}
    upgraded, probe = project_assay_replay(
        root.parent, "run", {"artifacts": list(artifacts)}, manifest
    )
    assert probe["result"] == "pass"
    assert upgraded["objects"]["effective_config_hash"] is False
    receipt = root / "verification/verification.json"
    if damage == "missing_receipt":
        receipt.unlink()
    elif damage == "bad_receipt":
        receipt.write_bytes(b"bad")
    elif damage == "missing_output":
        (root / "verification/output/table.parquet").unlink()
    elif damage == "changed_output":
        (root / "verification/output/table.parquet").write_bytes(b"changed")
    elif damage == "duplicate_parent":
        artifacts += tuple(
            item for item in artifacts if item["kind"] == "composite_exact_replay"
        )
    selected_id = "other" if damage == "parent_identity" else "run"
    _, probe = project_assay_replay(
        root.parent,
        selected_id,
        {"artifacts": list(artifacts)},
        None if damage == "absent_manifest" else manifest,
    )
    assert probe["result"] == "fail"


def test_unsealed_envelope_and_other_families_do_not_upgrade(tmp_path):
    assert replay_artifacts(None, "composite_assay", "run") == ()
    assert replay_artifacts(tmp_path, "composite_activity", "run") == ()
    assert replay_artifacts(tmp_path, "composite_assay", "run") == ()
    assert project_assay_replay(tmp_path, "run", {}, None) == (None, None)
    with pytest.raises(ValueError, match="path_escape"):
        confined_path(tmp_path, "../outside")
    with pytest.raises(ValueError, match="path_escape"):
        confined_path(tmp_path, str(tmp_path / "absolute"))
    digest = publish_bytes(tmp_path, "array.json", b"[]")
    with pytest.raises(ValueError, match="envelope_invalid"):
        load_verified_json(tmp_path, "array.json", digest)
    with pytest.raises(FileExistsError):
        publish_bytes(tmp_path, "array.json", b"changed")
    with pytest.raises(ValueError, match="identity_missing"):
        canonical_table(pa.table({"other": [1]}))


def test_cli_rejects_wrong_envelope_and_digest(tmp_path):
    from click.testing import CliRunner
    from bioetl.interfaces.cli.commands.replay_assay import replay_assay_command

    path = tmp_path / "wrong.json"
    path.write_text("{}")
    runner = CliRunner()
    args = [
        "--envelope",
        str(path),
        "--sha256",
        "wrong",
        "--output",
        str(tmp_path / "output"),
    ]
    assert runner.invoke(replay_assay_command, args).exit_code == 1
    path.rename(tmp_path / "parent.json")
    args[1] = str(tmp_path / "parent.json")
    result = runner.invoke(replay_assay_command, args)
    assert result.exit_code == 1
    assert "digest_mismatch" in result.output
    assert not (tmp_path / "output").exists()


@pytest.mark.asyncio
async def test_capture_requires_report_root_and_active_request(tmp_path):
    from types import SimpleNamespace
    from unittest.mock import AsyncMock
    from bioetl.composition.bootstrap.runtime.assay_replay_capture import (
        prepare_assay_replay,
    )
    from bioetl.infrastructure.config.composite_config_api import load_composite_config
    from bioetl.infrastructure.observability.noop_logger import NoOpLogger

    config = load_composite_config("assay")
    kwargs = {
        "config": config,
        "reader": AsyncMock(),
        "storage": AsyncMock(),
        "logger": NoOpLogger(),
    }
    with pytest.raises(ValueError, match="report_root"):
        prepare_assay_replay(**kwargs, settings=SimpleNamespace(report_root=None))
    reader, _ = prepare_assay_replay(
        **kwargs, settings=SimpleNamespace(report_root=tmp_path)
    )
    for method in (reader.get_schema, reader.get_row_count, reader.table_exists):
        with pytest.raises(KeyError):
            await method("uncaptured")
    await reader.aclose()
