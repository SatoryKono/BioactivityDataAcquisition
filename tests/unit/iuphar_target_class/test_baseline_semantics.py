"""RF-001 baseline: field layers, decision rows, and the pinned manifest."""

from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path

import pytest
import yaml

from bioetl.domain.config.target_classification import TARGET_CLASSIFICATION_FIELDS
from iuphar_target_class.baseline_manifest import (
    BASELINE_REVISION,
    CANDIDATE_MANIFEST_RELATIVE_PATH,
    INCOMPLETE_HISTORY,
    MANIFEST_RELATIVE_PATH,
    build_baseline_manifest,
    historical_blob_problems,
    verify_baseline_manifest,
    write_baseline_manifest,
)
from iuphar_target_class.gtopdb_2026_3_1 import (
    ARCHIVE_SHA256,
    RELEASE,
    SQL_SHA256,
    TARGETS_CSV_SHA256,
)
from iuphar_target_class.baseline_semantics import (
    CANONICAL_OTHER,
    COMMITTED_COMPOSITE_VERSION,
    COMMITTED_ENTITY_CONTRACT,
    COMMITTED_ENTITY_MODE,
    COMMITTED_TABLE_GENERATION,
    DROPPED_PARENTS,
    FALSE_OTHER,
    FIELD_DEFINITIONS,
    LEGACY_OTHER,
    LOCAL_INFERENCE_IN_IUPHAR,
    PROFILE_CHANGE_RULES,
    SNAPSHOT_ANNOTATION_CAPABILITY,
    UNDEFINED_TABLE_DISTINCT,
    UNCERTAINTY_STATUSES,
    BoundaryObservation,
    contract_document,
    covered_statuses,
    decide,
    field_layer,
)
from iuphar_target_class.policy import (
    BASE_MISSING_MARKERS,
    baseline_contract,
    policy_document,
)
from iuphar_target_class.stage0.io import canonical_json_bytes, sha256_bytes

pytestmark = pytest.mark.unit
ROOT = Path(__file__).resolve().parents[3]


def test_v31_fields_keep_distinct_layers() -> None:
    layers = {item.name: item.layer for item in FIELD_DEFINITIONS}
    assert layers["target_type"] == "chembl_object_type"
    assert "target_type" not in TARGET_CLASSIFICATION_FIELDS
    assert len(TARGET_CLASSIFICATION_FIELDS) == 9
    for name in TARGET_CLASSIFICATION_FIELDS:
        assert layers[name] == field_layer(name)
    assert field_layer("iuphar_class") == "dictionary"
    assert field_layer("local_class") == "local_rule"
    assert field_layer("effective_class") == "decision"
    assert field_layer("effective_source") == "decision"
    with pytest.raises(ValueError, match="no RF-001 layer"):
        field_layer("pref_name")


def test_decision_table_covers_uncertainty_and_availability() -> None:
    covered = covered_statuses()
    assert set(UNCERTAINTY_STATUSES) <= covered
    assert {"source_unavailable", "not_found"} <= covered
    assert [rule.rule_id for rule in PROFILE_CHANGE_RULES]
    versions = contract_document()["contract_versions"]
    assert isinstance(versions, dict)
    assert all(versions.values())
    assert baseline_contract() == contract_document()


def test_missing_marker_version_stays_unapproved() -> None:
    parameters = policy_document()["parameters"]
    assert isinstance(parameters, dict)
    assert parameters["missing_markers_version"] is None
    markers = contract_document()["missing_markers"]
    assert isinstance(markers, dict)
    assert markers["base"] == list(BASE_MISSING_MARKERS)
    assert markers["version"] is None
    assert markers["effect"] == "absence"
    assert "not_found" in markers["does_not_mean"]


def test_audit_counterexamples_follow_the_decision_table() -> None:
    mixed = decide(LOCAL_INFERENCE_IN_IUPHAR)
    assert mixed.rule_id == "layer_mix"
    assert mixed.decision_status == "contract_defect"
    assert mixed.iuphar_class is None
    assert mixed.local_class == "Enzyme"
    assert mixed.effective_class is None
    assert mixed.effective_source != "iuphar"

    parents = decide(DROPPED_PARENTS)
    assert parents.rule_id == "dropped_parents"
    assert parents.completeness == "partial"
    assert parents.effective_class is None
    assert parents.dropped_parent_ids == ("20",)
    assert parents.decision_status == "requires_review"

    other = decide(FALSE_OTHER)
    assert other.rule_id == "false_other"
    assert other.effective_class is None
    assert other.iuphar_class is None
    assert other.completeness == "unknown"

    distinct = decide(UNDEFINED_TABLE_DISTINCT)
    assert distinct.rule_id == "undefined_table_distinct"
    assert distinct.completeness == "ambiguous"
    assert distinct.effective_class is None
    assert distinct.decision_status == "requires_review"


def test_source_unavailable_is_not_rewritten_as_not_found() -> None:
    unavailable = decide(
        BoundaryObservation(case_id="gap", source_state="source_unavailable")
    )
    assert unavailable.rule_id == "source_unavailable"
    assert unavailable.completeness == "source_unavailable"
    assert "not_found" not in unavailable.codes

    found = decide(BoundaryObservation(case_id="absent", source_state="not_found"))
    assert found.rule_id == "confirmed_not_found"
    assert found.completeness == "not_found"
    assert "source_unavailable" not in found.codes


@pytest.mark.parametrize(
    ("uncertainty", "rule_id", "completeness"),
    [
        ("unknown", "unknown", "unknown"),
        ("partial", "partial_annotation", "partial"),
        ("ambiguous", "ambiguous_match", "ambiguous"),
        ("conflict", "layer_conflict", "conflict"),
    ],
)
def test_uncertainty_rows_do_not_invent_a_class(
    uncertainty: str, rule_id: str, completeness: str
) -> None:
    decision = decide(BoundaryObservation(case_id=uncertainty, uncertainty=uncertainty))
    assert decision.rule_id == rule_id
    assert decision.completeness == completeness
    assert decision.effective_class is None


def test_legacy_other_is_admissible_only_as_a_legacy_alias() -> None:
    rejected = decide(
        BoundaryObservation(
            case_id="other-in-dictionary",
            assigned_label=LEGACY_OTHER,
            approved_other_mapping=True,
            legacy_field=False,
        )
    )
    assert rejected.rule_id == "false_other"
    assert rejected.iuphar_class is None

    alias = decide(
        BoundaryObservation(
            case_id="legacy-alias",
            assigned_label=LEGACY_OTHER,
            approved_other_mapping=True,
            legacy_field=True,
        )
    )
    assert alias.rule_id == "legacy_other_alias"
    assert alias.iuphar_class == CANONICAL_OTHER
    assert alias.effective_source == "iuphar"

    direct = decide(
        BoundaryObservation(
            case_id="canonical-other",
            assigned_label=CANONICAL_OTHER,
            approved_other_mapping=True,
        )
    )
    assert direct.rule_id == "admissible_other"
    assert direct.effective_class == CANONICAL_OTHER


def test_partial_and_conflict_keep_a_dictionary_fact_apart_from_local() -> None:
    partial = decide(
        BoundaryObservation(
            case_id="partial-family",
            uncertainty="partial",
            dictionary_class="Receptor",
            local_class="Enzyme",
        )
    )
    assert partial.iuphar_class == "Receptor"
    assert partial.local_class == "Enzyme"
    assert partial.effective_source == "iuphar"
    assert partial.decision_status == "requires_review"

    conflict = decide(
        BoundaryObservation(
            case_id="direct-local",
            uncertainty="conflict",
            dictionary_class="Ion Channel",
            local_class="Transporter",
        )
    )
    assert conflict.rule_id == "layer_conflict"
    assert conflict.iuphar_class == "Ion Channel"
    assert conflict.local_class == "Transporter"
    assert conflict.effective_class == "Ion Channel"


def _baseline_file(relative: str) -> str | None:
    commit = subprocess.run(
        ["git", "cat-file", "-e", f"{BASELINE_REVISION}^{{commit}}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    if commit.returncode != 0:
        return None
    blob = subprocess.run(
        ["git", "cat-file", "blob", f"{BASELINE_REVISION}:{relative}"],
        cwd=ROOT,
        capture_output=True,
        check=False,
    )
    assert blob.returncode == 0, relative
    return blob.stdout.decode("utf-8")


def test_committed_configs_match_the_baseline_claim() -> None:
    entity_text = _baseline_file("configs/entities/chembl/target.yaml")
    composite_text = _baseline_file("configs/composites/target.yaml")
    if entity_text is None or composite_text is None:
        pytest.skip(INCOMPLETE_HISTORY)
    entity = yaml.safe_load(entity_text)
    composite = yaml.safe_load(composite_text)
    classification = entity["pipeline"]["target_classification"]
    assert classification["mode"] == COMMITTED_ENTITY_MODE
    assert entity["contracts"]["active_version"] == COMMITTED_ENTITY_CONTRACT
    assert COMMITTED_TABLE_GENERATION == "V30"
    assert composite["composite"]["version"] == COMMITTED_COMPOSITE_VERSION


def test_snapshot_builder_records_family_only_capability(tmp_path: Path) -> None:
    from tests.helpers.iuphar_snapshot import synthetic_snapshot_bundle

    root, _bundle = synthetic_snapshot_bundle(tmp_path)
    document = json.loads((root / "snapshot.json").read_bytes())
    assert document["annotation_capability"] == SNAPSHOT_ANNOTATION_CAPABILITY


def test_supported_local_stays_out_of_the_dictionary_layer() -> None:
    unavailable = decide(
        BoundaryObservation(
            case_id="unavailable-local",
            source_state="source_unavailable",
            local_class="Enzyme",
            local_status="supported",
        )
    )
    assert unavailable.rule_id == "source_unavailable_supported_local"
    assert unavailable.effective_class == "Enzyme"
    assert unavailable.effective_source == "local"
    assert unavailable.iuphar_class is None
    assert unavailable.decision_status == "requires_review"
    assert unavailable.completeness == "source_unavailable"
    assert unavailable.codes == ("source_unavailable",)

    confirmed = decide(
        BoundaryObservation(
            case_id="not-found-local",
            source_state="not_found",
            local_class="Enzyme",
            local_status="supported",
        )
    )
    assert confirmed.rule_id == "confirmed_not_found_supported_local"
    assert confirmed.effective_class == "Enzyme"
    assert confirmed.effective_source == "local"
    assert confirmed.iuphar_class is None
    assert confirmed.decision_status == "resolved"
    assert confirmed.codes == ("confirmed_not_found",)

    conflict = decide(
        BoundaryObservation(
            case_id="not-found-conflict",
            source_state="not_found",
            local_status="conflicting",
        )
    )
    assert conflict.rule_id == "confirmed_not_found_conflict"
    assert conflict.effective_class is None
    assert "source_unavailable" not in conflict.codes


def test_unapproved_local_other_does_not_fill_a_dictionary_gap() -> None:
    cases = (
        ("not_found", "not_found", "confirmed_not_found", LEGACY_OTHER, False),
        ("not_found", "not_found", "confirmed_not_found", CANONICAL_OTHER, False),
        (
            "source_unavailable",
            "source_unavailable",
            "source_unavailable",
            LEGACY_OTHER,
            False,
        ),
        (
            "source_unavailable",
            "source_unavailable",
            "source_unavailable",
            CANONICAL_OTHER,
            True,
        ),
    )
    for source_state, completeness, code, label, approved in cases:
        decision = decide(
            BoundaryObservation(
                case_id=f"{source_state}-{label}-{approved}",
                source_state=source_state,
                local_class=label,
                local_status="supported",
                approved_other_mapping=approved,
                legacy_field=False,
            )
        )
        assert decision.effective_class is None
        assert decision.effective_source is None
        assert decision.iuphar_class is None
        assert decision.local_class == label
        assert decision.completeness == completeness
        assert decision.decision_status == "unresolved"
        if approved:
            assert decision.rule_id in {"confirmed_not_found", "source_unavailable"}
            assert "false_other" not in decision.codes
        else:
            assert decision.rule_id == "false_other"
            assert decision.codes == ("false_other", code)


def test_dropped_parents_outrank_an_admissible_other() -> None:
    decision = decide(
        BoundaryObservation(
            case_id="other-and-parents",
            assigned_label=CANONICAL_OTHER,
            approved_other_mapping=True,
            parent_ids=("10", "20"),
            retained_parent_ids=("10",),
        )
    )
    assert decision.rule_id == "dropped_parents"
    assert decision.decision_status == "requires_review"
    assert decision.completeness == "partial"
    assert decision.effective_class is None
    assert decision.iuphar_class is None


def test_published_manifest_matches_the_current_contract() -> None:
    document = json.loads((ROOT / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    assert document["semantics"] == contract_document()
    release = document["iuphar_release"]
    assert release["release"] == RELEASE
    assert release["archive_sha256"] == ARCHIVE_SHA256
    assert release["sql_sha256"] == SQL_SHA256
    assert release["targets_csv_sha256"] == TARGETS_CSV_SHA256


def test_swapped_material_bytes_fail_verification() -> None:
    document = json.loads((ROOT / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    by_id = {row["material_id"]: row for row in document["materials"]}
    rules = by_id["rules_record"]
    control = by_id["control_target"]
    for key in ("path", "baseline_sha256", "worktree_sha256", "delta"):
        rules[key] = control[key]
    problems = verify_baseline_manifest(ROOT, document)
    assert "rules_record path mismatch" in problems


def test_manifest_hashes_and_required_roles_hold() -> None:
    path = ROOT / MANIFEST_RELATIVE_PATH
    document = json.loads(path.read_text(encoding="utf-8"))
    problems = verify_baseline_manifest(ROOT, document)
    if problems == (INCOMPLETE_HISTORY,):
        pytest.skip(INCOMPLETE_HISTORY)
    assert problems == ()
    materials = document["materials"]
    by_id = {row["material_id"]: row for row in materials}
    assert by_id["m_source"]["availability"] == "source_unavailable"
    assert by_id["m_source"]["semantics_bound"] is False
    assert by_id["m_source"]["version_id"] is None
    assert by_id["m_source"]["confirmed_absence"] is False
    assert by_id["result_cache"]["role"] == "result_cache"
    assert by_id["result_cache"]["fresh_recalculation"] is False
    assert by_id["result_cache"]["availability"] == "source_unavailable"
    assert by_id["iuphar_snapshot_bytes"]["availability"] == "source_unavailable"
    assert document["m_semantics_bound"] is False
    assert document["fresh_recalculation"] is False
    changed = {
        row["material_id"]
        for row in materials
        if row["delta"] == "content_changed_by_rf001"
    }
    assert changed == {"rules_source"}
    introduced = {
        row["material_id"] for row in materials if row["delta"] == "absent_on_baseline"
    }
    assert introduced == {"manifest_source", "semantics_source"}
    encoded = canonical_json_bytes(document)
    assert path.read_bytes() == encoded


def _git(repo: Path, *args: str) -> str:
    completed = subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
        env={
            **os.environ,
            "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull,
        },
    )
    return completed.stdout.strip()


def _init_repo(repo: Path) -> None:
    repo.mkdir()
    _git(repo, "init")
    _git(repo, "config", "user.email", "rf001@example.com")
    _git(repo, "config", "user.name", "RF-001")
    _git(repo, "config", "commit.gpgsign", "false")


def test_missing_revision_is_one_incomplete_history_problem(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    rows = [
        {
            "availability": "present",
            "baseline_sha256": "b" * 64,
            "material_id": "classifier_source",
            "path": "missing.py",
        }
    ]
    problems = historical_blob_problems(repo, "a" * 40, rows)
    assert problems == (INCOMPLETE_HISTORY,)


def test_absent_path_on_an_available_revision_stays_absent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    (repo / "kept.py").write_text("kept\n", encoding="utf-8")
    _git(repo, "add", "kept.py")
    _git(repo, "commit", "-m", "baseline")
    revision = _git(repo, "rev-parse", "HEAD")
    absent = historical_blob_problems(
        repo,
        revision,
        [
            {
                "availability": "present",
                "baseline_sha256": None,
                "material_id": "semantics_source",
                "path": "added-later.py",
            }
        ],
    )
    assert absent == ()
    mismatched = historical_blob_problems(
        repo,
        revision,
        [
            {
                "availability": "present",
                "baseline_sha256": "c" * 64,
                "material_id": "semantics_source",
                "path": "added-later.py",
            }
        ],
    )
    assert mismatched == ("semantics_source baseline hash mismatch",)


def test_later_file_bytes_do_not_fail_historical_verification(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    target = repo / "classifier.py"
    target.write_text("original\n", encoding="utf-8")
    _git(repo, "add", "classifier.py")
    _git(repo, "commit", "-m", "baseline")
    revision = _git(repo, "rev-parse", "HEAD")
    original = sha256_bytes(b"original\n")
    target.write_text("later\n", encoding="utf-8")
    problems = historical_blob_problems(
        repo,
        revision,
        [
            {
                "availability": "present",
                "baseline_sha256": original,
                "material_id": "classifier_source",
                "path": "classifier.py",
                "worktree_sha256": sha256_bytes(b"later\n"),
            }
        ],
    )
    assert problems == ()


def test_tree_path_is_unreadable_rather_than_absent(tmp_path: Path) -> None:
    repo = tmp_path / "repo"
    _init_repo(repo)
    folder = repo / "nested"
    folder.mkdir()
    (folder / "kept.py").write_text("kept\n", encoding="utf-8")
    _git(repo, "add", "nested/kept.py")
    _git(repo, "commit", "-m", "baseline")
    revision = _git(repo, "rev-parse", "HEAD")
    problems = historical_blob_problems(
        repo,
        revision,
        [
            {
                "availability": "present",
                "baseline_sha256": None,
                "material_id": "classifier_source",
                "path": "nested",
            }
        ],
    )
    assert problems == ("classifier_source baseline blob is unreadable",)


def test_local_disagreement_is_not_a_resolved_dictionary_fact() -> None:
    conflicting = decide(
        BoundaryObservation(
            case_id="conflict",
            dictionary_class="Receptor",
            local_status="conflicting",
        )
    )
    assert conflicting.rule_id == "layer_conflict"
    assert conflicting.decision_status == "requires_review"
    assert conflicting.completeness == "conflict"
    assert conflicting.iuphar_class == "Receptor"
    assert conflicting.effective_class == "Receptor"
    assert conflicting.effective_source == "iuphar"

    different = decide(
        BoundaryObservation(
            case_id="different-local",
            dictionary_class="Receptor",
            local_class="Enzyme",
            local_status="supported",
        )
    )
    assert different.rule_id == "layer_conflict"
    assert different.decision_status == "requires_review"
    assert different.local_class == "Enzyme"
    assert different.iuphar_class == "Receptor"
    assert different.effective_class == "Receptor"

    agreed = decide(
        BoundaryObservation(
            case_id="same-local",
            dictionary_class="Receptor",
            local_class="Receptor",
            local_status="supported",
        )
    )
    assert agreed.rule_id == "dictionary_resolved"
    assert agreed.decision_status == "resolved"


def test_approved_other_survives_an_incomplete_annotation() -> None:
    partial = decide(
        BoundaryObservation(
            case_id="partial-other",
            dictionary_class=CANONICAL_OTHER,
            approved_other_mapping=True,
            uncertainty="partial",
        )
    )
    assert partial.rule_id == "partial_annotation"
    assert partial.decision_status == "requires_review"
    assert partial.completeness == "partial"
    assert partial.iuphar_class == CANONICAL_OTHER
    assert partial.effective_class == CANONICAL_OTHER
    assert partial.effective_source == "iuphar"

    conflict = decide(
        BoundaryObservation(
            case_id="conflict-other",
            dictionary_class=CANONICAL_OTHER,
            approved_other_mapping=True,
            uncertainty="conflict",
        )
    )
    assert conflict.rule_id == "layer_conflict"
    assert conflict.decision_status == "requires_review"
    assert conflict.completeness == "conflict"
    assert conflict.iuphar_class == CANONICAL_OTHER
    assert conflict.effective_class == CANONICAL_OTHER
    assert conflict.effective_source == "iuphar"

    legacy = decide(
        BoundaryObservation(
            case_id="partial-legacy-other",
            dictionary_class=LEGACY_OTHER,
            approved_other_mapping=True,
            legacy_field=True,
            uncertainty="partial",
        )
    )
    assert legacy.rule_id == "partial_annotation"
    assert legacy.iuphar_class == CANONICAL_OTHER
    assert legacy.effective_class == CANONICAL_OTHER

    rejected = decide(
        BoundaryObservation(
            case_id="partial-unapproved-other",
            dictionary_class=CANONICAL_OTHER,
            uncertainty="partial",
        )
    )
    assert rejected.rule_id == "false_other"
    assert rejected.iuphar_class is None
    assert rejected.effective_class is None


def test_blank_classes_do_not_become_dictionary_or_local_facts() -> None:
    with pytest.raises(ValueError, match="supported local"):
        BoundaryObservation(
            case_id="blank-local",
            local_class="  ",
            local_status="supported",
        )
    empty = decide(BoundaryObservation(case_id="empty-dictionary", dictionary_class=""))
    assert empty.rule_id == "unknown"
    assert empty.iuphar_class is None
    unmarked = decide(
        BoundaryObservation(
            case_id="dictionary-other",
            dictionary_class=CANONICAL_OTHER,
        )
    )
    assert unmarked.rule_id == "false_other"
    assert unmarked.effective_class is None
    ambiguous = decide(
        BoundaryObservation(
            case_id="legacy-ambiguous",
            assigned_label=LEGACY_OTHER,
            approved_other_mapping=True,
            legacy_field=True,
            uncertainty="ambiguous",
        )
    )
    assert ambiguous.rule_id == "ambiguous_match"
    assert ambiguous.effective_class is None
    enzyme = decide(
        BoundaryObservation(
            case_id="enzyme",
            source_state="not_found",
            local_class="Enzyme",
            local_status="supported",
        )
    )
    assert enzyme.effective_class == "Enzyme"
    assert enzyme.iuphar_class is None


def test_manifest_rejects_non_hex_hashes_and_non_string_roles() -> None:
    document = json.loads((ROOT / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    by_id = {row["material_id"]: row for row in document["materials"]}
    by_id["manifest_source"]["worktree_sha256"] = "z" * 64
    letters = verify_baseline_manifest(ROOT, document)
    assert "manifest_source hash shape mismatch" in letters
    by_id["manifest_source"]["worktree_sha256"] = "1" * 64
    digits = verify_baseline_manifest(ROOT, document)
    assert "manifest_source hash shape mismatch" not in digits
    by_id["control_target"]["role"] = ["control_input"]
    roles = verify_baseline_manifest(ROOT, document)
    assert "control_target role is not a string" in roles


def test_release_header_matches_the_pinned_source() -> None:
    document = json.loads((ROOT / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    document["iuphar_release"]["archive_sha256"] = "ab" * 32
    problems = verify_baseline_manifest(ROOT, document)
    if INCOMPLETE_HISTORY in problems:
        pytest.skip(INCOMPLETE_HISTORY)
    assert "IUPHAR archive_sha256 does not match the baseline revision" in problems


def test_embedded_semantics_must_carry_the_decision_contract() -> None:
    document = json.loads((ROOT / MANIFEST_RELATIVE_PATH).read_text(encoding="utf-8"))
    embedded = {
        "artifact": "iuphar_rf001_baseline_semantics",
        "baseline_id": document["semantics"]["baseline_id"],
        "configuration": document["semantics"]["configuration"],
        "snapshot_annotation_capability": document["semantics"][
            "snapshot_annotation_capability"
        ],
    }
    document["semantics"] = embedded
    document["semantics_sha256"] = sha256_bytes(canonical_json_bytes(embedded))
    problems = verify_baseline_manifest(ROOT, document)
    assert "semantics decision table is missing" in problems
    assert "semantics field dictionary is missing" in problems
    assert "semantics hash mismatch" not in problems


def test_writer_does_not_replace_the_published_manifest() -> None:
    published = ROOT / MANIFEST_RELATIVE_PATH
    before = published.read_bytes()
    candidate = ROOT / CANDIDATE_MANIFEST_RELATIVE_PATH
    try:
        written = write_baseline_manifest(ROOT)
    except RuntimeError as exc:
        if str(exc) == INCOMPLETE_HISTORY:
            pytest.skip(INCOMPLETE_HISTORY)
        raise
    try:
        assert written == candidate
        assert published.read_bytes() == before
        assert candidate.is_file()
    finally:
        candidate.unlink(missing_ok=True)


def test_rebuild_refuses_when_the_revision_object_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "iuphar_target_class.baseline_manifest.BASELINE_REVISION",
        "a" * 40,
    )
    with pytest.raises(RuntimeError, match=INCOMPLETE_HISTORY):
        build_baseline_manifest(ROOT)
