"""Closure rules for additive assay-target restoration."""

from __future__ import annotations

import json
from pathlib import Path

import orjson
import pyarrow as pa
import pytest
from deltalake import write_deltalake

from bioetl.infrastructure.storage.target_fk_restoration import (
    load_published_restoration,
    publish_target_fk_restoration,
)
from bioetl.infrastructure.storage.target_migration_classification_checks import (
    TargetRecoveryInput,
)
from bioetl.infrastructure.storage.target_migration_row_ops import read_delta
from iuphar_target_class.stage0.io import sha256_file

pytestmark = pytest.mark.unit

CONFIG = Path(__file__).resolve().parents[4] / "configs/entities/chembl/target.yaml"


def _row(target_id: str, *, layer: str, pref_name: str = "Known") -> dict[str, object]:
    row: dict[str, object] = {
        "target_id": target_id,
        "target_type": "SINGLE PROTEIN",
        "pref_name": pref_name,
        "organism": "Homo sapiens",
        "organism_class": "multicellular",
        "component_accessions": '["P12345"]',
        "component_ids": '["1"]',
        "component_types": '["PROTEIN"]',
    }
    if layer == "silver":
        row["target_description"] = "Receptor"
    else:
        row["description"] = "Receptor"
    return row


def _write_tables(root: Path, tables: dict[str, list[dict[str, object]]]) -> None:
    for name, rows in tables.items():
        write_deltalake(root / name, pa.Table.from_pylist(rows))


def _recovery(
    root: Path,
    row_id: str,
    gold: dict[str, object],
    silver: dict[str, object] | None,
) -> TargetRecoveryInput:
    payload: dict[str, object] = {"target_id": row_id, "gold": gold}
    if silver is not None:
        payload["silver"] = silver
    source = root / "recovery" / f"{row_id}.json"
    source.parent.mkdir(parents=True, exist_ok=True)
    source.write_bytes(orjson.dumps(payload, option=orjson.OPT_SORT_KEYS))
    return TargetRecoveryInput(
        row_id,
        "verified_pipeline_output",
        source.relative_to(root).as_posix(),
        source,
        sha256_file(source),
        silver,
        gold,
    )


def _publish(root: Path, recoveries: tuple[TargetRecoveryInput, ...]) -> Path:
    return publish_target_fk_restoration(
        silver=root / "silver",
        gold=root / "gold",
        assay=root / "assay",
        config=CONFIG,
        recoveries=recoveries,
        destination=root / "restoration",
        workspace=root,
    )


def test_incomplete_load_uses_persisted_silver_and_adds_gold_only(tmp_path: Path):
    existing = _row("CHEMBL1", layer="silver")
    persisted = _row("CHEMBL2605", layer="silver", pref_name="Adenosine receptor")
    gold_existing = _row("CHEMBL1", layer="gold")
    restored = _row("CHEMBL2605", layer="gold", pref_name="Adenosine receptor")
    _write_tables(
        tmp_path,
        {
            "silver": [existing, persisted],
            "gold": [gold_existing],
            "assay": [{"target_id": "CHEMBL1"}, {"target_id": "CHEMBL2605"}],
        },
    )
    manifest = _publish(tmp_path, (_recovery(tmp_path, "CHEMBL2605", restored, None),))
    document = orjson.loads(manifest.read_bytes())
    assert document["status"] == "validated_candidate"
    assert document["published_target_ids"] == {
        "silver": [],
        "gold": ["CHEMBL2605"],
    }
    silver_ids = {
        row["target_id"] for row in read_delta(tmp_path / "restoration/silver")
    }
    gold_ids = {row["target_id"] for row in read_delta(tmp_path / "restoration/gold")}
    assert silver_ids == {"CHEMBL1", "CHEMBL2605"}
    assert gold_ids == {"CHEMBL1", "CHEMBL2605"}
    assert (
        _publish(
            tmp_path, (_recovery(tmp_path, "CHEMBL2605", restored, None),)
        ).read_bytes()
        == manifest.read_bytes()
    )


def test_incomplete_load_reload_keeps_verified_source_silver(tmp_path: Path):
    persisted = _row("CHEMBL2605", layer="silver", pref_name="Adenosine receptor")
    restored = _row("CHEMBL2605", layer="gold", pref_name="Adenosine receptor")
    _write_tables(
        tmp_path,
        {
            "silver": [_row("CHEMBL1", layer="silver"), persisted],
            "gold": [_row("CHEMBL1", layer="gold")],
            "assay": [{"target_id": "CHEMBL1"}, {"target_id": "CHEMBL2605"}],
        },
    )
    manifest = _publish(
        tmp_path, (_recovery(tmp_path, "CHEMBL2605", restored, persisted),)
    )
    finding = orjson.loads(manifest.read_bytes())["findings"][0]
    assert finding["layers"] == ["gold"]
    assert "silver" not in finding["row_sha256"]
    published = load_published_restoration(
        manifest,
        workspace=tmp_path,
        silver=tmp_path / "silver",
        gold=tmp_path / "gold",
        assay=tmp_path / "assay",
        config=CONFIG,
    )
    assert published.additions["silver"] == ()
    assert [row["target_id"] for row in published.additions["gold"]] == ["CHEMBL2605"]


def test_supplied_silver_cannot_override_persisted_silver(tmp_path: Path):
    persisted = _row("CHEMBL2605", layer="silver", pref_name="Adenosine receptor")
    conflicting = _row("CHEMBL2605", layer="silver", pref_name="Other receptor")
    restored = _row("CHEMBL2605", layer="gold", pref_name="Other receptor")
    _write_tables(
        tmp_path,
        {
            "silver": [_row("CHEMBL1", layer="silver"), persisted],
            "gold": [_row("CHEMBL1", layer="gold")],
            "assay": [{"target_id": "CHEMBL1"}, {"target_id": "CHEMBL2605"}],
        },
    )
    with pytest.raises(ValueError, match="foreign-key closure"):
        _publish(
            tmp_path,
            (_recovery(tmp_path, "CHEMBL2605", restored, conflicting),),
        )
    decision = orjson.loads(
        (tmp_path / "restoration/contract-decision.json").read_bytes()
    )
    assert decision["blockers"] == [
        {"target_id": "CHEMBL2605", "absence_reason": "contract_mismatch"}
    ]
    assert not (tmp_path / "restoration/gold").exists()


def test_mixed_plan_records_the_blocker_without_publishing_rows(tmp_path: Path):
    base = _row("CHEMBL1", layer="gold")
    admissible_gold = _row("CHEMBL2237", layer="gold", pref_name="Adenosine receptor")
    admissible_silver = _row(
        "CHEMBL2237", layer="silver", pref_name="Adenosine receptor"
    )
    blocked = {**base, "target_id": "CHEMBL2411", "organism_class": "unicellular"}
    _write_tables(
        tmp_path,
        {
            "silver": [_row("CHEMBL1", layer="silver")],
            "gold": [base],
            "assay": [
                {"target_id": "CHEMBL1"},
                {"target_id": "CHEMBL2237"},
                {"target_id": "CHEMBL2411"},
            ],
        },
    )
    with pytest.raises(ValueError, match="foreign-key closure"):
        _publish(
            tmp_path,
            (
                _recovery(tmp_path, "CHEMBL2237", admissible_gold, admissible_silver),
                _recovery(tmp_path, "CHEMBL2411", blocked, blocked),
            ),
        )
    document = orjson.loads((tmp_path / "restoration/manifest.json").read_bytes())
    by_id = {item["target_id"]: item for item in document["findings"]}
    assert by_id["CHEMBL2237"]["row_sha256"] == {}
    assert by_id["CHEMBL2411"]["absence_reason"] == "gold_filter"
    assert document["status"] == "blocked"
    assert not (tmp_path / "restoration/gold").exists()


def test_source_identity_alone_does_not_prove_a_restored_row(tmp_path: Path):
    gold = _row("CHEMBL2237", layer="gold")
    silver = _row("CHEMBL2237", layer="silver")
    _write_tables(
        tmp_path,
        {
            "silver": [_row("CHEMBL1", layer="silver")],
            "gold": [_row("CHEMBL1", layer="gold")],
            "assay": [{"target_id": "CHEMBL1"}, {"target_id": "CHEMBL2237"}],
        },
    )
    source = tmp_path / "recovery/CHEMBL2237.json"
    source.parent.mkdir()
    source.write_bytes(b'{"target_id":"CHEMBL2237"}\n')
    with pytest.raises(ValueError, match="does not contain the restored gold row"):
        _publish(
            tmp_path,
            (
                TargetRecoveryInput(
                    "CHEMBL2237",
                    "verified_pipeline_output",
                    source.relative_to(tmp_path).as_posix(),
                    source,
                    sha256_file(source),
                    silver,
                    gold,
                ),
            ),
        )
    assert not (tmp_path / "restoration").exists()


def test_cli_forwards_restoration_manifest_only_to_freeze_and_prepare(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
):
    from scripts.ops import target_classification_migration as cli

    configs = tmp_path / "configs"
    configs.mkdir()
    monkeypatch.setattr(cli, "resolve_configs_root", lambda: configs)
    seen: dict[str, Path | None] = {}

    def freeze(
        paths,
        *,
        legacy_include_fields,
        output,
        source_profile,
        restoration_manifest=None,
    ):
        del paths, legacy_include_fields, output
        assert source_profile == "V30"
        seen["freeze"] = restoration_manifest

    def prepare(
        paths,
        *,
        legacy_include_fields,
        deployment,
        source_profile,
        destination_profile,
        restoration_manifest=None,
    ):
        del paths, legacy_include_fields, deployment
        assert (source_profile, destination_profile) == ("V30", "V31")
        seen["prepare"] = restoration_manifest
        return {"phase": "prepared"}

    monkeypatch.setattr(cli, "freeze_target_inputs", freeze)
    monkeypatch.setattr(cli, "prepare_target_migration", prepare)
    monkeypatch.setattr(cli, "bind_target_deployment", lambda paths: object())
    names = (
        "silver",
        "gold",
        "assay",
        "config",
        "candidate_silver",
        "candidate_gold",
        "candidate_config",
        "backup",
    )
    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps(
            {
                "paths": {
                    "workspace": str(tmp_path),
                    **{name: str(tmp_path / name) for name in names},
                },
                "legacy_include_fields": ["pref_name"],
                "source_profile": "V30",
                "destination_profile": "V31",
            }
        ),
        encoding="utf-8",
    )
    manifest = tmp_path / "fk/manifest.json"
    manifest.parent.mkdir()
    manifest.write_bytes(b"{}\n")
    cli.main(
        [
            "freeze-inputs",
            "--plan",
            str(plan),
            "--output",
            str(tmp_path / "frozen.json"),
            "--restoration-manifest",
            str(manifest),
        ]
    )
    cli.main(
        [
            "prepare",
            "--plan",
            str(plan),
            "--restoration-manifest",
            str(manifest),
        ]
    )
    assert seen["freeze"] == manifest.resolve()
    assert seen["prepare"] == manifest.resolve()
    with pytest.raises(SystemExit) as unsupported_action:
        cli.main(
            [
                "build-candidates",
                "--plan",
                str(plan),
                "--restoration-manifest",
                str(manifest),
            ]
        )
    assert unsupported_action.value.code == 2
    assert (
        "--restoration-manifest applies to freeze-inputs and prepare"
        in capsys.readouterr().err
    )
