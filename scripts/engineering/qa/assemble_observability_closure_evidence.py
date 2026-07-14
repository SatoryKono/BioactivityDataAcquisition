#!/usr/bin/env python3
"""Assemble one typed observability campaign evidence envelope.

The assembler does not manufacture observations. It hashes retained raw files,
checks their category-specific semantics, binds them to an executed campaign,
and writes the envelope accepted by the closure runner.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path

from scripts.engineering.qa import run_observability_closure_campaign as campaign


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--campaign-report", type=Path, required=True)
    parser.add_argument(
        "--category", choices=campaign.REQUIRED_EXTERNAL_EVIDENCE, required=True
    )
    parser.add_argument("--raw", action="append", default=[])
    parser.add_argument("--summary", action="append", default=[])
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--tool-version")
    return parser


def _pairs(items: list[str], *, option: str) -> dict[str, str]:
    result: dict[str, str] = {}
    for item in items:
        key, separator, value = item.partition("=")
        if not separator or not key.strip() or not value.strip():
            raise ValueError(f"{option} requires KEY=VALUE")
        if key in result:
            raise ValueError(f"{option} key {key!r} is duplicated")
        result[key] = value
    return result


def _load_report(path: Path) -> tuple[dict[str, object], Path]:
    resolved = path.expanduser().resolve()
    payload = json.loads(resolved.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("campaign report must be an object")
    if payload.get("status") != "awaiting_external_evidence":
        raise ValueError("campaign report must be awaiting external evidence")
    audit_root = resolved.parent
    if resolved != audit_root / "observability-closure-campaign.json":
        raise ValueError("campaign report must use the canonical audit-root path")
    if not isinstance(payload.get("campaign_binding"), dict):
        raise ValueError("campaign report has no occurrence binding")
    return payload, audit_root


def _raw_specs(items: list[str]) -> list[tuple[str, str]]:
    result: list[tuple[str, str]] = []
    for item in items:
        kind, separator, value = item.partition("=")
        if not separator or not kind.strip() or not value.strip():
            raise ValueError("--raw requires KIND=PATH")
        result.append((kind, value))
    return result


def _raw_artifacts(
    specs: list[tuple[str, str]], *, audit_root: Path
) -> list[dict[str, str]]:
    raw_root = (audit_root / "evidence" / "raw").resolve()
    artifacts: list[dict[str, str]] = []
    for kind, raw_path in specs:
        path = Path(raw_path).expanduser().resolve()
        if raw_root not in path.parents or not path.is_file():
            raise ValueError(
                "raw artifacts must be files below AUDIT_ROOT/evidence/raw"
            )
        artifacts.append(
            {
                "path": str(path),
                "kind": kind,
                "sha256": campaign._sha256_file(path),
            }
        )
    return artifacts


def _summary(category: str, pairs: dict[str, str]) -> dict[str, int]:
    required = campaign.EVIDENCE_SUMMARY_REQUIREMENTS[category]
    result: dict[str, int] = {}
    for key, value in pairs.items():
        try:
            result[key] = int(value)
        except ValueError as exc:
            raise ValueError(f"summary {key!r} must be an integer") from exc
    missing = set(required) - set(result)
    if missing:
        raise ValueError("missing summary fields: " + ", ".join(sorted(missing)))
    errors = campaign._validate_summary(category, result)
    if errors:
        raise ValueError("; ".join(errors))
    return result


def main(argv: list[str] | None = None) -> int:
    parsed = _parser().parse_args(argv)
    try:
        report, audit_root = _load_report(parsed.campaign_report)
        output = parsed.output.expanduser().resolve()
        expected_output = (
            audit_root / "evidence" / f"{parsed.category}.json"
        ).resolve()
        if output != expected_output:
            raise ValueError("output must be AUDIT_ROOT/evidence/CATEGORY.json")
        raw = _raw_artifacts(_raw_specs(parsed.raw), audit_root=audit_root)
        raw_errors, retained = campaign._validate_raw_artifacts(
            parsed.category,
            raw,
            raw_root=(audit_root / "evidence" / "raw").resolve(),
        )
        content_errors = campaign._validate_raw_content(
            parsed.category,
            retained,
            report["campaign_binding"],
        )
        errors = [*raw_errors, *content_errors]
        if errors:
            raise ValueError("; ".join(errors))
        summary = _summary(parsed.category, _pairs(parsed.summary, option="--summary"))
        command = [sys.executable, "-m", campaign.CANONICAL_EVIDENCE_ASSEMBLER]
        command.extend(sys.argv[1:] if argv is None else argv)
        producer: dict[str, object] = {"command": command, "exit_code": 0}
        if parsed.tool_version:
            producer["tool_version"] = parsed.tool_version
        payload = {
            "schema_version": 1,
            "evidence_type": parsed.category,
            "status": "pass",
            "source_revision": report["source_revision"],
            "campaign_binding": report["campaign_binding"],
            "generated_at": datetime.now(UTC).isoformat(),
            "summary": summary,
            "producer": producer,
            "assertions": [
                {
                    "name": "typed-raw-content",
                    "expected": [],
                    "actual": [],
                    "status": "pass",
                }
            ],
            "raw_artifacts": raw,
        }
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, sort_keys=True))
        return 2
    print(json.dumps({"status": "pass", "evidence": str(output)}, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
