#!/usr/bin/env python3
"""Validate semantic pair-matrix drift budgets."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import sys
from collections import Counter
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BUDGET_PATH = (
    REPO_ROOT / "configs" / "field_registry" / "semantic_pair_matrix_budget.yaml"
)
DEFAULT_REVIEW_REGISTRY_PATH = (
    REPO_ROOT / "configs" / "field_registry" / "semantic_audit_review_registry.yaml"
)
PAIR_MATRIX_PREFIX = "semantic_pair_matrix_"
PAIR_MATRIX_PATTERN = re.compile(r"^semantic_pair_matrix_(\d{4}-\d{2}-\d{2})\.csv$")
ROW_KEY_FIELDS = (
    "Cluster ID",
    "Pipeline A",
    "Field A",
    "Pipeline B",
    "Field B",
)

if __package__ in {None, ""}:
    sys.path.insert(0, str(REPO_ROOT))


@dataclass(frozen=True, slots=True)
class PairMatrixFinding:
    """One semantic pair-matrix budget finding."""

    kind: str
    row_key: str
    cluster_id: str
    message: str

    def as_dict(self) -> dict[str, str]:
        """Return a JSON-serializable finding payload."""
        return {
            "kind": self.kind,
            "row_key": self.row_key,
            "cluster_id": self.cluster_id,
            "message": self.message,
        }


@dataclass(frozen=True, slots=True)
class PairMatrixBudgetResult:
    """Semantic pair-matrix budget validation result."""

    risk_counts: dict[str, int]
    findings: tuple[PairMatrixFinding, ...]

    @property
    def ok(self) -> bool:
        """Return whether no budget findings were found."""
        return not self.findings


def _load_yaml(path: Path, *, root: Path | None = None) -> dict[str, Any]:
    from scripts.engineering.common.repo_paths import REPO_ROOT, resolve_output_path

    path = resolve_output_path(path, root=root or REPO_ROOT)
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    if isinstance(payload, dict):
        return payload
    raise ValueError(f"Expected YAML mapping in {path}")


def _matrix_path(repo_root: Path, budget: dict[str, Any]) -> Path:
    value = budget.get("matrix_path")
    if not isinstance(value, str):
        raise ValueError("semantic pair-matrix budget must define matrix_path")
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _snapshot_date_from_matrix_path(path: Path) -> date | None:
    match = PAIR_MATRIX_PATTERN.match(path.name)
    if match is None:
        return None
    return date.fromisoformat(match.group(1))


def _latest_generated_matrix_path(repo_root: Path) -> Path | None:
    report_dir = repo_root / "reports" / "semantic_pipeline_audit"
    candidates = sorted(report_dir.glob(f"{PAIR_MATRIX_PREFIX}*.csv"))
    return candidates[-1] if candidates else None


def _row_key(row: dict[str, str]) -> str:
    seed = "|".join(row[field] for field in ROW_KEY_FIELDS)
    return hashlib.sha256(seed.encode("utf-8")).hexdigest()[:16]


def _load_matrix_rows(matrix_path: Path) -> tuple[dict[str, str], ...]:
    with matrix_path.open(encoding="utf-8", newline="") as handle:
        return tuple(csv.DictReader(handle))


def _reviewed_rows(payload: dict[str, Any]) -> dict[str, dict[str, Any]]:
    rows = payload.get("reviewed_critical_rows", [])
    if not isinstance(rows, list):
        return {}
    reviewed: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not isinstance(row, dict):
            continue
        row_key = row.get("row_key")
        if isinstance(row_key, str):
            reviewed[row_key] = row
    return reviewed


def _review_registry_path(repo_root: Path, budget: dict[str, Any]) -> Path:
    value = budget.get("review_registry_path")
    if not isinstance(value, str):
        return DEFAULT_REVIEW_REGISTRY_PATH
    path = Path(value)
    return path if path.is_absolute() else repo_root / path


def _review_covers_cluster(
    review: dict[str, Any],
    *,
    cluster_id: str,
    semantic_status: str,
) -> bool:
    statuses = review.get("semantic_statuses", [])
    if isinstance(statuses, list) and statuses:
        normalized_statuses = {str(status).upper() for status in statuses}
        if semantic_status.upper() not in normalized_statuses:
            return False

    clusters = review.get("clusters")
    if clusters is None:
        return True
    return isinstance(clusters, list) and cluster_id in {str(item) for item in clusters}


def _cluster_has_review(
    review_registry: dict[str, Any],
    *,
    cluster_id: str,
    semantic_status: str,
) -> bool:
    for section in ("risk_reviews", "semantic_reviews", "warning_reviews"):
        reviews = review_registry.get(section, [])
        if not isinstance(reviews, list):
            continue
        for review in reviews:
            if not isinstance(review, dict):
                continue
            if _review_covers_cluster(
                review,
                cluster_id=cluster_id,
                semantic_status=semantic_status,
            ):
                return True
    return False


def _review_registry_metadata_findings(
    review_registry: dict[str, Any],
    *,
    today: date,
) -> list[PairMatrixFinding]:
    findings: list[PairMatrixFinding] = []
    for section in ("risk_reviews", "semantic_reviews", "warning_reviews"):
        reviews = review_registry.get(section, [])
        if not isinstance(reviews, list):
            continue
        for review in reviews:
            if not isinstance(review, dict):
                continue
            review_id = str(review.get("id") or "<unknown>")
            for field in ("owner", "rationale", "expires_on"):
                if review.get(field):
                    continue
                findings.append(
                    PairMatrixFinding(
                        kind="missing_review_registry_metadata",
                        row_key=review_id,
                        cluster_id=review_id,
                        message=f"{section} entry {review_id} is missing {field}",
                    )
                )
            expires_on = review.get("expires_on")
            if not isinstance(expires_on, str):
                continue
            try:
                expiry = date.fromisoformat(expires_on)
            except ValueError:
                findings.append(
                    PairMatrixFinding(
                        kind="invalid_review_registry_expiry",
                        row_key=review_id,
                        cluster_id=review_id,
                        message=f"{section} entry {review_id} has invalid expiry {expires_on!r}",
                    )
                )
                continue
            if expiry < today:
                findings.append(
                    PairMatrixFinding(
                        kind="expired_review_registry_entry",
                        row_key=review_id,
                        cluster_id=review_id,
                        message=f"{section} entry {review_id} expired on {expires_on}",
                    )
                )
    return findings


def _metadata_findings(
    reviewed: dict[str, dict[str, Any]],
    *,
    today: date,
) -> list[PairMatrixFinding]:
    findings: list[PairMatrixFinding] = []
    for row_key, row in reviewed.items():
        cluster_id = str(row.get("cluster_id") or "<unknown>")
        for field in ("owner", "rationale", "expires_on"):
            if row.get(field):
                continue
            findings.append(
                PairMatrixFinding(
                    kind="missing_review_metadata",
                    row_key=row_key,
                    cluster_id=cluster_id,
                    message=f"reviewed row {row_key} is missing {field}",
                )
            )
        expires_on = row.get("expires_on")
        if not isinstance(expires_on, str):
            continue
        try:
            expiry = date.fromisoformat(expires_on)
        except ValueError:
            findings.append(
                PairMatrixFinding(
                    kind="invalid_review_expiry",
                    row_key=row_key,
                    cluster_id=cluster_id,
                    message=f"reviewed row {row_key} has invalid expiry {expires_on!r}",
                )
            )
            continue
        if expiry < today:
            findings.append(
                PairMatrixFinding(
                    kind="expired_review",
                    row_key=row_key,
                    cluster_id=cluster_id,
                    message=f"reviewed row {row_key} expired on {expires_on}",
                )
            )
    return findings


def _budget_findings(
    risk_counts: dict[str, int],
    budget: dict[str, Any],
) -> list[PairMatrixFinding]:
    budgets = budget.get("budgets", {})
    if not isinstance(budgets, dict):
        return [
            PairMatrixFinding(
                kind="missing_budget_section",
                row_key="<budget>",
                cluster_id="<budget>",
                message="semantic pair-matrix budget must define budgets",
            )
        ]

    findings: list[PairMatrixFinding] = []
    for risk, risk_budget in budgets.items():
        if not isinstance(risk, str) or not isinstance(risk_budget, dict):
            continue
        max_count = risk_budget.get("max_count")
        if not isinstance(max_count, int):
            continue
        actual = risk_counts.get(risk, 0)
        if actual <= max_count:
            continue
        findings.append(
            PairMatrixFinding(
                kind="risk_count_budget_exceeded",
                row_key=risk,
                cluster_id=risk,
                message=f"{risk} row count {actual} exceeds budget {max_count}",
            )
        )
    return findings


def _status_budget_findings(
    rows: tuple[dict[str, str], ...],
    budget: dict[str, Any],
    review_registry: dict[str, Any],
) -> list[PairMatrixFinding]:
    status_budgets = budget.get("status_budgets", [])
    if not isinstance(status_budgets, list):
        return []

    findings: list[PairMatrixFinding] = []
    for status_budget in status_budgets:
        if not isinstance(status_budget, dict):
            continue
        column = status_budget.get("column")
        value = status_budget.get("value")
        if not isinstance(column, str) or not isinstance(value, str):
            continue
        matching_rows = [row for row in rows if row.get(column) == value]
        max_count = status_budget.get("max_count")
        if isinstance(max_count, int) and len(matching_rows) > max_count:
            findings.append(
                PairMatrixFinding(
                    kind="status_count_budget_exceeded",
                    row_key=f"{column}:{value}",
                    cluster_id=f"{column}:{value}",
                    message=(
                        f"{column}={value} row count {len(matching_rows)} "
                        f"exceeds budget {max_count}"
                    ),
                )
            )
        if not status_budget.get("require_reviewed_clusters"):
            continue
        unreviewed = sorted(
            {
                row.get("Cluster ID", "<unknown>")
                for row in matching_rows
                if not _cluster_has_review(
                    review_registry,
                    cluster_id=row.get("Cluster ID", "<unknown>"),
                    semantic_status=row.get("Semantic Status", ""),
                )
            }
        )
        for cluster_id in unreviewed:
            findings.append(
                PairMatrixFinding(
                    kind="unreviewed_status_cluster",
                    row_key=f"{column}:{value}:{cluster_id}",
                    cluster_id=cluster_id,
                    message=(
                        f"{column}={value} cluster {cluster_id} is not covered "
                        "by semantic_audit_review_registry reviews"
                    ),
                )
            )
    return findings


def _critical_row_findings(
    rows: tuple[dict[str, str], ...],
    reviewed: dict[str, dict[str, Any]],
) -> list[PairMatrixFinding]:
    critical_rows = [row for row in rows if row.get("Drift Risk") == "CRITICAL"]
    current_by_key = {_row_key(row): row for row in critical_rows}
    findings: list[PairMatrixFinding] = []

    for row_key, row in current_by_key.items():
        if row_key in reviewed:
            continue
        findings.append(
            PairMatrixFinding(
                kind="unreviewed_critical_row",
                row_key=row_key,
                cluster_id=row.get("Cluster ID", "<unknown>"),
                message=(
                    f"CRITICAL row {row_key} "
                    f"{row.get('Cluster ID')}:{row.get('Pipeline A')}.{row.get('Field A')} "
                    f"vs {row.get('Pipeline B')}.{row.get('Field B')} is not reviewed"
                ),
            )
        )

    for row_key, reviewed_row in reviewed.items():
        if row_key in current_by_key:
            continue
        findings.append(
            PairMatrixFinding(
                kind="stale_reviewed_critical_row",
                row_key=row_key,
                cluster_id=str(reviewed_row.get("cluster_id") or "<unknown>"),
                message=(
                    f"reviewed critical row {row_key} is no longer present; "
                    "remove the stale budget entry"
                ),
            )
        )
    return findings


def _snapshot_binding_findings(
    *,
    repo_root: Path,
    budget: dict[str, Any],
) -> list[PairMatrixFinding]:
    findings: list[PairMatrixFinding] = []
    matrix_path = _matrix_path(repo_root, budget)
    reviewed_on = budget.get("reviewed_on")
    if not isinstance(reviewed_on, str):
        return [
            PairMatrixFinding(
                kind="missing_reviewed_on",
                row_key="<budget>",
                cluster_id="<budget>",
                message="semantic pair-matrix budget must define reviewed_on",
            )
        ]

    try:
        reviewed_on_date = date.fromisoformat(reviewed_on)
    except ValueError:
        return [
            PairMatrixFinding(
                kind="invalid_reviewed_on",
                row_key="<budget>",
                cluster_id="<budget>",
                message=f"semantic pair-matrix budget has invalid reviewed_on {reviewed_on!r}",
            )
        ]

    matrix_date = _snapshot_date_from_matrix_path(matrix_path)
    if matrix_date is not None and matrix_date != reviewed_on_date:
        findings.append(
            PairMatrixFinding(
                kind="reviewed_snapshot_mismatch",
                row_key="<budget>",
                cluster_id="<budget>",
                message=(
                    f"semantic pair-matrix budget reviewed_on={reviewed_on} does not match "
                    f"matrix snapshot {matrix_path.name}"
                ),
            )
        )

    latest_matrix_path = _latest_generated_matrix_path(repo_root)
    latest_matrix_date = (
        _snapshot_date_from_matrix_path(latest_matrix_path)
        if latest_matrix_path is not None
        else None
    )
    if (
        latest_matrix_path is not None
        and latest_matrix_path != matrix_path
        and latest_matrix_date is not None
        and latest_matrix_date > reviewed_on_date
    ):
        findings.append(
            PairMatrixFinding(
                kind="stale_reviewed_snapshot",
                row_key="<budget>",
                cluster_id="<budget>",
                message=(
                    f"semantic pair-matrix budget still targets {matrix_path.name}, "
                    f"but newer generated snapshot {latest_matrix_path.name} exists and "
                    "must be explicitly reviewed or promoted"
                ),
            )
        )
    return findings


def _reviewed_identity_findings(
    rows: tuple[dict[str, str], ...],
    reviewed: dict[str, dict[str, Any]],
) -> list[PairMatrixFinding]:
    current_by_key = {
        _row_key(row): row for row in rows if row.get("Drift Risk") == "CRITICAL"
    }
    findings: list[PairMatrixFinding] = []
    field_pairs = (
        ("cluster_id", "Cluster ID"),
        ("pipeline_a", "Pipeline A"),
        ("field_a", "Field A"),
        ("pipeline_b", "Pipeline B"),
        ("field_b", "Field B"),
    )
    for row_key, reviewed_row in reviewed.items():
        current = current_by_key.get(row_key)
        if current is None:
            continue
        for review_field, matrix_field in field_pairs:
            expected = reviewed_row.get(review_field)
            actual = current.get(matrix_field)
            if expected == actual:
                continue
            findings.append(
                PairMatrixFinding(
                    kind="reviewed_row_identity_mismatch",
                    row_key=row_key,
                    cluster_id=current.get("Cluster ID", "<unknown>"),
                    message=(
                        f"reviewed row {row_key} expected {review_field}={expected!r}, "
                        f"found {actual!r}"
                    ),
                )
            )
    return findings


def validate_semantic_pair_matrix_budget(
    *,
    repo_root: Path = REPO_ROOT,
    budget_path: Path = DEFAULT_BUDGET_PATH,
    today: date | None = None,
) -> PairMatrixBudgetResult:
    """Return semantic pair-matrix budget findings."""
    budget = _load_yaml(budget_path)
    rows = _load_matrix_rows(_matrix_path(repo_root, budget))
    risk_counts = dict(Counter(row.get("Drift Risk", "<unknown>") for row in rows))
    reviewed = _reviewed_rows(budget)
    review_registry = _load_yaml(_review_registry_path(repo_root, budget))

    findings: list[PairMatrixFinding] = []
    findings.extend(_budget_findings(risk_counts, budget))
    findings.extend(_status_budget_findings(rows, budget, review_registry))
    findings.extend(_metadata_findings(reviewed, today=today or date.today()))
    findings.extend(
        _review_registry_metadata_findings(
            review_registry,
            today=today or date.today(),
        )
    )
    findings.extend(_critical_row_findings(rows, reviewed))
    findings.extend(_reviewed_identity_findings(rows, reviewed))
    findings.extend(_snapshot_binding_findings(repo_root=repo_root, budget=budget))
    return PairMatrixBudgetResult(risk_counts=risk_counts, findings=tuple(findings))


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Validate semantic pair-matrix drift budgets.",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="fail with a non-zero exit code when findings are present",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="emit machine-readable validation output",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=REPO_ROOT,
        help="repository root containing reports and budget config",
    )
    parser.add_argument(
        "--budget-path",
        type=Path,
        default=DEFAULT_BUDGET_PATH,
        help="semantic pair-matrix budget YAML",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    result = validate_semantic_pair_matrix_budget(
        repo_root=args.repo_root,
        budget_path=args.budget_path,
    )
    if args.json:
        payload = {
            "ok": result.ok,
            "risk_counts": result.risk_counts,
            "finding_count": len(result.findings),
            "findings": [finding.as_dict() for finding in result.findings],
        }
        print(json.dumps(payload, indent=2, sort_keys=True))
    elif result.findings:
        print("[semantic-pair-matrix-budget] validation failed")
        for finding in result.findings:
            print(f"- {finding.message}")
    else:
        print("[semantic-pair-matrix-budget] ok")

    return 1 if args.check and result.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
