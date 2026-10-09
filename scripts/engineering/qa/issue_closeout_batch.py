#!/usr/bin/env python3
"""Evaluate many issue closeout criteria from one verified evidence bundle.

This command is read-only with respect to GitHub. It neither executes evidence
producers nor closes issues; it only emits a source-bound readiness report.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from jsonschema import Draft202012Validator

from memory.proof import load_policy, load_schema, verify_bundle

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_MANIFEST_SCHEMA = ROOT / "configs/quality/issue_closeout_batch.schema.json"


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bundle", type=Path, required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    parser.add_argument("--manifest-schema", type=Path, default=DEFAULT_MANIFEST_SCHEMA)
    return parser


def _read_object(path: Path, *, label: str) -> dict[str, Any]:
    resolved = path.expanduser().resolve()
    if not resolved.is_file():
        raise ValueError(f"{label} does not exist: {resolved}")
    try:
        if resolved.suffix.lower() in {".yaml", ".yml"}:
            payload = yaml.safe_load(resolved.read_text(encoding="utf-8"))
        else:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, yaml.YAMLError) as exc:
        raise ValueError(f"{label} is not valid JSON/YAML: {resolved}") from exc
    if not isinstance(payload, dict):
        raise ValueError(f"{label} must contain an object: {resolved}")
    return payload


def _validate_manifest(manifest: dict[str, Any], schema: dict[str, Any]) -> None:
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(manifest), key=lambda item: list(item.path))
    if errors:
        rendered = "; ".join(
            f"{'/'.join(str(part) for part in error.absolute_path) or '<root>'}: "
            f"{error.message}"
            for error in errors
        )
        raise ValueError(f"invalid closeout manifest: {rendered}")

    issue_numbers: set[int] = set()
    for issue in manifest["issues"]:
        number = int(issue["number"])
        if number in issue_numbers:
            raise ValueError(f"duplicate issue number: {number}")
        issue_numbers.add(number)
        criterion_ids: set[str] = set()
        for criterion in issue["criteria"]:
            criterion_id = str(criterion["id"])
            if criterion_id in criterion_ids:
                raise ValueError(
                    f"duplicate criterion id for issue {number}: {criterion_id}"
                )
            criterion_ids.add(criterion_id)


def _safe_output(path: Path, repo_root: Path) -> Path:
    output = path.expanduser().resolve()
    reports_root = (repo_root / "reports").resolve()
    if output.suffix.lower() != ".json" or not output.is_relative_to(reports_root):
        raise ValueError("output must be a JSON file below REPO_ROOT/reports")
    return output


def _matching_receipts(
    receipts: list[dict[str, Any]], requires: dict[str, str]
) -> list[dict[str, Any]]:
    if "receipt_id" in requires:
        return [
            receipt
            for receipt in receipts
            if receipt.get("receipt_id") == requires["receipt_id"]
        ]
    if "evidence_kind" in requires:
        return [
            receipt
            for receipt in receipts
            if receipt.get("evidence_kind") == requires["evidence_kind"]
        ]
    return []


def _evaluate_criterion(
    criterion: dict[str, Any],
    *,
    bundle_outcome: str,
    receipts: list[dict[str, Any]],
) -> dict[str, Any]:
    requires = criterion["requires"]
    if "bundle_outcome" in requires:
        passed = bundle_outcome == requires["bundle_outcome"]
        evidence = {"bundle_outcome": bundle_outcome}
    else:
        matching = _matching_receipts(receipts, requires)
        passing = [receipt for receipt in matching if receipt.get("status") == "pass"]
        passed = bundle_outcome == "ADMIT" and bool(passing)
        evidence = {
            "bundle_outcome": bundle_outcome,
            "matching_receipts": [
                {
                    "receipt_id": receipt.get("receipt_id"),
                    "evidence_kind": receipt.get("evidence_kind"),
                    "status": receipt.get("status"),
                    "output_digest": receipt.get("output_digest"),
                }
                for receipt in matching
            ],
        }
    return {
        "id": criterion["id"],
        "description": criterion["description"],
        "requires": requires,
        "status": "pass" if passed else "fail",
        "evidence": evidence,
    }


def evaluate_batch(
    *,
    bundle: dict[str, Any],
    manifest: dict[str, Any],
    repo_root: Path,
) -> tuple[dict[str, Any], int]:
    verification = verify_bundle(
        bundle=bundle,
        repo_root=repo_root,
        policy=load_policy(),
        schema=load_schema(),
    )
    raw_receipts = bundle.get("receipts", [])
    receipts = [item for item in raw_receipts if isinstance(item, dict)]
    issues: list[dict[str, Any]] = []
    for issue in manifest["issues"]:
        criteria = [
            _evaluate_criterion(
                criterion,
                bundle_outcome=verification.outcome,
                receipts=receipts,
            )
            for criterion in issue["criteria"]
        ]
        issues.append(
            {
                "number": issue["number"],
                "status": (
                    "ready"
                    if all(item["status"] == "pass" for item in criteria)
                    else "not_ready"
                ),
                "criteria": criteria,
            }
        )
    ready_count = sum(issue["status"] == "ready" for issue in issues)
    report = {
        "schema_version": 1,
        "batch_id": manifest["batch_id"],
        "generated_at": datetime.now(UTC).isoformat(),
        "source": {
            "head_sha": bundle.get("source", {}).get("head_sha"),
            "bundle_digest": bundle.get("bundle_digest"),
            "proof_run_id": bundle.get("run_id"),
            "ci_run_id": bundle.get("repository", {}).get("ci_run_id"),
        },
        "verification": verification.to_dict(),
        "execution": {
            "evidence_producer_runs": 0,
            "issues_evaluated": len(issues),
            "ready_count": ready_count,
            "not_ready_count": len(issues) - ready_count,
        },
        "status": "ready" if ready_count == len(issues) else "not_ready",
        "issues": issues,
    }
    return report, 0 if report["status"] == "ready" else 2


def main(argv: list[str] | None = None) -> int:
    parsed = _parser().parse_args(argv)
    try:
        repo_root = parsed.repo_root.expanduser().resolve()
        output = _safe_output(parsed.output, repo_root)
        bundle = _read_object(parsed.bundle, label="bundle")
        manifest = _read_object(parsed.manifest, label="manifest")
        manifest_schema = _read_object(parsed.manifest_schema, label="manifest schema")
        _validate_manifest(manifest, manifest_schema)
        report, exit_code = evaluate_batch(
            bundle=bundle,
            manifest=manifest,
            repo_root=repo_root,
        )
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        return 2
    print(
        json.dumps(
            {
                "status": report["status"],
                "output": str(output),
                "issues_evaluated": report["execution"]["issues_evaluated"],
                "evidence_producer_runs": 0,
            },
            sort_keys=True,
        )
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
