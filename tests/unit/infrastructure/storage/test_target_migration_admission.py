"""Full target migration admission rejects forged identities and decisions."""

from __future__ import annotations

from pathlib import Path
from datetime import UTC, datetime

import click
import pyarrow as pa
import pytest
import yaml
from deltalake import write_deltalake
from pandera.errors import SchemaErrors

from bioetl.application.core.record_normalization_processor import (
    RecordNormalizationProcessor,
)
from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from bioetl.domain.contracts.gold.chembl_target_classification import (
    ChEMBLTargetGoldSchemaV31,
)
from bioetl.domain.normalization.profiles.chembl_target import CHEMBL_TARGET_PROFILE
from bioetl.domain.normalization.profiles.chembl_target_classification import (
    target_v31_normalization_profile,
)
from bioetl.infrastructure.adapters.iuphar.adapter import (
    IupharTargetClassificationAdapter,
)
from bioetl.infrastructure.adapters.iuphar.snapshot_loader import (
    LoadedIupharProfile,
    LoadedIupharSnapshot,
)
from bioetl.infrastructure.storage import target_migration_validation as validation
from bioetl.infrastructure.storage.target_migration_row_ops import (
    hash_input,
    scoped_target_hash,
)
from bioetl.infrastructure.storage.target_classification_guard import (
    assert_target_table_compatibility,
)
from bioetl.interfaces.cli.commands.run_composite import run_composite
from iuphar_target_class.matching import CatalogTarget
from iuphar_target_class.models import ProviderAnnotation
from iuphar_target_class.pipeline import IndexedSnapshot
from iuphar_target_class.snapshot import Completeness
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_bytes

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[4]


@pytest.mark.parametrize("directory", ["--list-only", "--help", "--dry-run"])
def test_composite_cached_path_value_does_not_mark_a_writer_as_preview(
    directory: str,
):
    args = ["run-composite", "--composite=target", "--cached-bronze-path", directory]

    assert validation._managed_writer_command(["bioetl", *args])
    assert not validation._managed_writer_command(["bioetl", *args, "--dry-run"])


def test_composite_guard_consumes_each_value_taking_cli_option():
    expected = {
        name
        for param in run_composite.params
        if isinstance(param, click.Option) and not param.is_flag
        for name in param.opts
    }

    assert expected <= validation._WRITER_VALUE_OPTIONS


@pytest.mark.parametrize(
    "argv",
    [
        ["python.exe", "-m", "bioetl", "run", "--pipeline", "chembl_target"],
        ["python", "-m", "bioetl.interfaces.cli", "run", "--pipeline", "chembl_target"],
        ["python", "-m", "bioetl.interfaces.cli", "workflow", "run", "chembl_baseline"],
        ["D:/repo/.venv/Scripts/bioetl.exe", "run", "--pipeline=chembl_target"],
        ["bioetl.exe", "workflow", "run", "chembl_baseline"],
        ["bioetl", "run", "chembl_target"],
        [
            "bioetl",
            "run",
            "--pipeline",
            "chembl_target",
            "--debug-export-dir",
            "--dry-run",
        ],
        ["bioetl", "run", "--pipeline=chembl_target", "--debug-export-dir", "--help"],
        ["bioetl", "workflow", "run", "baseline", "--debug-export-dir", "-h"],
        [
            "bioetl",
            "run-composite",
            "--composite",
            "target",
            "--cached-bronze-path",
            "--list-only",
        ],
        [
            "bioetl",
            "run-composite",
            "--composite",
            "target",
            "--cached-bronze-path",
            "--dry-run",
        ],
        ["bioetl", "workflow", "run", "--", "--help"],
        ["bioetl", "debug", "--pipeline", "chembl_target"],
        ["bioetl", "debug", "--pipeline=chembl_target"],
        ["python", "-m", "bioetl", "debug", "--pipeline", "chembl_target"],
        ["python", "-m", "bioetl.interfaces.cli", "debug", "--pipeline=chembl_target"],
        ["bioetl", "run-composite", "--composite", "target"],
        ["bioetl", "run-composite", "--composite=target"],
        ["python", "-m", "bioetl", "run-composite", "--composite", "target"],
        ["bioetl", "run-composite", "--composite", "operator_profile"],
        ["bioetl", "run-all", "--source", "chembl"],
        ["bioetl", "--", "run-all", "--source=chembl"],
        ["bioetl", "run-all", "--source=pubchem", "--source", "chembl"],
        [
            "bioetl",
            "run",
            "--pipeline",
            "chembl_target",
            "--debug-export",
            "--debug-export-dir",
            "run-all",
        ],
        ["bioetl.exe", "run-all", "--source=chembl"],
        ["python", "-m", "bioetl", "run-all", "--source", "chembl"],
        ["python", "-m", "bioetl", "run-all", "--source=chembl"],
        ["python", "-m", "bioetl.interfaces.cli", "run-all", "--source", "chembl"],
        ["python", "-m", "bioetl.interfaces.cli", "run-all", "--source=chembl"],
        ["python", "D:/repo/reports/workflow-campaigns/runner.py"],
    ],
)
def test_managed_writer_detection_recognizes_actual_argv(argv, monkeypatch):
    from types import SimpleNamespace

    monkeypatch.setattr(
        validation.psutil,
        "process_iter",
        lambda _: [SimpleNamespace(info={"pid": -1, "cmdline": argv})],
    )
    with pytest.raises(RuntimeError, match="managed writer"):
        validation.assert_no_managed_writers()


@pytest.mark.parametrize(
    "argv",
    [
        ["bioetl", "run", "--pipeline", "chembl_target", "--dry-run"],
        ["bioetl", "workflow", "run", "--help"],
        ["bioetl", "run", "--pipeline", "chembl_assay"],
        ["python", "unrelated.py", "run", "chembl_target"],
        ["python", "unrelated.py", "bioetl.interfaces.cli", "run", "chembl_target"],
        ["python", "-m", "bioetl.interfaces.cli", "workflow", "run", "--help"],
        ["bioetl", "workflow", "list"],
        ["bioetl", "debug", "--pipeline", "chembl_target", "--help"],
        ["bioetl", "debug", "--pipeline=chembl_target", "-h"],
        ["bioetl", "debug", "--pipeline", "pubchem_compound"],
        ["bioetl", "run-composite", "--composite", "target", "--dry-run"],
        ["bioetl", "run-composite", "--composite=target", "--help"],
        ["python", "unrelated.py", "debug", "--pipeline=chembl_target"],
        [
            "bioetl",
            "run-composite",
            "--composite",
            "target",
            "--cached-bronze-path",
            "--list-only",
            "--dry-run",
        ],
        ["bioetl", "run-all", "--source", "chembl", "--dry-run"],
        ["bioetl", "run-all", "--source=chembl", "--list-only"],
        ["bioetl", "run-all", "--source", "chembl", "--help"],
        ["bioetl", "run-all", "--source=chembl", "-h"],
        ["bioetl", "run-all", "--source", "pubchem"],
        ["bioetl", "run-all", "--source", "chembl", "--source=pubchem"],
        ["bioetl", "run-all", "--source=chembl", "--source", "pubchem"],
        ["bioetl", "run-all", "--source=chembl_similar"],
        ["bioetl", "run-all"],
        ["python", "unrelated.py", "run-all", "--source", "chembl"],
    ],
)
def test_read_only_and_unrelated_commands_do_not_block_migration(argv):
    assert validation._managed_writer_command(argv) is False


@pytest.mark.parametrize(
    ("command_path", "arguments", "value_key", "value"),
    [
        (
            ("run",),
            ["--pipeline", "chembl_target", "--debug-export-dir", "--dry-run"],
            "debug_export_dir",
            "--dry-run",
        ),
        (
            ("workflow", "run"),
            ["baseline", "--debug-export-dir", "-h"],
            "debug_export_dir",
            "-h",
        ),
        (
            ("run-composite",),
            ["--composite", "target", "--cached-bronze-path", "--list-only"],
            "cached_bronze_path",
            "--list-only",
        ),
    ],
)
def test_writer_guard_respects_click_option_values(
    command_path, arguments, value_key, value
):
    """Parse real maintained options without invoking callbacks or a runner."""
    import click
    from bioetl.interfaces.cli import cli

    command = cli
    for name in command_path:
        command = command.get_command(click.Context(command), name)
    options, _, _ = command.make_parser(click.Context(command)).parse_args(
        list(arguments)
    )
    assert options[value_key] == value
    assert not options.get("dry_run")
    assert validation._managed_writer_command(["bioetl", *command_path, *arguments])


def test_writer_guard_value_options_cover_maintained_cli():
    """A new valued CLI option must not bypass writer admission as a flag."""
    import click
    from bioetl.interfaces.cli import cli

    paths = [
        ("run",),
        ("debug",),
        ("run-all",),
        ("run-composite",),
        ("workflow", "run"),
    ]
    for path in paths:
        command = cli
        for name in path:
            command = command.get_command(click.Context(command), name)
        value_options = {
            option
            for parameter in command.params
            if isinstance(parameter, click.Option) and not parameter.is_flag
            for option in parameter.opts
        }
        assert value_options <= validation._WRITER_VALUE_OPTIONS


def _synthetic_profile(tmp_path: Path) -> LoadedIupharProfile:
    """Explicit software fixture; this is not a biological acceptance receipt."""
    raw = canonical_json_bytes({"targetId": 1, "type": "gpcr"}).decode()
    snapshot = IndexedSnapshot.build(
        snapshot_id="migration-fixture",
        mapping_version="synthetic-mapping",
        complete=True,
        catalog=(
            CatalogTarget("1", ("P12345",), None, None, "9606", ("Fixture",), ()),
        ),
        annotations={
            "1": ProviderAnnotation(
                "1", "gpcr", (), sha256_bytes(raw.encode()), "9606", raw
            )
        },
        family_nodes=(),
        type_to_class={"gpcr": "Receptor"},
        family_to_class={},
    )
    loaded = LoadedIupharSnapshot(
        snapshot,
        Completeness(True, True, False, True, "synthetic fixture"),
        "b" * 64,
        (tmp_path / "snapshot.json").as_uri(),
        "2026-11-16T00:00:00+00:00",
        frozenset({"9606"}),
        {},
    )
    return LoadedIupharProfile(
        loaded,
        "a" * 64,
        (tmp_path / "profile.json").as_uri(),
        "c" * 64,
        "bioetl-iuphar-input-v1",
        "plan-v1-r9",
        "3.1.0",
    )


def _processor(
    fields: tuple[str, ...], *, enrich: bool
) -> RecordNormalizationProcessor:
    return RecordNormalizationProcessor(
        provider="chembl",
        entity_type="target",
        profile=target_v31_normalization_profile() if enrich else CHEMBL_TARGET_PROFILE,
        content_hash_policy_authoritative=True,
        content_hash_include_fields=frozenset(fields),
    )


def _old_row(target_id: str, fields: tuple[str, ...]) -> dict[str, object]:
    row = {
        "target_id": target_id,
        "entity_id": "chembl:" + target_id,
        "content_hash": "0" * 64,
        "target_type": "SINGLE PROTEIN",
        "pref_name": "Fixture",
        "organism": "Homo sapiens",
        "taxonomy_id": 9606,
        "organism_class": None,
        "species_group_flag": False,
        "component_accessions": '["P12345"]',
        "target_description": None,
        "_run_id": "synthetic-old-run",
        "_run_type": "backfill",
        "_ingestion_ts": "2026-11-16T00:00:00+00:00",
        "_index": 0,
        "_dq_warn": False,
        "_dq_error": False,
    }
    return _processor(fields, enrich=False).normalize_record(row)


def _gold(row: dict[str, object]) -> dict[str, object]:
    source = {
        **row,
        "description": row.get("target_description"),
        "taxonomy_id": 9606.0,
    }
    return {
        field: source.get(field)
        for field in ChEMBLTargetGoldSchemaV31.to_schema().columns
        if field not in TARGET_CLASSIFICATION_FIELDS or field in row
    }


@pytest.fixture
def admitted_candidate(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    config = yaml.safe_load((ROOT / "configs/entities/chembl/target.yaml").read_text())
    fields = tuple(config["hash_policy"]["hash_policy"]["include_fields"])
    config_path = tmp_path / "target.yaml"
    config_path.write_text(yaml.safe_dump(config), encoding="utf-8")
    paths = {
        name: tmp_path / name
        for name in ("silver", "gold", "assay", "candidate_silver", "candidate_gold")
    }
    paths["config"] = config_path
    profile = _synthetic_profile(tmp_path)
    classifier = IupharTargetClassificationAdapter(profile)
    old_silver = [_old_row("CHEMBL1", fields), _old_row("CHEMBL2", fields)]
    new_silver = []
    v31_fields = (*fields, *TARGET_CLASSIFICATION_FIELDS)
    for row in old_silver:
        result = classifier.classify_record(
            row,
            input_row_id="fixture:" + str(row["target_id"]),
            run_id="synthetic-candidate",
            run_started_at="2026-11-16T00:00:00+00:00",
        )
        candidate = {**row, **result.projection}
        candidate["content_hash"] = _processor(
            v31_fields, enrich=True
        ).compute_content_hash(candidate)
        new_silver.append(candidate)
    tables = {
        paths["silver"]: old_silver,
        paths["gold"]: [_gold(old_silver[0])],
        paths["candidate_silver"]: new_silver,
        paths["candidate_gold"]: [_gold(new_silver[0])],
        paths["assay"]: [{"target_id": "CHEMBL1"}, {"target_id": None}],
    }
    monkeypatch.setattr(
        validation, "_load_candidate_profile", lambda *_args, **_kwargs: profile
    )
    monkeypatch.setattr(validation, "_read_delta", lambda path: tables[path])
    from bioetl.infrastructure.storage import target_migration_classification_checks

    monkeypatch.setattr(
        target_migration_classification_checks, "read_delta", lambda path: tables[path]
    )
    return paths, fields, tables


def test_silver_superset_preserves_each_complete_layer_and_final_gold_closure(
    admitted_candidate,
):
    paths, fields, _ = admitted_candidate
    report = validation.validate_target_candidate(paths, fields)
    assert report["silver"]["rows"] == 2
    assert report["gold"]["rows"] == 1
    assert report["fk_closure"] == "PASS"


@pytest.mark.parametrize(
    "organism",
    [
        "Human herpesvirus 1 (strain SC16)",
        "Human cytomegalovirus (strain AD169)",
    ],
)
def test_hash_verification_preserves_persisted_organism_text(organism):
    config = yaml.safe_load((ROOT / "configs/entities/chembl/target.yaml").read_bytes())
    fields = tuple(config["hash_policy"]["hash_policy"]["include_fields"])
    row = {**_old_row("CHEMBL1", fields), "organism": organism}
    row["content_hash"] = _processor(fields, enrich=False).compute_content_hash(row)
    assert validation.compare_target_rows([row], [dict(row)], fields)["rows"] == 1


def test_historical_gold_keeps_the_current_silver_projection(admitted_candidate):
    paths, fields, tables = _as_legacy_physical(admitted_candidate)
    silver = dict(tables[paths["silver"]][0])
    historical_business = {**silver, "target_type": "PROTEIN FAMILY"}
    historical_business["content_hash"] = scoped_target_hash(
        historical_business, fields, CHEMBL_TARGET_PROFILE
    )
    historical = _gold(historical_business)
    for field in ("_index", "_dq_error", "_dq_warn", "description"):
        historical.pop(field, None)
    historical.update(
        _valid_from=datetime(2026, 1, 1, tzinfo=UTC),
        _valid_to=datetime(2026, 11, 16, tzinfo=UTC),
        _is_current=False,
        _version=1,
    )
    current = tables[paths["gold"]][0]
    current_candidate = tables[paths["candidate_gold"]][0]
    current["_version"] = 2
    current_candidate["_version"] = 2
    projection = {
        name: tables[paths["candidate_silver"]][0][name]
        for name in TARGET_CLASSIFICATION_FIELDS
    }
    candidate_historical = {**historical, **projection}
    candidate_historical["content_hash"] = scoped_target_hash(
        candidate_historical,
        (*fields, *TARGET_CLASSIFICATION_FIELDS),
        target_v31_normalization_profile(),
    )
    tables[paths["gold"]] = [historical, current]
    tables[paths["candidate_gold"]] = [candidate_historical, current_candidate]
    report = validation.validate_target_candidate(paths, fields)
    assert report["fk_closure"] == "PASS"
    assert candidate_historical["iuphar_target_id"] == projection["iuphar_target_id"]


def test_gold_targets_unused_by_assay_are_preserved(admitted_candidate):
    paths, fields, tables = admitted_candidate
    tables[paths["gold"]].append(_gold(tables[paths["silver"]][1]))
    tables[paths["candidate_gold"]].append(_gold(tables[paths["candidate_silver"]][1]))
    report = validation.validate_target_candidate(paths, fields)
    assert report["gold"]["rows"] == 2
    assert report["fk_closure"] == "PASS"


def test_canonical_description_wins_over_legacy_alias():
    assert (
        hash_input({"target_description": "canonical", "description": "legacy"})[
            "target_description"
        ]
        == "canonical"
    )


def test_candidate_entity_identity_cannot_change(admitted_candidate):
    paths, fields, tables = admitted_candidate
    tables[paths["candidate_silver"]][0]["entity_id"] = "forged:identity"
    with pytest.raises(ValueError, match="legacy entity_id"):
        validation.validate_target_candidate(paths, fields)


@pytest.mark.parametrize("layer", ["candidate_silver", "candidate_gold"])
def test_well_formed_dummy_v31_hash_is_rejected(admitted_candidate, layer):
    paths, fields, tables = admitted_candidate
    tables[paths[layer]][0]["content_hash"] = "d" * 64
    with pytest.raises(ValueError, match="V31 content hash"):
        validation.validate_target_candidate(paths, fields)


def test_invented_class_with_recomputed_valid_hash_is_rejected(admitted_candidate):
    paths, fields, tables = admitted_candidate
    row = tables[paths["candidate_silver"]][0]
    row["iuphar_class"] = "Enzyme"
    row["content_hash"] = _processor(
        (*fields, *TARGET_CLASSIFICATION_FIELDS), enrich=True
    ).compute_content_hash(row)
    with pytest.raises(ValueError, match="classification differs from admitted source"):
        validation.validate_target_candidate(paths, fields)


def test_gold_projection_must_equal_its_classified_silver_source(admitted_candidate):
    paths, fields, tables = admitted_candidate
    row = tables[paths["candidate_gold"]][0]
    row["effective_class"] = "Enzyme"
    processor = _processor((*fields, *TARGET_CLASSIFICATION_FIELDS), enrich=True)
    hash_input = {**row, "target_description": row["description"]}
    hash_input.pop("description")
    row["content_hash"] = processor.compute_content_hash(
        processor.normalize_business_data(hash_input)
    )
    with pytest.raises(ValueError, match="classification differs from admitted source"):
        validation.validate_target_candidate(paths, fields)


def test_migration_plan_cannot_weaken_frozen_canonical_hash_scope(admitted_candidate):
    paths, fields, _ = admitted_candidate
    with pytest.raises(ValueError, match="frozen canonical V30 policy"):
        validation.validate_target_candidate(paths, fields[:-1])


def test_final_gold_foreign_key_gap_is_rejected(admitted_candidate):
    paths, fields, tables = admitted_candidate
    tables[paths["assay"]].append({"target_id": "CHEMBL3"})
    with pytest.raises(ValueError, match="foreign-key closure"):
        validation.validate_target_candidate(paths, fields)


@pytest.mark.parametrize("existing", ["silver", "gold"])
def test_destructive_enrich_preserves_existing_v31_table(tmp_path: Path, existing: str):
    table = tmp_path / existing
    write_deltalake(
        str(table),
        pa.table(
            {name: ["fixture"] for name in ("target_id", *TARGET_CLASSIFICATION_FIELDS)}
        ),
    )
    original = {
        path.relative_to(table): path.read_bytes()
        for path in table.rglob("*")
        if path.is_file()
    }
    with pytest.raises(ValueError, match="before destructive writes"):
        assert_target_table_compatibility(
            silver_path=tmp_path / "silver",
            gold_path=tmp_path / "gold",
            mode="enrich",
            destructive=True,
        )
    assert original == {
        path.relative_to(table): path.read_bytes()
        for path in table.rglob("*")
        if path.is_file()
    }


def test_destructive_enrich_allows_empty_candidate_destinations(tmp_path: Path):
    assert_target_table_compatibility(
        silver_path=tmp_path / "silver",
        gold_path=tmp_path / "gold",
        mode="enrich",
        destructive=True,
    )


def _as_legacy_physical(admitted_candidate):
    paths, fields, tables = admitted_candidate
    for layer in ("silver", "candidate_silver"):
        for row in tables[paths[layer]]:
            for field in ("_run_id", "_run_type", "_ingestion_ts", "_source_batch_id"):
                row.pop(field, None)
    for layer in ("gold", "candidate_gold"):
        for row in tables[paths[layer]]:
            for field in ("_index", "_dq_error", "_dq_warn", "description"):
                row.pop(field, None)
            row.update(
                {
                    "_valid_from": datetime(2026, 11, 16, tzinfo=UTC),
                    "_valid_to": None,
                    "_is_current": True,
                    "_version": 1,
                }
            )
    return paths, fields, tables


def test_explicit_historical_physical_projection_preserves_rows_without_provenance_fabrication(
    admitted_candidate,
):
    paths, fields, tables = _as_legacy_physical(admitted_candidate)
    report = validation.validate_target_candidate(paths, fields)
    silver = report["silver"]["physical_projection"]
    gold = report["gold"]["physical_projection"]
    assert silver["policy_id"] == "legacy_physical_target_v30_to_v31_v1"
    assert silver["omitted_runtime_columns"] == [
        "_ingestion_ts",
        "_run_id",
        "_run_type",
    ]
    assert gold["logical_nullable_absences"] == ["description"]
    assert gold["storage_envelope_columns"] == [
        "_is_current",
        "_valid_from",
        "_valid_to",
        "_version",
    ]
    assert "description" not in tables[paths["candidate_gold"]][0]
    assert "_run_id" not in tables[paths["candidate_silver"]][0]
    import pandas as pd
    from bioetl.domain.schemas.chembl.target import TargetSchemaV31

    with pytest.raises(SchemaErrors, match="_run_id"):
        TargetSchemaV31.validate(
            pd.DataFrame(tables[paths["candidate_silver"]]), lazy=True
        )


@pytest.mark.parametrize(
    "field", ["_valid_from", "_valid_to", "_is_current", "_version"]
)
@pytest.mark.parametrize("remove", [True, False])
def test_old_scd_metadata_cannot_be_removed_or_changed(
    admitted_candidate, field, remove
):
    paths, fields, tables = _as_legacy_physical(admitted_candidate)
    row = tables[paths["candidate_gold"]][0]
    if remove:
        row.pop(field)
    else:
        row[field] = "changed"
    with pytest.raises(ValueError, match="legacy technical field"):
        validation.validate_target_candidate(paths, fields)


@pytest.mark.parametrize(
    "field,value",
    [
        ("_valid_from", "2026-11-16"),
        ("_valid_from", 123),
        ("_valid_from", "2026-99-16T10:28:06+00:00"),
        ("_valid_to", "tomorrow"),
        ("_is_current", 1),
        ("_version", True),
        ("_version", 0),
    ],
)
def test_existing_scd_envelope_types_are_validated(admitted_candidate, field, value):
    paths, fields, tables = _as_legacy_physical(admitted_candidate)
    for layer in ("gold", "candidate_gold"):
        tables[paths[layer]][0][field] = value
    with pytest.raises(ValueError, match="Gold SCD"):
        validation.validate_target_candidate(paths, fields)


def test_present_runtime_lineage_remains_nonnullable(admitted_candidate):
    paths, fields, tables = admitted_candidate
    for layer in ("silver", "candidate_silver"):
        tables[paths[layer]][0]["_run_id"] = None
    with pytest.raises(SchemaErrors, match="_run_id"):
        validation.validate_target_candidate(paths, fields)


def test_unknown_nullable_business_omission_is_not_adapted(admitted_candidate):
    paths, fields, tables = _as_legacy_physical(admitted_candidate)
    for layer in ("gold", "candidate_gold"):
        row = tables[paths[layer]][0]
        row.pop("target_gene_synonyms")
        include = (
            fields if layer == "gold" else (*fields, *TARGET_CLASSIFICATION_FIELDS)
        )
        row["content_hash"] = validation._scoped_target_hash(
            row,
            include,
            CHEMBL_TARGET_PROFILE
            if layer == "gold"
            else target_v31_normalization_profile(),
        )
    with pytest.raises(SchemaErrors, match="target_gene_synonyms"):
        validation.validate_target_candidate(paths, fields)


@pytest.mark.parametrize("field", ["_invented_provenance", "unexpected_business"])
def test_unexpected_physical_candidate_columns_are_rejected(admitted_candidate, field):
    paths, fields, tables = _as_legacy_physical(admitted_candidate)
    for row in tables[paths["candidate_silver"]]:
        row[field] = "invented"
    with pytest.raises(ValueError, match="old columns plus nine"):
        validation.validate_target_candidate(paths, fields)


def test_existing_lineage_column_cannot_be_deleted(admitted_candidate):
    paths, fields, tables = admitted_candidate
    for row in tables[paths["candidate_silver"]]:
        row.pop("_run_id")
    with pytest.raises(ValueError, match="legacy technical field"):
        validation.validate_target_candidate(paths, fields)


def test_historical_scd_iso8601_text_remains_exactly_preserved(admitted_candidate):
    paths, fields, tables = _as_legacy_physical(admitted_candidate)
    value = "2026-11-16T10:28:06.795495+00:00"
    for layer in ("gold", "candidate_gold"):
        tables[paths[layer]][0]["_valid_from"] = value
    assert validation.validate_target_candidate(paths, fields)["fk_closure"] == "PASS"
    assert tables[paths["candidate_gold"]][0]["_valid_from"] == value


def test_supported_transition_is_only_v30_to_v31():
    from bioetl.infrastructure.storage.target_classification_migration import (
        require_rf009_fk_restoration,
        resolve_target_migration_transition,
    )

    transition = resolve_target_migration_transition("V30", "V31")
    assert transition.source_contract_version == "3.0.0"
    assert transition.destination_contract_version == "3.1.0"
    assert (
        require_rf009_fk_restoration({"CHEMBL1"}, {"CHEMBL1", "CHEMBL2"})["status"]
        == "closed"
    )


@pytest.mark.parametrize(
    ("source", "destination", "message"),
    [
        ("V30", "V32", "3.2.0 is not installed"),
        ("V31", "V32", "3.2.0 is not installed"),
        ("V31", "V30", "unsupported target migration transition"),
        ("V31", "V31", "unsupported target migration transition"),
        ("V30", "V30", "unsupported target migration transition"),
        ("empty", "V31", "unsupported target migration transition"),
        ("V32", "V31", "unsupported target migration transition"),
    ],
)
def test_unsupported_transitions_are_rejected(source, destination, message):
    from bioetl.infrastructure.storage.target_classification_migration import (
        resolve_target_migration_transition,
    )

    with pytest.raises(ValueError, match=message):
        resolve_target_migration_transition(source, destination)


def test_open_assay_fk_requires_rf009_before_promotion():
    from bioetl.infrastructure.storage.target_classification_migration import (
        require_rf009_fk_restoration,
    )

    with pytest.raises(ValueError, match="RF-009"):
        require_rf009_fk_restoration({"CHEMBL1", "CHEMBL9"}, {"CHEMBL1"})


def test_cli_plan_requires_profiles_and_refuses_canonical_promote(
    tmp_path, monkeypatch
):
    import json

    from scripts.ops import target_classification_migration as cli

    plan = tmp_path / "plan.json"
    plan.write_text(
        json.dumps({"paths": {}, "legacy_include_fields": ["target_id"]}),
        encoding="utf-8",
    )
    monkeypatch.setattr(cli, "confined_io_path", lambda path, root: Path(path))
    monkeypatch.setattr(cli, "resolve_configs_root", lambda: tmp_path)
    with pytest.raises(SystemExit):
        cli.main(
            [
                "freeze-inputs",
                "--plan",
                str(plan),
                "--output",
                str(tmp_path / "out.json"),
            ]
        )
    plan.write_text(
        json.dumps(
            {
                "paths": {},
                "legacy_include_fields": ["target_id"],
                "source_profile": "V30",
                "destination_profile": "V32",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        cli.main(["prepare", "--plan", str(plan)])
    plan.write_text(
        json.dumps(
            {
                "paths": {},
                "legacy_include_fields": ["target_id"],
                "source_profile": "V30",
                "destination_profile": "V31",
            }
        ),
        encoding="utf-8",
    )
    with pytest.raises(SystemExit):
        cli.main(["promote", "--plan", str(plan)])


@pytest.mark.parametrize("field,value", [("_version", True), ("_is_current", 1)])
def test_equal_numeric_value_cannot_hide_technical_type_drift(
    admitted_candidate, field, value
):
    paths, fields, tables = _as_legacy_physical(admitted_candidate)
    tables[paths["candidate_gold"]][0][field] = value
    with pytest.raises(ValueError, match="legacy technical field"):
        validation.validate_target_candidate(paths, fields)
