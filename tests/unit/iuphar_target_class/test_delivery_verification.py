"""The three delivery reports stay separate and keep their own statuses."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from iuphar_target_class.delivery_verification import (
    CLASSIFICATION_VERIFICATION,
    M_PARITY_REPORT,
    PROOF_VERIFICATION,
    publish_acceptance_reports,
)

pytestmark = pytest.mark.unit

_PROFILE = "a" * 64
_SNAPSHOT = "b" * 64
_LABELS = "c" * 64


def _receipt(**overrides: object) -> dict[str, object]:
    receipt: dict[str, object] = {
        "run_id": "run-1",
        "status": "BLOCKED_INPUT",
        "snapshot_manifest_sha256": _SNAPSHOT,
        "expected_labels_sha256": _LABELS,
        "normalization_version": "bioetl-iuphar-input-v1",
        "rules_version": "plan-v1-r8",
        "classification_schema_version": "3.1.0",
        "biological_accuracy_accepted": False,
        "checks": {
            "stage0_admission": "NOT_RUN",
            "reference_cases": "NOT_RUN",
            "evidence_integrity": "NOT_RUN",
            "semantic_determinism": "NOT_RUN",
            "pipeline_integration": "NOT_RUN",
        },
    }
    receipt.update(overrides)
    return receipt


def _publish(tmp_path: Path, receipt: dict[str, object]) -> Path:
    output = tmp_path / "acceptance"
    output.mkdir()
    publish_acceptance_reports(
        output,
        root=output,
        receipt=receipt,
        profile_sha256=_PROFILE,
        source_name="profile.json",
        pipeline_proof=None,
        pipeline_report=None,
    )
    return output


def _load(output: Path, name: str) -> dict[str, object]:
    return json.loads((output / name).read_text(encoding="utf-8"))


def test_blocked_acceptance_keeps_not_run_and_unmeasured_parity(tmp_path: Path) -> None:
    output = _publish(tmp_path, _receipt())
    classification = _load(output, CLASSIFICATION_VERIFICATION)
    parity = _load(output, M_PARITY_REPORT)
    proof = _load(output, PROOF_VERIFICATION)
    assert set(classification["checks"].values()) == {"NOT_RUN"}
    assert "pipeline_integration" not in classification["checks"]
    assert parity["measured"] is False
    assert parity["metrics"] is None
    assert parity["m_rows_supplied"] == 0
    assert "checks" not in parity
    assert proof["checks"] == {"pipeline_integration": "NOT_RUN"}
    assert proof["ci"] == {"head_sha": None, "status": "NOT_RUN"}
    assert proof["acceptance_status"] == "BLOCKED_INPUT"
    for document in (classification, parity, proof):
        assert document["biological_accuracy_accepted"] is False
        assert document["bindings"]["run_id"] == "run-1"
        assert document["bindings"]["profile_sha256"] == _PROFILE
        assert document["bindings"]["snapshot_manifest_sha256"] == _SNAPSHOT
        assert document["bindings"]["source_name"] == "profile.json"


def test_local_pass_does_not_become_ci_or_biological_acceptance(tmp_path: Path) -> None:
    receipt = _receipt(
        status="PASS",
        checks={
            "stage0_admission": "PASS",
            "reference_cases": "PASS",
            "evidence_integrity": "PASS",
            "semantic_determinism": "PASS",
            "pipeline_integration": "NOT_RUN",
        },
    )
    output = _publish(tmp_path, receipt)
    classification = _load(output, CLASSIFICATION_VERIFICATION)
    proof = _load(output, PROOF_VERIFICATION)
    parity = _load(output, M_PARITY_REPORT)
    assert set(classification["checks"].values()) == {"PASS"}
    assert classification["biological_accuracy_accepted"] is False
    assert proof["checks"]["pipeline_integration"] == "NOT_RUN"
    assert proof["ci"]["status"] == "NOT_RUN"
    assert proof["acceptance_status"] == "PASS"
    assert parity["measured"] is False
    assert "stage0_admission" not in proof["checks"]


def test_existing_report_is_kept_and_siblings_are_not_created(tmp_path: Path) -> None:
    output = tmp_path / "acceptance"
    output.mkdir()
    kept = output / CLASSIFICATION_VERIFICATION
    kept.write_text("original\n", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exist"):
        publish_acceptance_reports(
            output,
            root=output,
            receipt=_receipt(),
            profile_sha256=_PROFILE,
            source_name="profile.json",
            pipeline_proof=None,
            pipeline_report=None,
        )
    assert kept.read_text(encoding="utf-8") == "original\n"
    assert not (output / M_PARITY_REPORT).exists()
    assert not (output / PROOF_VERIFICATION).exists()


def test_second_publish_does_not_replace_reports(tmp_path: Path) -> None:
    output = _publish(tmp_path, _receipt())
    before = {
        name: (output / name).read_bytes()
        for name in (
            CLASSIFICATION_VERIFICATION,
            M_PARITY_REPORT,
            PROOF_VERIFICATION,
        )
    }
    with pytest.raises(FileExistsError, match="already exist"):
        publish_acceptance_reports(
            output,
            root=output,
            receipt=_receipt(status="PASS"),
            profile_sha256=_PROFILE,
            source_name="profile.json",
            pipeline_proof=None,
            pipeline_report=None,
        )
    for name, payload in before.items():
        assert (output / name).read_bytes() == payload


def test_ci_pass_without_head_sha_writes_nothing(tmp_path: Path) -> None:
    output = tmp_path / "acceptance"
    output.mkdir()
    with pytest.raises(ValueError, match="CI PASS requires the head SHA"):
        publish_acceptance_reports(
            output,
            root=output,
            receipt=_receipt(),
            profile_sha256=_PROFILE,
            source_name="profile.json",
            pipeline_proof=None,
            pipeline_report=None,
            ci_status="PASS",
        )
    assert list(output.iterdir()) == []


def test_proof_file_hash_is_bound_without_marking_ci(tmp_path: Path) -> None:
    proof = tmp_path / "pipeline-proof.json"
    proof.write_bytes(b'{"artifact":"proof"}\n')
    output = tmp_path / "acceptance"
    output.mkdir()
    publish_acceptance_reports(
        output,
        root=output,
        receipt=_receipt(),
        profile_sha256=_PROFILE,
        source_name="profile.json",
        pipeline_proof=proof,
        pipeline_report=None,
    )
    document = _load(output, PROOF_VERIFICATION)
    digest = document["bindings"]["pipeline_proof_sha256"]
    assert isinstance(digest, str) and len(digest) == 64
    assert document["ci"]["status"] == "NOT_RUN"
    assert document["bindings"]["pipeline_report_sha256"] is None


def test_blocked_input_keeps_reports_when_label_hash_is_not_sha256(
    tmp_path: Path,
) -> None:
    receipt = _receipt(expected_labels_sha256="abc")
    output = _publish(tmp_path, receipt)
    classification = _load(output, CLASSIFICATION_VERIFICATION)
    assert classification["bindings"]["expected_labels_sha256"] is None
    assert classification["bindings"]["snapshot_manifest_sha256"] == _SNAPSHOT
    assert (output / M_PARITY_REPORT).is_file()
    assert (output / PROOF_VERIFICATION).is_file()


def test_successful_acceptance_still_requires_a_label_sha256(tmp_path: Path) -> None:
    output = tmp_path / "acceptance"
    output.mkdir()
    with pytest.raises(ValueError, match="expected_labels_sha256"):
        publish_acceptance_reports(
            output,
            root=output,
            receipt=_receipt(status="PASS", expected_labels_sha256="abc"),
            profile_sha256=_PROFILE,
            source_name="profile.json",
            pipeline_proof=None,
            pipeline_report=None,
        )
    assert list(output.iterdir()) == []


def test_ci_pass_records_a_git_commit_id(tmp_path: Path) -> None:
    head = "73a6368fbe9ee8a2644bf780f33afd567889f6bd"
    output = tmp_path / "acceptance"
    output.mkdir()
    publish_acceptance_reports(
        output,
        root=output,
        receipt=_receipt(),
        profile_sha256=_PROFILE,
        source_name="profile.json",
        pipeline_proof=None,
        pipeline_report=None,
        ci_status="PASS",
        ci_head_sha=head,
    )
    proof = _load(output, PROOF_VERIFICATION)
    assert proof["ci"] == {"head_sha": head, "status": "PASS"}


def test_ci_head_rejects_a_file_digest(tmp_path: Path) -> None:
    output = tmp_path / "acceptance"
    output.mkdir()
    with pytest.raises(ValueError, match="40-character Git commit id"):
        publish_acceptance_reports(
            output,
            root=output,
            receipt=_receipt(),
            profile_sha256=_PROFILE,
            source_name="profile.json",
            pipeline_proof=None,
            pipeline_report=None,
            ci_status="PASS",
            ci_head_sha=_PROFILE,
        )
    assert list(output.iterdir()) == []


def test_tilde_output_is_expanded_before_publication(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))
    monkeypatch.setenv("USERPROFILE", str(home))
    target = home / "acceptance-run"
    target.mkdir()
    publish_acceptance_reports(
        Path("~/acceptance-run"),
        root=Path("~/acceptance-run"),
        receipt=_receipt(),
        profile_sha256=_PROFILE,
        source_name="profile.json",
        pipeline_proof=None,
        pipeline_report=None,
    )
    assert (target / CLASSIFICATION_VERIFICATION).is_file()
    assert (target / M_PARITY_REPORT).is_file()
    assert (target / PROOF_VERIFICATION).is_file()
    assert not (Path.cwd() / "~").exists()
