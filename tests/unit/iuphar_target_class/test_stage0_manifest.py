"""TC-01 stage-0 manifest: unestablished fields stay restricted."""

from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pandas as pd
import pandera.pandas as pa
import pytest

from iuphar_target_class.stage0.build import build_artifacts, publish_stage0
from iuphar_target_class.stage0.constants import (
    PROVENANCE_ESTABLISHED,
    PROVENANCE_UNESTABLISHED,
    USAGE_CANDIDATE_ONLY,
    USAGE_LEGACY,
)
from iuphar_target_class.stage0.io import atomic_write_bytes, sha256_bytes
from iuphar_target_class.stage0.survey import survey_from_object

pytestmark = pytest.mark.unit

REPO = Path(__file__).resolve().parents[3]
SURVEY_PATH = REPO / "data" / "iuphar_target_class" / "stage0" / "survey.json"
OUTPUT_DIR = SURVEY_PATH.parent
ARTIFACTS = (
    "content_checks.csv",
    "m_code_versions.csv",
    "manifest.json",
    "provenance_map.csv",
    "stage_report.json",
)


def _base_survey(**overrides: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "candidate_files": [],
        "expected_materials": [],
        "gold_standard_reviewer": None,
        "gold_standard_reviewer_source": None,
        "issued_on": "2026-11-10",
        "local_observations": [],
        "m_code_versions": [],
        "module_executor": None,
        "module_executor_source": None,
        "plan_revision": "8",
        "plan_version": "1",
        "provenance_claims": [
            {
                "confirmation_owner": None,
                "field_id": field_id,
                "rule_or_process": None,
                "source_ref": None,
                "source_sha256": None,
            }
            for field_id in ("L1", "L2", "g2p_availability", "target_all")
        ],
        "recorded_at_utc": "2026-11-11T18:45:00Z",
        "result_owner_name": "Федор Новиков",
        "result_owner_source": "план v1 r8 §1.1",
    }
    payload.update(overrides)
    return payload


def _claim(field_id: str, **overrides: object) -> dict[str, object]:
    claim: dict[str, object] = {
        "confirmation_owner": None,
        "field_id": field_id,
        "rule_or_process": None,
        "source_ref": None,
        "source_sha256": None,
    }
    claim.update(overrides)
    return claim


def _publish(repo: Path, survey: dict[str, object], output: Path) -> dict[str, bytes]:
    survey_path = repo / "survey.json"
    encoded = (
        json.dumps(survey, ensure_ascii=False, indent=2, sort_keys=True) + "\n"
    ).encode(
        "utf-8",
    )
    survey_path.write_bytes(encoded)
    loaded = survey_from_object(json.loads(encoded.decode("utf-8")))
    return build_artifacts(
        repo_root=repo,
        survey=loaded,
        survey_sha256=sha256_bytes(encoded),
        output_dir=output,
    )


def test_committed_bundle_matches_rebuild() -> None:
    survey_bytes = SURVEY_PATH.read_bytes()
    survey = survey_from_object(json.loads(survey_bytes.decode("utf-8")))
    rebuilt = build_artifacts(
        repo_root=REPO,
        survey=survey,
        survey_sha256=sha256_bytes(survey_bytes),
        output_dir=OUTPUT_DIR,
    )
    for name in ARTIFACTS:
        assert (OUTPUT_DIR / name).read_bytes() == rebuilt[name]


def test_committed_manifest_pins_hashes_and_blocks_ground_truth() -> None:
    manifest = json.loads((OUTPUT_DIR / "manifest.json").read_text(encoding="utf-8"))
    report = json.loads((OUTPUT_DIR / "stage_report.json").read_text(encoding="utf-8"))
    provenance = (OUTPUT_DIR / "provenance_map.csv").read_text(encoding="utf-8")
    assert manifest["biological_accuracy_accepted"] is False
    assert manifest["development_mode"] == "synthetic_fixtures_only"
    assert manifest["copies"] == []
    assert manifest["m_code_version_status"] == PROVENANCE_UNESTABLISHED
    assert manifest["missing_parameters"] == []
    assert manifest["roles"]["result_owner"]["name"] == "Федор Новиков"
    assert manifest["roles"]["result_owner"]["status"] == "назначен"
    assert manifest["roles"]["module_executor"]["name"] == "Cursor"
    assert manifest["roles"]["module_executor"]["status"] == "назначен"
    assert manifest["roles"]["gold_standard_reviewer"]["name"] == "Cursor"
    assert manifest["roles"]["gold_standard_reviewer"]["status"] == "назначен"
    for name, digest in manifest["artifact_sha256"].items():
        payload = (OUTPUT_DIR / name).read_bytes()
        assert hashlib.sha256(payload).hexdigest() == digest
    assert report["statement"].startswith("Без проверенных данных")
    assert report["stage_status"] == "recorded_without_biological_acceptance"
    assert all(item["status"] != "PASS" for item in report["criteria"])
    assert all(not line.endswith(",true") for line in provenance.splitlines()[1:])
    content = (OUTPUT_DIR / "content_checks.csv").read_text(encoding="utf-8")
    assert "candidate:data/input/target.csv" in content
    assert "selected_copy" not in content
    assert (OUTPUT_DIR / "m_code_versions.csv").read_text(encoding="utf-8") == (
        "version_id,source_ref,source_sha256\n"
    )


def test_unestablished_limits_are_legacy_and_candidate_only() -> None:
    provenance = (
        (OUTPUT_DIR / "provenance_map.csv").read_text(encoding="utf-8").splitlines()
    )
    rows = {line.split(",")[0]: line for line in provenance[1:]}
    assert rows["target_all"].split(",")[1] == PROVENANCE_UNESTABLISHED
    assert rows["target_all"].split(",")[6] == USAGE_LEGACY
    assert rows["L1"].split(",")[6] == USAGE_CANDIDATE_ONLY
    assert rows["L2"].split(",")[6] == USAGE_CANDIDATE_ONLY
    assert rows["g2p_availability"].split(",")[1] == PROVENANCE_UNESTABLISHED
    assert rows["g2p_availability"].split(",")[6] == ""


def test_placeholder_role_is_rejected() -> None:
    payload = _base_survey(module_executor="[...]")
    with pytest.raises(ValueError, match="refusing to invent"):
        survey_from_object(payload)


def test_partial_claim_is_not_ground_truth(tmp_path: Path) -> None:
    payload = _base_survey()
    claims = payload["provenance_claims"]
    assert isinstance(claims, list)
    claims[3] = _claim("target_all", source_ref="data/input/target.csv")
    artifacts = _publish(tmp_path, payload, tmp_path / "out")
    text = artifacts["provenance_map.csv"].decode("utf-8")
    target_row = next(
        line for line in text.splitlines() if line.startswith("target_all,")
    )
    assert PROVENANCE_UNESTABLISHED in target_row
    assert target_row.endswith(",legacy,false")
    assert b"true" not in artifacts["provenance_map.csv"]


def test_established_claim_requires_copy_and_all_three_elements(tmp_path: Path) -> None:
    source = tmp_path / "tables" / "target_all.csv"
    source.parent.mkdir(parents=True)
    source.write_text("target_all\nEnzyme\n", encoding="utf-8", newline="\n")
    digest = hashlib.sha256(source.read_bytes()).hexdigest()
    before = source.read_bytes()
    payload = _base_survey(
        candidate_files=[
            {"relative_path": "tables/target_all.csv", "select_as_source": True}
        ],
    )
    claims = payload["provenance_claims"]
    assert isinstance(claims, list)
    claims[3] = _claim(
        "target_all",
        source_ref="tables/target_all.csv",
        source_sha256=digest,
        rule_or_process="копия выгрузки, правило зафиксировано в сопроводительной записи",
        confirmation_owner="проверяющий эталонов",
    )
    output = tmp_path / "out"
    artifacts = _publish(tmp_path, payload, output)
    assert source.read_bytes() == before
    copy_path = output / "copies" / f"{digest}.bin"
    assert copy_path.read_bytes() == before
    text = artifacts["provenance_map.csv"].decode("utf-8")
    target_row = next(
        line for line in text.splitlines() if line.startswith("target_all,")
    )
    assert PROVENANCE_ESTABLISHED in target_row
    assert target_row.endswith(",,true")
    report = json.loads(artifacts["stage_report.json"].decode("utf-8"))
    assert report["biological_accuracy_accepted"] is False
    assert report["stage_status"] == "incomplete_missing_parameters"


def test_hash_mismatch_stays_unestablished(tmp_path: Path) -> None:
    source = tmp_path / "tables" / "target_all.csv"
    source.parent.mkdir(parents=True)
    source.write_text("target_all\nEnzyme\n", encoding="utf-8", newline="\n")
    payload = _base_survey(
        candidate_files=[
            {"relative_path": "tables/target_all.csv", "select_as_source": True}
        ],
    )
    claims = payload["provenance_claims"]
    assert isinstance(claims, list)
    claims[3] = _claim(
        "target_all",
        source_ref="tables/target_all.csv",
        source_sha256="0" * 64,
        rule_or_process="правило",
        confirmation_owner="проверяющий",
    )
    artifacts = _publish(tmp_path, payload, tmp_path / "out")
    text = artifacts["provenance_map.csv"].decode("utf-8")
    target_row = next(
        line for line in text.splitlines() if line.startswith("target_all,")
    )
    assert PROVENANCE_UNESTABLISHED in target_row
    assert target_row.endswith(",legacy,false")


def test_republish_is_byte_identical(tmp_path: Path) -> None:
    payload = _base_survey()
    first = _publish(tmp_path, payload, tmp_path / "a")
    second = _publish(tmp_path, payload, tmp_path / "b")
    assert first == second


def test_atomic_write_replaces_and_removes_temp(tmp_path: Path) -> None:
    target = tmp_path / "manifest.json"
    atomic_write_bytes(target, b"one\n", root=tmp_path)
    atomic_write_bytes(target, b"two\n", root=tmp_path)
    assert target.read_bytes() == b"two\n"
    assert not (tmp_path / ".manifest.json.tmp").exists()
    assert not list(tmp_path.glob(".manifest.json.*.tmp"))


def test_atomic_write_preserves_existing_temp_sibling(tmp_path: Path) -> None:
    target = tmp_path / "manifest.json"
    sibling = tmp_path / ".manifest.json.tmp"
    sibling.write_bytes(b"original source bytes\n")
    atomic_write_bytes(target, b"published\n", root=tmp_path)
    assert sibling.read_bytes() == b"original source bytes\n"
    assert target.read_bytes() == b"published\n"
    assert set(tmp_path.iterdir()) == {target, sibling}


def test_atomic_write_cleans_own_temp_on_replace_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    target = tmp_path / "manifest.json"
    target.write_bytes(b"previous publication\n")

    def fail_replace(_source: Path, _destination: Path) -> None:
        raise OSError("replacement unavailable")

    monkeypatch.setattr(Path, "replace", fail_replace)
    with pytest.raises(OSError, match="replacement unavailable"):
        atomic_write_bytes(target, b"new publication\n", root=tmp_path)
    assert target.read_bytes() == b"previous publication\n"
    assert set(tmp_path.iterdir()) == {target}


def test_schema_rejects_unestablished_ground_truth(tmp_path: Path) -> None:
    from iuphar_target_class.stage0.schema import ProvenanceMapSchema

    artifacts = _publish(tmp_path, _base_survey(), tmp_path / "out")
    frame = pd.read_csv(
        io.BytesIO(artifacts["provenance_map.csv"]), keep_default_na=False
    )
    frame["accepted_as_ground_truth"] = frame["accepted_as_ground_truth"].map(
        {"true": True, "false": False},
    )
    frame.loc[frame["field_id"].eq("target_all"), "accepted_as_ground_truth"] = True
    for column in (
        "source_ref",
        "source_sha256",
        "rule_or_process",
        "confirmation_owner",
    ):
        frame[column] = frame[column].replace({"": pd.NA})
    with pytest.raises(pa.errors.SchemaError):
        ProvenanceMapSchema.validate(frame)


def test_publish_stage0_writes_the_committed_names(tmp_path: Path) -> None:
    survey_path = tmp_path / "survey.json"
    survey_path.write_text(
        json.dumps(_base_survey(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    output = tmp_path / "stage0"
    publish_stage0(tmp_path, survey_path, output)
    for name in ARTIFACTS:
        assert (output / name).is_file()


def test_utf8_bom_does_not_hide_watched_header(tmp_path: Path) -> None:
    source = tmp_path / "tables" / "target_all.csv"
    source.parent.mkdir(parents=True)
    source.write_bytes("target_all\nEnzyme\n".encode("utf-8-sig"))
    raw = source.read_bytes()
    assert raw.startswith(b"\xef\xbb\xbf")
    payload = _base_survey(
        candidate_files=[
            {"relative_path": "tables/target_all.csv", "select_as_source": False},
        ],
    )
    artifacts = _publish(tmp_path, payload, tmp_path / "out")
    text = artifacts["content_checks.csv"].decode("utf-8")
    row = next(line for line in text.splitlines() if "tables/target_all.csv" in line)
    assert ",target_all," in row
    assert hashlib.sha256(raw).hexdigest() in row


def test_publish_rejects_output_outside_repo(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    repo.mkdir()
    survey_path = repo / "survey.json"
    survey_path.write_text(
        json.dumps(_base_survey(), ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(ValueError, match="escapes repo"):
        publish_stage0(repo, survey_path, tmp_path / "outside")


def test_publish_rejects_output_that_replaces_a_source(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    tables = repo / "tables"
    tables.mkdir(parents=True)
    source = tables / "content_checks.csv"
    original = b"target_all\nEnzyme\n"
    source.write_bytes(original)
    survey_path = repo / "survey.json"
    survey_path.write_text(
        json.dumps(
            _base_survey(
                candidate_files=[
                    {
                        "relative_path": "tables/content_checks.csv",
                        "select_as_source": True,
                    },
                ],
            ),
            ensure_ascii=False,
            indent=2,
            sort_keys=True,
        )
        + "\n",
        encoding="utf-8",
        newline="\n",
    )
    with pytest.raises(ValueError, match="replaces source"):
        publish_stage0(repo, survey_path, tables)
    assert source.read_bytes() == original
    assert not (tables / "manifest.json").exists()
