"""Optional child absence needs sealed evidence of an empty eligible seed set."""

from __future__ import annotations

import json

import pyarrow as pa
import pytest
import yaml

from bioetl.infrastructure.storage.composite_replay_bundle import (
    implementation_fingerprint,
    publish_bytes,
    publish_json,
)
from scripts.ops.observability.green_acceptance import Case, composite_report_coverage

pytestmark = pytest.mark.unit


@pytest.mark.parametrize(
    "values,condition,empty",
    [
        ({"doi": ""}, "doi IS NOT NULL", True),
        ({"doi": "10.1000/example"}, "doi IS NOT NULL", False),
        (
            {"inchi_key": "BSYNRYMUTXBXSQ-UHFFFAOYSA-N", "canonical_smiles": None},
            "inchi_key IS NOT NULL",
            False,
        ),
        ({"inchi_key": None, "canonical_smiles": "CC"}, "inchi_key IS NOT NULL", True),
        ({"inchi_key": None, "canonical_smiles": "CC"}, None, False),
        ({"cell_id": None, "tissue_id": "TISSUE1"}, "cell_id IS NULL", False),
    ],
)
def test_optional_eligibility_matches_normalized_runtime_filter(
    values, condition, empty
):
    from scripts.ops.observability.green_acceptance import _has_no_eligible_keys

    table = pa.table(
        {key: pa.array([value], type=pa.string()) for key, value in values.items()}
    )
    keys = list(values)
    enricher = {
        "pipeline": "optional_child",
        "join_keys": keys,
        "filter_condition": condition,
    }
    assert _has_no_eligible_keys(table, keys, enricher) is empty


@pytest.mark.parametrize(
    "defect",
    [
        None,
        "default_optional",
        "eligible",
        "required",
        "unknown_keys",
        "failed",
        "wrong_run",
        "missing",
        "tampered",
        "missing_arrow",
        "path_escape",
    ],
)
def test_absent_optional_child_requires_verified_empty_input(tmp_path, defect):
    config = {
        "seed": {"pipeline": "seed", "output_keys": ["cell_id"]},
        "enrichers": [
            {
                "pipeline": "optional_child",
                "required": defect == "required",
                "join_keys": ["unknown" if defect == "unknown_keys" else "cell_id"],
            }
        ],
    }
    if defect == "default_optional":
        del config["enrichers"][0]["required"]
    config_root = tmp_path / "configs"
    (config_root / "composites").mkdir(parents=True)
    (config_root / "composites/assay.yaml").write_text(
        yaml.safe_dump({"composite": config})
    )
    paths = [
        tmp_path / "reports/pipeline" / name / "run/pipeline-run-report.json"
        for name in ("composite_assay", "seed")
    ]
    for path in paths:
        path.parent.mkdir(parents=True)
        path.write_text("{}")
    root = paths[0].parent / "replay"
    table = pa.table(
        {
            "cell_id": pa.array(
                ["CELL1" if defect == "eligible" else None], type=pa.string()
            )
        }
    )
    sink = pa.BufferOutputStream()
    with pa.ipc.new_file(sink, table.schema) as writer:
        writer.write_table(table)
    objects = {
        "inputs/seed.arrow": publish_bytes(
            root, "inputs/seed.arrow", sink.getvalue().to_pybytes()
        )
    }
    objects["inputs/inputs.json"] = publish_json(
        root,
        "inputs/inputs.json",
        {
            "version": "composite-inputs-v1",
            "required_tables": ["silver/seed"],
            "inputs": [
                {
                    "table": "silver/seed",
                    "file": "seed.arrow",
                    "sha256": objects["inputs/seed.arrow"],
                }
            ],
        },
    )
    for name in (
        "config.json",
        "uv.lock",
        "pipeline-settings.json",
        "expected/silver.arrow",
        "expected/gold.arrow",
        "field-groups.json",
    ):
        objects[name] = publish_bytes(root, name, b"{}")
    digest = publish_json(
        root,
        "parent.json",
        {
            "version": "composite-parent-replay-v2",
            "pipeline": "composite_assay",
            "run_id": "other" if defect == "wrong_run" else "run",
            "implementation": implementation_fingerprint(),
            "objects": objects,
            "input_snapshot_fingerprint": objects["inputs/inputs.json"],
            "request": {
                "seed_pipeline": "seed",
                "seed_table": "silver/seed",
                "outcomes": {
                    "optional_child": "failed" if defect == "failed" else "skipped"
                },
            },
        },
    )
    parent = {
        "io": {
            "child_runs": [
                {"pipeline_name": "seed", "run_id": "run", "status": "success"}
            ]
        },
        "artifacts": [
            {
                "kind": "composite_exact_replay",
                "ref": "../parent.json"
                if defect == "path_escape"
                else "replay/parent.json",
                "sha256": digest,
            }
        ],
    }
    if defect == "missing":
        parent["artifacts"] = []
    elif defect == "tampered":
        (root / "inputs/seed.arrow").write_bytes(b"changed")
    elif defect == "missing_arrow":
        (root / "inputs/seed.arrow").unlink()
    paths[0].write_text(json.dumps(parent))
    failures = composite_report_coverage(
        Case("composite", "composite_assay"), config_root, paths
    )
    if defect in {None, "default_optional"}:
        assert failures == []
    else:
        assert "composite_report_coverage_mismatch" in failures
        if defect in {
            "wrong_run",
            "missing",
            "tampered",
            "missing_arrow",
            "path_escape",
        }:
            assert any(
                value.startswith("composite_optional_skip_unverified:")
                for value in failures
            )
