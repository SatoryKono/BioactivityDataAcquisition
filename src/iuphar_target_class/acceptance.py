"""Acceptance report. A check is PASS only when this run executed it."""

from __future__ import annotations

import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path

from .models import RawTargetRow, RunProvenance
from .normalization import classify_batch, validate_batch
from .policy import PLAN_VERSION, policy_document
from .stage0.io import atomic_write_bytes, canonical_json_bytes
from .w153 import INTEGRATION_REASON

# RF-001 immutable_hash_locked acceptance report; live PLAN_VERSION publishes elsewhere.
STAGES_0_3_LOCKED_RULES_VERSION = "plan-v1-r8"

NOT_RUN_REASONS: dict[str, str] = {
    "api_smoke": "сохранённых ответов API нет",
    "gold_cases": "эталонные случаи не подтверждены",
    "graph_limits_boundary": (
        "значения graph_limits записаны; граничный прогон на пределе и "
        "пределе + 1 не выполнялся"
    ),
    "http_transport": (
        "параметры адаптера записаны; эксплуатационная проверка HTTP не запускалась"
    ),
    "isoform_policy": "политика изоформ не утверждена",
    "missing_markers_version": "версия missing_markers не утверждена",
    "quality_counts": "эталонный набор этапа 0 пуст, числа качества не измерены",
    "real_data": "происхождение IUPHAR на этапе 0 не установлено",
    "snapshot_coverage": "охват и набор видов снимка не утверждены",
    "w153_integration": INTEGRATION_REASON,
}
UNEXECUTED_REASONS: dict[str, str] = {
    "volume_scenario": "объёмный прогон в этом отчёте не выполнялся",
}
_VOLUME_PROVENANCE = RunProvenance(
    snapshot_id="snapshot-unset",
    normalization_version=None,
    rules_version=PLAN_VERSION,
    schema_version=PLAN_VERSION,
    retrieved_at="2026-11-11T00:00:00Z",
    run_started_at="2026-11-11T00:00:01Z",
)
_VOLUME_ROWS: tuple[dict[str, str], ...] = (
    {
        "gene_symbol": "GENE1",
        "input_row_id": "volume-1",
        "target_kind": "protein",
    },
    {
        "input_row_id": "volume-2",
        "target_kind": "protein",
        "uniprot": "P04637",
    },
    {
        "gene_symbol": "GENE3",
        "input_row_id": "volume-3",
        "target_kind": "complex",
    },
)
_ROW_META = frozenset({"input_row_id", "target_kind"})


def build_acceptance_report(executed: Mapping[str, str]) -> dict[str, object]:
    """Merge executed results with the checks that cannot be marked PASS."""
    names = set(executed) | set(NOT_RUN_REASONS) | set(UNEXECUTED_REASONS)
    checks: list[dict[str, str]] = []
    for name in sorted(names):
        if executed.get(name) == "FAIL":
            checks.append({"name": name, "reason": "", "status": "FAIL"})
            continue
        if name in NOT_RUN_REASONS:
            checks.append(
                {"name": name, "reason": NOT_RUN_REASONS[name], "status": "NOT_RUN"}
            )
            continue
        if name not in executed:
            checks.append(
                {
                    "name": name,
                    "reason": UNEXECUTED_REASONS[name],
                    "status": "NOT_RUN",
                }
            )
            continue
        status = executed[name]
        if status not in {"PASS", "FAIL"}:
            status = "NOT_RUN"
        checks.append({"name": name, "reason": "", "status": status})
    return {
        "biological_accuracy_accepted": False,
        "checks": checks,
        "mapping_version": None,
        "rules_version": PLAN_VERSION,
        "schema_version": None,
        "snapshot_coverage": "не утверждено",
        "snapshot_id": None,
        "statement": (
            "Без проверенных данных разработка на синтетических fixtures допустима, "
            "биологическая точность не принимается."
        ),
    }


@dataclass(frozen=True, slots=True)
class VolumeResult:
    """Timed result of one offline volume run. It assigns no class."""

    status: str
    row_count: int
    elapsed_seconds: float
    limit_seconds: int
    reason: str


def volume_fixture_document() -> dict[str, object]:
    """Synthetic stages 0–3 rows. The stage-0 IUPHAR source stays empty."""
    return {
        "artifact": "volume_fixture",
        "biological_accuracy_accepted": False,
        "kind": "synthetic",
        "rows": [dict(row) for row in _VOLUME_ROWS],
        "stage0_selected_source_count": 0,
        "stages": ["0", "1", "2", "3"],
    }


def volume_fixture_rows() -> tuple[RawTargetRow, ...]:
    """Return the committed synthetic rows in fixture order."""
    return tuple(
        RawTargetRow(
            row["input_row_id"],
            {key: value for key, value in row.items() if key not in _ROW_META},
            target_kind=row["target_kind"],
        )
        for row in _VOLUME_ROWS
    )


def run_volume_scenario(
    rows: tuple[RawTargetRow, ...],
    *,
    limit_seconds: int,
    clock: Callable[[], float] = time.perf_counter,
) -> VolumeResult:
    """Validate a non-empty fixture offline and compare elapsed time to the limit."""
    if limit_seconds <= 0:
        message = "volume_test_seconds must be positive"
        raise ValueError(message)
    if not rows:
        return VolumeResult("FAIL", 0, 0.0, limit_seconds, "фиксация объёма пуста")
    started = clock()
    validated = validate_batch(rows, provenance=_VOLUME_PROVENANCE)
    elapsed = clock() - started
    if any(row.input_validation_status != "valid" for row in validated):
        return VolumeResult(
            "FAIL",
            len(rows),
            elapsed,
            limit_seconds,
            "строка фиксации не прошла проверку входа",
        )
    if elapsed > limit_seconds:
        return VolumeResult(
            "FAIL",
            len(rows),
            elapsed,
            limit_seconds,
            "время превысило volume_test_seconds",
        )
    return VolumeResult("PASS", len(rows), elapsed, limit_seconds, "")


def stages_0_3_document(*, rules_version: str | None = None) -> dict[str, object]:
    """Report for stages 0–3. Unrun checks stay NOT_RUN.

    ``rules_version`` defaults to live ``PLAN_VERSION``. The RF-001 locked
    artifact uses ``STAGES_0_3_LOCKED_RULES_VERSION`` so historical bytes stay
    immutable when the plan pin advances.
    """
    parameters = policy_document()["parameters"]
    if not isinstance(parameters, dict):
        message = "policy parameters are missing"
        raise ValueError(message)
    limit = parameters["volume_test_seconds"]
    if not isinstance(limit, int):
        message = "volume_test_seconds is not approved"
        raise ValueError(message)
    volume = run_volume_scenario(volume_fixture_rows(), limit_seconds=limit)
    boundaries = _boundary_checks()
    executed = {
        "all_invalid_batch": boundaries["all_invalid_batch"],
        "empty_batch": boundaries["empty_batch"],
        "synthetic_volume_smoke": volume.status,
    }
    report = build_acceptance_report(executed)
    version = PLAN_VERSION if rules_version is None else rules_version
    return {
        "artifact": "stages_0_3_acceptance",
        "biological_accuracy_accepted": False,
        "checks": report["checks"],
        "fixture_kind": "synthetic",
        "fixture_row_count": volume.row_count,
        "rules_version": version,
        "stage0_selected_source_count": 0,
        "stages": ["0", "1", "2", "3"],
        "statement": report["statement"],
        "traceability": [
            {
                "check": "all_invalid_batch",
                "status": boundaries["all_invalid_batch"],
                "test": (
                    "tests/unit/iuphar_target_class/"
                    "test_normalization.py::test_all_invalid_batch"
                ),
            },
            {
                "check": "empty_batch",
                "status": boundaries["empty_batch"],
                "test": (
                    "tests/unit/iuphar_target_class/"
                    "test_normalization.py::test_normalize_iuphar_empty_batch"
                ),
            },
            {
                "check": "synthetic_volume_smoke",
                "status": volume.status,
                "test": (
                    "tests/unit/iuphar_target_class/"
                    "test_acceptance.py::"
                    "test_volume_scenario_finishes_within_the_approved_limit"
                ),
            },
            {
                "check": "volume_scenario",
                "status": "NOT_RUN",
                "test": "requires admitted full Stage-0 cohort via run_admitted_volume",
            },
        ],
        "volume_test_seconds": limit,
        "volume_test_time_status": parameters["volume_test_time_status"],
    }


def stages_0_3_live_report_name() -> str:
    """Filename for the live PLAN_VERSION stages 0–3 acceptance run."""
    return f"stages_0_3_report.{PLAN_VERSION}.json"


def publish_volume_artifacts(root: Path) -> None:
    """Write the fixture, locked RF-001 report, and live plan report."""
    output = root / "data" / "iuphar_target_class" / "acceptance"
    atomic_write_bytes(
        output / "volume_fixture.json",
        canonical_json_bytes(volume_fixture_document()),
        root=root,
    )
    atomic_write_bytes(
        output / "stages_0_3_report.json",
        canonical_json_bytes(
            stages_0_3_document(rules_version=STAGES_0_3_LOCKED_RULES_VERSION)
        ),
        root=root,
    )
    atomic_write_bytes(
        output / stages_0_3_live_report_name(),
        canonical_json_bytes(stages_0_3_document()),
        root=root,
    )


def _boundary_checks() -> dict[str, str]:
    """Execute the empty and all-invalid boundaries in this process."""
    empty = classify_batch((), provenance=_VOLUME_PROVENANCE)
    invalid = classify_batch(
        (
            RawTargetRow("", {}, target_kind="other"),
            RawTargetRow("row-2", {}, target_kind=None),
        ),
        provenance=_VOLUME_PROVENANCE,
    )
    empty_pass = (
        empty.status == "empty"
        and empty.quality.row_count == 0
        and empty.quality.classified_count == 0
    )
    invalid_pass = (
        invalid.status == "rejected"
        and invalid.quality.classified_count == 0
        and invalid.quality.row_count == 2
    )
    return {
        "all_invalid_batch": "PASS" if invalid_pass else "FAIL",
        "empty_batch": "PASS" if empty_pass else "FAIL",
    }
