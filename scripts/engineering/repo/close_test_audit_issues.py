#!/usr/bin/env python3
"""Close TEST-AUDIT issues #5925-#5931 with completion evidence."""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO = "SatoryKono/BioactivityDataAcquisition"
ISSUES = {
    5925: "TEST-AUDIT-013: CI architecture governance cache via .github/actions/architecture-governance-cache",
    5926: "TEST-AUDIT-014: Renamed duplicate Batch lifecycle event tests in test_batch_internal_modules.py",
    5927: "TEST-AUDIT-015: Expanded integration determinism matrix (chembl/assay, composite, pubchem idempotency)",
    5928: "TEST-AUDIT-016: Coverage tail addenda for checkpoint_support and health_check_policy",
    5929: "TEST-AUDIT-017: Composite/checkpoint observability emission integration tests",
    5930: "TEST-AUDIT-018: e2e_smoke marker + test_matrix e2e-smoke/e2e-nightly-full lanes",
    5931: "TEST-AUDIT-019: Closeout retention audit 2026-07-03 + triage linked_issue refresh",
}


def _load_token() -> str:
    root = Path(__file__).resolve().parents[3]
    env_path = root / ".env"
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            if key.strip() == "GITHUB_TOKEN" and value.strip():
                return value.strip().strip('"').strip("'")
    token = os.getenv("GITHUB_TOKEN", "").strip()
    if token:
        return token
    raise SystemExit("GITHUB_TOKEN missing")


def _request(method: str, url: str, token: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(
        url,
        data=data,
        headers={
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github+json",
            "Content-Type": "application/json",
        },
        method=method,
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        raw = response.read().decode("utf-8")
    return {} if not raw else json.loads(raw)


def main() -> int:
    token = _load_token()
    for number, summary in ISSUES.items():
        comment = (
            f"Closed after implementing acceptance criteria on `main`.\n\n"
            f"- {summary}\n"
            f"- Evidence pack: `.github/ISSUES/TEST-AUDIT-2026-07-03-ISSUE-PACK.md`\n"
            f"- Publish report: `reports/quality/test-audit-issue-publish.json`"
        )
        issue_url = f"https://api.github.com/repos/{REPO}/issues/{number}"
        try:
            _request(
                "POST",
                f"{issue_url}/comments",
                token,
                {"body": comment},
            )
            _request("PATCH", issue_url, token, {"state": "closed"})
            print(f"Closed #{number}")
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            print(f"Failed #{number}: {exc.code} {detail}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
