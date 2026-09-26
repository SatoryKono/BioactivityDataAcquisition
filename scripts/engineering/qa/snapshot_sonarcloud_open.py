"""Export a live SonarCloud OPEN-issue snapshot without printing tokens."""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import urllib.error
import urllib.parse
import urllib.request
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

PROJECT_KEY = "SatoryKono_BioactivityDataAcquisition"
DEFAULT_HOST = "https://sonarcloud.io"
DEFAULT_ORG = "satorykono"
MEASURE_KEYS = (
    "bugs,vulnerabilities,code_smells,alert_status,security_rating,"
    "reliability_rating,sqale_index,ncloc,security_hotspots,new_violations,"
    "security_issues,reliability_issues,maintainability_issues"
)


def _load_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        raw = line.strip()
        if not raw or raw.startswith("#") or "=" not in raw:
            continue
        key, value = raw.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")
    return values


def _opener(host: str, token: str) -> urllib.request.OpenerDirector:
    auth = urllib.request.HTTPPasswordMgrWithDefaultRealm()
    auth.add_password(None, host, token, "")
    return urllib.request.build_opener(urllib.request.HTTPBasicAuthHandler(auth))


def _get(
    opener: urllib.request.OpenerDirector, host: str, path: str, params: dict[str, str]
) -> dict[str, Any]:
    url = f"{host}{path}?{urllib.parse.urlencode(params)}"
    with opener.open(url, timeout=60) as response:
        payload = json.load(response)
    if not isinstance(payload, dict):
        raise RuntimeError(f"{path} did not return a JSON object")
    return payload


def _rating_letter(value: str | None) -> str:
    mapping = {"1.0": "A", "2.0": "B", "3.0": "C", "4.0": "D", "5.0": "E"}
    return mapping.get(str(value or ""), str(value or ""))


def _normalize_issue(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "key": item.get("key"),
        "rule": item.get("rule"),
        "severity": item.get("severity"),
        "type": item.get("type"),
        "status": item.get("status"),
        "resolution": item.get("resolution"),
        "message": item.get("message"),
        "component": item.get("component"),
        "path": str(item.get("component") or "").split(":", 1)[-1],
        "line": item.get("line"),
        "effort": item.get("effort"),
        "creationDate": item.get("creationDate"),
        "updateDate": item.get("updateDate"),
    }


def _count_by(issues: list[dict[str, Any]], field: str) -> dict[str, int]:
    counts: dict[str, int] = {}
    for item in issues:
        key = str(item.get(field) or "UNKNOWN")
        counts[key] = counts.get(key, 0) + 1
    return counts


def _origin_main_sha(repo_root: Path) -> str:
    git_dir = repo_root / ".git"
    if not git_dir.exists() and not git_dir.is_file():
        return ""
    completed = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "origin/main"],
        check=False,
        capture_output=True,
        text=True,
    )
    return completed.stdout.strip()


def _acceptance(
    *,
    open_total: int,
    measures: dict[str, Any],
    qg_status: str,
    revision: str,
    origin_main: str,
    resolved_false_total: int,
) -> dict[str, bool]:
    return {
        "open_zero": open_total == 0,
        "bugs_zero": str(measures.get("bugs") or "0") == "0",
        "vulnerabilities_zero": str(measures.get("vulnerabilities") or "0") == "0",
        "code_smells_zero": str(measures.get("code_smells") or "0") == "0",
        "quality_gate_ok": qg_status == "OK",
        "security_rating_a": _rating_letter(measures.get("security_rating")) == "A",
        "reliability_rating_a": _rating_letter(measures.get("reliability_rating"))
        == "A",
        "revision_matches_origin_main": bool(revision)
        and origin_main.startswith(revision[:12]),
        "no_indexing_discrepancy": open_total == resolved_false_total,
    }


def snapshot(*, repo_root: Path) -> dict[str, Any]:
    env = {**_load_dotenv(repo_root / ".env"), **os.environ}
    token = (
        env.get("SONARQUBE_TOKEN")
        or env.get("SONAR_LOGIN")
        or env.get("SONAR_TOKEN")
        or ""
    ).strip()
    if not token:
        raise SystemExit("Sonar token missing from environment / .env")
    host = (env.get("SONAR_HOST_URL") or DEFAULT_HOST).rstrip("/")
    org = env.get("SONARQUBE_ORG") or DEFAULT_ORG
    opener = _opener(host, token)
    open_issues = _get(
        opener,
        host,
        "/api/issues/search",
        {
            "componentKeys": PROJECT_KEY,
            "organization": org,
            "statuses": "OPEN",
            "ps": "500",
            "p": "1",
            "additionalFields": "_all",
        },
    )
    resolved_false = _get(
        opener,
        host,
        "/api/issues/search",
        {
            "componentKeys": PROJECT_KEY,
            "organization": org,
            "resolved": "false",
            "ps": "1",
        },
    )
    measures_payload = _get(
        opener,
        host,
        "/api/measures/component",
        {"component": PROJECT_KEY, "metricKeys": MEASURE_KEYS},
    )
    quality_gate = _get(
        opener,
        host,
        "/api/qualitygates/project_status",
        {"projectKey": PROJECT_KEY},
    )
    analyses = _get(
        opener,
        host,
        "/api/project_analyses/search",
        {"project": PROJECT_KEY, "ps": "3"},
    )
    issues = [
        _normalize_issue(item)
        for item in open_issues.get("issues") or []
        if isinstance(item, dict)
    ]
    measures = {
        item["metric"]: item.get("value")
        for item in (measures_payload.get("component") or {}).get("measures") or []
        if isinstance(item, dict) and "metric" in item
    }
    latest = (analyses.get("analyses") or [{}])[0]
    origin_main = _origin_main_sha(repo_root)
    revision = str(latest.get("revision") or "")
    open_total = int(open_issues.get("total") or len(issues))
    resolved_false_total = int(resolved_false.get("total") or 0)
    qg_status = str((quality_gate.get("projectStatus") or {}).get("status") or "")
    return {
        "schema_version": 2,
        "exported_at": datetime.now(tz=UTC).isoformat(),
        "host": host,
        "project": PROJECT_KEY,
        "organization": org,
        "accounting_query": "statuses=OPEN",
        "analysis_date": latest.get("date"),
        "revision": revision,
        "origin_main_sha": origin_main,
        "revision_matches_origin_main": bool(revision)
        and revision.startswith(origin_main[:12]),
        "total": open_total,
        "unique_keys": len({item["key"] for item in issues}),
        "issues": issues,
        "measures": measures,
        "quality_gate_status": qg_status,
        "ratings": {
            "reliability": _rating_letter(measures.get("reliability_rating")),
            "security": _rating_letter(measures.get("security_rating")),
            "maintainability": _rating_letter(measures.get("sqale_rating")),
        },
        "by_type": _count_by(issues, "type"),
        "by_severity": _count_by(issues, "severity"),
        "by_rule": sorted(
            _count_by(issues, "rule").items(), key=lambda pair: (-pair[1], pair[0])
        ),
        "indexing": {
            "open_total": open_total,
            "resolved_false_total": resolved_false_total,
            "discrepancy": abs(open_total - resolved_false_total),
        },
        "acceptance": _acceptance(
            open_total=open_total,
            measures=measures,
            qg_status=qg_status,
            revision=revision,
            origin_main=origin_main,
            resolved_false_total=resolved_false_total,
        ),
        "baseline_compare": {
            "baseline_open": 308,
            "baseline_paths": 152,
            "baseline_effort_hours": 64.6,
            "net_open": open_total - 308,
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--label", default="snr-rf-009-live-closeout")
    args = parser.parse_args()
    repo_root = args.repo_root.resolve()
    try:
        payload = snapshot(repo_root=repo_root)
    except urllib.error.HTTPError as exc:
        raise SystemExit(f"Sonar HTTP {exc.code}") from exc
    print(
        json.dumps(
            {
                "total": payload["total"],
                "quality_gate_status": payload["quality_gate_status"],
                "revision": payload["revision"],
                "origin_main_sha": payload["origin_main_sha"],
                "revision_matches_origin_main": payload["revision_matches_origin_main"],
                "acceptance": payload["acceptance"],
                "by_rule": payload["by_rule"],
                "issues": [
                    {
                        "rule": item["rule"],
                        "path": item["path"],
                        "line": item["line"],
                        "type": item["type"],
                        "severity": item["severity"],
                    }
                    for item in payload["issues"]
                ],
            },
            indent=2,
        )
    )
    if args.write:
        stamp = datetime.now(tz=UTC).strftime("%Y%m%d")
        out_dir = repo_root / "reports" / "quality" / "sonar"
        out_dir.mkdir(parents=True, exist_ok=True)
        full_path = out_dir / f"live-issues-{stamp}-rf009-full.json"
        summary_path = out_dir / f"live-snapshot-{stamp}-rf009-summary.json"
        full_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        summary = {key: value for key, value in payload.items() if key != "issues"}
        summary["label"] = args.label
        summary["reports"] = {
            "full": str(full_path.relative_to(repo_root).as_posix()),
            "summary": str(summary_path.relative_to(repo_root).as_posix()),
        }
        summary_path.write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
        print(f"wrote {full_path.relative_to(repo_root)}")
        print(f"wrote {summary_path.relative_to(repo_root)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
