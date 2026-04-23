#!/usr/bin/env python3
"""Build a reproducible Sonar baseline report for the BioETL repository."""

from __future__ import annotations

import argparse
import fnmatch
import json
import os
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Final

import requests
from dotenv import load_dotenv

load_dotenv()

DEFAULT_PROJECT_KEY: Final[str] = os.getenv(
    "SONAR_PROJECT_KEY",
    "SatoryKono_BioactivityDataAcquisition",
)
DEFAULT_SONAR_URL: Final[str] = os.getenv("SONARQUBE_URL", "https://sonarcloud.io")
DEFAULT_ORGANIZATION: Final[str | None] = os.getenv("SONARQUBE_ORG")
DEFAULT_TOKEN_ENV_VAR: Final[str] = "SONARQUBE_TOKEN"
DEFAULT_CONFIG_PATH: Final[Path] = Path("sonar-project.properties")
DEFAULT_OUTPUT_PATH: Final[Path] = Path("reports/quality/sonar_baseline_report.json")
DEFAULT_TOP_BUCKET_DEPTH: Final[int] = 4
DEFAULT_TOP_BUCKET_LIMIT: Final[int] = 20


def _normalize_url(url: str) -> str:
    return url.rstrip("/")


def _commit_property(
    properties: dict[str, str],
    *,
    key: str,
    value_parts: list[str],
) -> None:
    """Store one parsed property assembled from one or more logical lines."""
    properties[key] = "".join(value_parts)


def _parse_property_assignment(raw_line: str) -> tuple[str, str, bool] | None:
    """Return the parsed property assignment for one raw line."""
    if "=" not in raw_line:
        return None
    key, value = raw_line.split("=", 1)
    normalized_value = value.strip()
    continued = normalized_value.endswith("\\")
    value_part = normalized_value[:-1] if continued else normalized_value
    return key.strip(), value_part, continued


def _consume_continued_property(
    stripped_line: str,
    *,
    properties: dict[str, str],
    current_key: str,
    current_value_parts: list[str],
) -> str | None:
    """Consume one continuation line and return the next active property key."""
    continued = stripped_line.endswith("\\")
    value_part = stripped_line[:-1] if continued else stripped_line
    current_value_parts.append(value_part)
    if continued:
        return current_key
    _commit_property(properties, key=current_key, value_parts=current_value_parts)
    return None


def parse_java_properties(text: str) -> dict[str, str]:
    """Parse a Java-style properties file with line continuations."""
    properties: dict[str, str] = {}
    current_key: str | None = None
    current_value_parts: list[str] = []

    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("#"):
            continue

        if current_key is not None:
            current_key = _consume_continued_property(
                stripped,
                properties=properties,
                current_key=current_key,
                current_value_parts=current_value_parts,
            )
            if current_key is not None:
                continue
            current_value_parts = []
            continue

        assignment = _parse_property_assignment(raw_line)
        if assignment is None:
            continue
        key, value_part, continued = assignment
        if continued:
            current_key = key
            current_value_parts = [value_part]
            continue
        properties[key] = value_part

    if current_key is not None:
        _commit_property(properties, key=current_key, value_parts=current_value_parts)

    return properties


def parse_exclusions(raw_value: str) -> list[str]:
    """Split sonar.exclusions into normalized file paths."""
    entries: list[str] = []
    for item in raw_value.split(","):
        normalized = item.strip()
        if normalized:
            entries.append(normalized)
    return entries


def parse_sources(raw_value: str) -> list[str]:
    """Split sonar.sources into normalized path roots."""
    sources: list[str] = []
    for item in raw_value.split(","):
        normalized = item.strip().rstrip("/")
        if normalized:
            sources.append(normalized)
    return sources


def bucket_exclusions(
    exclusions: list[str],
    *,
    top_depth: int = DEFAULT_TOP_BUCKET_DEPTH,
) -> list[dict[str, Any]]:
    """Group exclusions by directory family to expose hotspot buckets."""
    counts: Counter[str] = Counter()
    for item in exclusions:
        parts = item.split("/")
        bucket = "/".join(parts[:top_depth]) if len(parts) >= top_depth else item
        counts[bucket] += 1
    return [
        {"path_prefix": path_prefix, "count": count}
        for path_prefix, count in counts.most_common()
    ]


def load_quarantine_from_properties(config_path: Path) -> dict[str, Any]:
    """Load the current Sonar quarantine surface from sonar-project.properties."""
    properties = parse_java_properties(config_path.read_text(encoding="utf-8"))
    exclusions = parse_exclusions(properties.get("sonar.exclusions", ""))
    buckets = bucket_exclusions(exclusions)

    return {
        "config_path": str(config_path),
        "project_key": properties.get("sonar.projectKey", DEFAULT_PROJECT_KEY),
        "organization": properties.get("sonar.organization", DEFAULT_ORGANIZATION),
        "sources": properties.get("sonar.sources", ""),
        "entry_count": len(exclusions),
        "entries": exclusions,
        "buckets": buckets,
    }


def _facet_counts(payload: dict[str, Any], facet_key: str) -> dict[str, int]:
    for facet in payload.get("facets", []):
        if facet.get("property") == facet_key:
            return {
                str(value["val"]): int(value["count"])
                for value in facet.get("values", [])
            }
    return {}


def _issue_path(issue: dict[str, Any]) -> str:
    component = str(issue.get("component", ""))
    if ":" in component:
        return component.split(":", 1)[1]
    return component


def _is_in_supported_scope(path: str, supported_sources: list[str]) -> bool:
    normalized = path.rstrip("/")
    for source in supported_sources:
        if normalized == source or normalized.startswith(f"{source}/"):
            return True
    return False


def _matches_current_quarantine(path: str, exclusion_patterns: list[str]) -> bool:
    normalized = path.strip().lstrip("./").rstrip("/")
    for pattern in exclusion_patterns:
        normalized_pattern = pattern.strip().lstrip("./").rstrip("/")
        if not normalized_pattern:
            continue
        if any(token in normalized_pattern for token in "*?[]"):
            if fnmatch.fnmatchcase(normalized, normalized_pattern):
                return True
            continue
        if normalized == normalized_pattern or normalized.startswith(
            f"{normalized_pattern}/"
        ):
            return True
    return False


def fetch_live_issue_summary(
    *,
    sonar_url: str,
    project_key: str,
    token: str | None,
    supported_sources: list[str],
    quarantine_patterns: list[str],
) -> dict[str, Any]:
    """Fetch a compact unresolved-issues summary from SonarCloud/SonarQube."""
    if not token:
        return {
            "status": "skipped",
            "reason": "missing_token",
        }

    response: requests.Response
    try:
        response = requests.get(
            f"{_normalize_url(sonar_url)}/api/issues/search",
            params={
                "componentKeys": project_key,
                "resolved": "false",
                "ps": 100,
                "facets": "severities,types",
            },
            auth=(token, ""),
            timeout=30,
        )
    except requests.RequestException as exc:
        return {
            "status": "error",
            "reason": "request_failed",
            "message": str(exc),
        }

    if response.status_code != 200:
        return {
            "status": "error",
            "reason": "http_error",
            "status_code": response.status_code,
            "message": response.text[:300],
        }

    payload = response.json()
    paging = payload.get("paging", {})
    issues = payload.get("issues", [])
    rendered_issues: list[dict[str, Any]] = []
    supported_scope_total = 0
    supported_non_quarantined_total = 0
    supported_quarantined_total = 0
    out_of_scope_total = 0
    for issue in issues:
        path = _issue_path(issue)
        in_supported_scope = _is_in_supported_scope(path, supported_sources)
        matches_current_quarantine = _matches_current_quarantine(
            path, quarantine_patterns
        )
        if in_supported_scope:
            supported_scope_total += 1
            if matches_current_quarantine:
                supported_quarantined_total += 1
            else:
                supported_non_quarantined_total += 1
        else:
            out_of_scope_total += 1
        rendered_issues.append(
            {
                "key": issue.get("key"),
                "path": path,
                "rule": issue.get("rule"),
                "severity": issue.get("severity"),
                "message": issue.get("message"),
                "line": issue.get("line"),
                "in_supported_scope": in_supported_scope,
                "matches_current_quarantine": matches_current_quarantine,
            }
        )
    return {
        "status": "ok",
        "total": int(paging.get("total", 0)),
        "page_size": int(paging.get("pageSize", 0) or 0),
        "severity_counts": _facet_counts(payload, "severities"),
        "type_counts": _facet_counts(payload, "types"),
        "supported_scope_total": supported_scope_total,
        "supported_non_quarantined_total": supported_non_quarantined_total,
        "supported_quarantined_total": supported_quarantined_total,
        "out_of_scope_total": out_of_scope_total,
        "issues": rendered_issues,
    }


def build_baseline_report(
    *,
    config_path: Path,
    sonar_url: str,
    token: str | None,
    bucket_limit: int = DEFAULT_TOP_BUCKET_LIMIT,
) -> dict[str, Any]:
    """Build a report combining repo-backed quarantine and live Sonar status."""
    quarantine = load_quarantine_from_properties(config_path)
    supported_sources = parse_sources(quarantine["sources"])
    live = fetch_live_issue_summary(
        sonar_url=sonar_url,
        project_key=quarantine["project_key"],
        token=token,
        supported_sources=supported_sources,
        quarantine_patterns=quarantine["entries"],
    )
    top_buckets = quarantine["buckets"][:bucket_limit]

    assessment: dict[str, Any] = {
        "historical_near_zero_status_is_stale": quarantine["entry_count"] > 0,
        "quarantine_entry_count": quarantine["entry_count"],
        "top_quarantine_buckets": top_buckets,
    }
    if live["status"] != "ok":
        assessment["live_measurement_ready"] = False
        assessment["live_measurement_blocker"] = live.get("reason", "unknown")
    else:
        assessment["live_measurement_ready"] = True
        assessment["live_unresolved_issue_count"] = live["total"]
        assessment["live_scope_drift_detected"] = live["out_of_scope_total"] > 0
        assessment["live_supported_scope_issue_count"] = live["supported_scope_total"]
        assessment["live_supported_non_quarantined_issue_count"] = live[
            "supported_non_quarantined_total"
        ]
        assessment["live_supported_quarantined_issue_count"] = live[
            "supported_quarantined_total"
        ]
        assessment["live_quarantine_drift_detected"] = (
            live["supported_quarantined_total"] > 0
        )
        assessment["live_out_of_scope_issue_count"] = live["out_of_scope_total"]
        assessment["live_authoritative_scope_ready"] = (
            not assessment["live_scope_drift_detected"]
            and not assessment["live_quarantine_drift_detected"]
        )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "project": {
            "project_key": quarantine["project_key"],
            "organization": quarantine["organization"],
            "sonar_url": _normalize_url(sonar_url),
            "sources": quarantine["sources"],
        },
        "quarantine": {
            "config_path": quarantine["config_path"],
            "entry_count": quarantine["entry_count"],
            "entries": quarantine["entries"],
            "buckets": quarantine["buckets"],
            "top_buckets": top_buckets,
        },
        "live_issues": live,
        "assessment": assessment,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build a reproducible Sonar baseline report for BioETL.",
    )
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to sonar-project.properties.",
    )
    parser.add_argument(
        "--sonar-url",
        default=DEFAULT_SONAR_URL,
        help="SonarQube / SonarCloud base URL.",
    )
    parser.add_argument(
        "--token-env-var",
        default=DEFAULT_TOKEN_ENV_VAR,
        help="Environment variable that stores the Sonar token.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_PATH,
        help="Output path for the JSON baseline report.",
    )
    parser.add_argument(
        "--write",
        action="store_true",
        help="Write the report to --output in addition to printing it.",
    )
    parser.add_argument(
        "--bucket-limit",
        type=int,
        default=DEFAULT_TOP_BUCKET_LIMIT,
        help="Number of top quarantine buckets to include in the report.",
    )
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    token = os.getenv(args.token_env_var)
    report = build_baseline_report(
        config_path=args.config,
        sonar_url=args.sonar_url,
        token=token,
        bucket_limit=args.bucket_limit,
    )

    payload = json.dumps(report, indent=2, sort_keys=True)
    print(payload)

    if args.write:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
