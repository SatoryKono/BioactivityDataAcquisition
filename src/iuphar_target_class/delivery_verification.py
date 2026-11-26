"""Write the three delivery reports as separate files.

Classification checks, the stage-5 M comparison, and pipeline-proof status
stay in different documents. A later publish does not replace an existing
sibling, and a local check is not recorded as CI.
"""

from __future__ import annotations

import os
import re
import tempfile
from collections.abc import Mapping
from pathlib import Path

from .comparison import ComparisonReport, Stage0Reference, compare_stage0
from .stage0.io import canonical_json_bytes, sha256_file

CLASSIFICATION_VERIFICATION = "classification-verification.json"
M_PARITY_REPORT = "m-parity-report.json"
PROOF_VERIFICATION = "proof-verification.json"
REPORT_NAMES = (
    CLASSIFICATION_VERIFICATION,
    M_PARITY_REPORT,
    PROOF_VERIFICATION,
)
CLASSIFICATION_CHECKS = (
    "stage0_admission",
    "reference_cases",
    "evidence_integrity",
    "semantic_determinism",
)
PROOF_CHECKS = ("pipeline_integration",)
_SHA256 = re.compile(r"[0-9a-f]{64}")
_GIT_SHA = re.compile(r"[0-9a-f]{40}")
_TEMP_PREFIX = ".iuphar-verification-"


def publish_acceptance_reports(
    output_dir: Path,
    *,
    root: Path,
    receipt: Mapping[str, object],
    profile_sha256: str,
    source_name: str,
    pipeline_proof: Path | None,
    pipeline_report: Path | None,
    ci_status: str = "NOT_RUN",
    ci_head_sha: str | None = None,
) -> tuple[Path, Path, Path]:
    """Publish the acceptance siblings. This command supplies no M rows."""
    bindings = _bindings(
        receipt,
        profile_sha256=profile_sha256,
        source_name=source_name,
        pipeline_proof_sha256=_file_sha256(pipeline_proof),
        pipeline_report_sha256=_file_sha256(pipeline_report),
    )
    biological = _bool(receipt, "biological_accuracy_accepted")
    parity = compare_stage0(Stage0Reference(source_name, 0, ()), ())
    documents = {
        CLASSIFICATION_VERIFICATION: _classification_document(
            bindings,
            _checks(receipt, CLASSIFICATION_CHECKS),
            biological,
        ),
        M_PARITY_REPORT: _parity_document(
            bindings, parity, biological, m_rows_supplied=0
        ),
        PROOF_VERIFICATION: _proof_document(
            bindings,
            _checks(receipt, PROOF_CHECKS),
            biological,
            acceptance_status=_text(receipt, "status"),
            ci_status=ci_status,
            ci_head_sha=ci_head_sha,
        ),
    }
    return _publish(output_dir, root=root, documents=documents)


def _classification_document(
    bindings: dict[str, object],
    checks: dict[str, str],
    biological_accuracy_accepted: bool,
) -> dict[str, object]:
    return {
        "artifact": "bioetl_iuphar_classification_verification",
        "schema_version": 1,
        "bindings": bindings,
        "biological_accuracy_accepted": biological_accuracy_accepted,
        "checks": checks,
    }


def _parity_document(
    bindings: dict[str, object],
    report: ComparisonReport,
    biological_accuracy_accepted: bool,
    *,
    m_rows_supplied: int,
) -> dict[str, object]:
    return {
        "artifact": "bioetl_iuphar_m_parity_report",
        "schema_version": 1,
        "bindings": bindings,
        "biological_accuracy_accepted": biological_accuracy_accepted,
        "measured": report.measured,
        "reason": report.reason,
        "m_rows_supplied": m_rows_supplied,
        "changes": [list(item) for item in report.changes],
        "residual": list(report.residual),
        "metrics": report.metrics,
        "source_overwritten": report.source_overwritten,
        "legacy_values": [list(item) for item in report.legacy_values],
    }


def _proof_document(
    bindings: dict[str, object],
    checks: dict[str, str],
    biological_accuracy_accepted: bool,
    *,
    acceptance_status: str,
    ci_status: str,
    ci_head_sha: str | None,
) -> dict[str, object]:
    head_sha = _git_head_sha(ci_head_sha, required=ci_status == "PASS")
    return {
        "artifact": "bioetl_iuphar_proof_verification",
        "schema_version": 1,
        "bindings": bindings,
        "acceptance_status": acceptance_status,
        "biological_accuracy_accepted": biological_accuracy_accepted,
        "checks": checks,
        "ci": {"head_sha": head_sha, "status": ci_status},
    }


def _bindings(
    receipt: Mapping[str, object],
    *,
    profile_sha256: str,
    source_name: str,
    pipeline_proof_sha256: str | None,
    pipeline_report_sha256: str | None,
) -> dict[str, object]:
    if not source_name.strip() or "/" in source_name or "\\" in source_name:
        raise ValueError("source name must be a single path segment")
    return {
        "run_id": _text(receipt, "run_id"),
        "profile_sha256": _sha256(profile_sha256, "profile_sha256"),
        "snapshot_manifest_sha256": _sha256(
            _text(receipt, "snapshot_manifest_sha256"),
            "snapshot_manifest_sha256",
        ),
        "normalization_version": _text(receipt, "normalization_version"),
        "rules_version": _text(receipt, "rules_version"),
        "classification_schema_version": _text(
            receipt, "classification_schema_version"
        ),
        "source_name": source_name,
        "stage0_manifest_sha256": _optional_sha(receipt, "stage0_manifest_sha256"),
        "expected_labels_sha256": _optional_sha(receipt, "expected_labels_sha256"),
        "pipeline_proof_sha256": pipeline_proof_sha256,
        "pipeline_report_sha256": pipeline_report_sha256,
    }


def _publish(
    output_dir: Path,
    *,
    root: Path,
    documents: Mapping[str, Mapping[str, object]],
) -> tuple[Path, Path, Path]:
    destinations = {name: _contained(output_dir / name, root) for name in REPORT_NAMES}
    if any(_entry(path) for path in destinations.values()):
        raise FileExistsError("delivery verification files already exist")
    created: list[Path] = []
    try:
        for name in REPORT_NAMES:
            payload = canonical_json_bytes(documents[name])
            if not _create_new(destinations[name], payload, root=root):
                raise FileExistsError(name)
            created.append(destinations[name])
    except Exception:
        for path in created:
            path.unlink(missing_ok=True)
        raise
    return (
        destinations[REPORT_NAMES[0]],
        destinations[REPORT_NAMES[1]],
        destinations[REPORT_NAMES[2]],
    )


def _checks(receipt: Mapping[str, object], names: tuple[str, ...]) -> dict[str, str]:
    raw = receipt.get("checks")
    checks = raw if isinstance(raw, Mapping) else {}
    selected: dict[str, str] = {}
    for name in names:
        value = checks.get(name, "NOT_RUN")
        if not isinstance(value, str) or not value.strip():
            raise ValueError(f"check {name} has no status")
        selected[name] = value
    return selected


def _text(receipt: Mapping[str, object], key: str) -> str:
    value = receipt.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"receipt {key} is missing")
    return value


def _bool(receipt: Mapping[str, object], key: str) -> bool:
    value = receipt.get(key)
    if not isinstance(value, bool):
        raise ValueError(f"receipt {key} must be boolean")
    return value


def _sha256(value: str, label: str) -> str:
    if _SHA256.fullmatch(value) is None:
        raise ValueError(f"{label} must be a lowercase SHA-256")
    return value


def _git_head_sha(value: str | None, *, required: bool) -> str | None:
    """Accept a Git commit id. File digests stay on the SHA-256 bindings."""
    if value is None:
        if required:
            raise ValueError("CI PASS requires the head SHA that ran it")
        return None
    if _GIT_SHA.fullmatch(value) is None:
        raise ValueError("CI head SHA must be a 40-character Git commit id")
    return value


def _optional_sha(receipt: Mapping[str, object], key: str) -> str | None:
    value = receipt.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(f"receipt {key} must be a SHA-256 or null")
    if _SHA256.fullmatch(value) is None:
        if receipt.get("status") == "BLOCKED_INPUT":
            return None
        raise ValueError(f"{key} must be a lowercase SHA-256")
    return value


def _file_sha256(path: Path | None) -> str | None:
    if path is None or not path.is_file():
        return None
    return sha256_file(path)


def _contained(path: Path, root: Path) -> Path:
    expanded = path.expanduser()
    root_resolved = root.expanduser().resolve()
    parent = expanded.parent.resolve()
    if expanded.name in {"", ".", ".."} or not parent.is_relative_to(root_resolved):
        raise ValueError("verification path escapes its output root")
    return parent / expanded.name


def _entry(path: Path) -> bool:
    try:
        path.lstat()
    except FileNotFoundError:
        return False
    return True


def _create_new(path: Path, payload: bytes, *, root: Path) -> bool:
    destination = _contained(path, root)
    if _entry(destination):
        return False
    temporary: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            dir=destination.parent,
            prefix=_TEMP_PREFIX,
            suffix=".tmp",
            delete=False,
        ) as handle:
            temporary = Path(handle.name)
            handle.write(payload)
        try:
            os.link(temporary, destination)
        except FileExistsError:
            return False
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)
    return True
