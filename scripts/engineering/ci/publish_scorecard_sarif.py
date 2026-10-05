"""Publish a same-workflow Scorecard report after explicit CircleCI approval."""

from __future__ import annotations

import argparse
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import time
import urllib.request

REPOSITORY = "SatoryKono/BioactivityDataAcquisition"
GITHUB_API = "https://api.github.com/repos/" + REPOSITORY


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _request(url: str, token: str | None = None, payload: dict | None = None):
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = "Bearer " + token
        headers["X-GitHub-Api-Version"] = "2022-11-28"
    data = None if payload is None else json.dumps(payload).encode()
    if data is not None:
        headers["Content-Type"] = "application/json"
    request = urllib.request.Request(url, data=data, headers=headers)
    with urllib.request.urlopen(request, timeout=30) as response:
        return json.load(response)


def validate_inputs(directory: Path, environment: dict[str, str]) -> tuple[dict, bytes]:
    """Reject foreign, incomplete or substituted producer artifacts before writing."""
    _require(environment.get("CIRCLECI") == "true", "CircleCI execution required")
    _require(environment.get("CIRCLE_BRANCH") == "main", "Main branch required")
    project = "/".join(
        environment.get(key, "")
        for key in ("CIRCLE_PROJECT_USERNAME", "CIRCLE_PROJECT_REPONAME")
    )
    _require(project == REPOSITORY, "Unexpected project")
    sha = environment.get("CIRCLE_SHA1", "")
    _require(re.fullmatch(r"[0-9a-f]{40}", sha) is not None, "Invalid source SHA")
    workflow = environment.get("CIRCLE_WORKFLOW_ID", "")
    _require(re.fullmatch(r"[0-9a-f-]{36}", workflow) is not None, "Invalid workflow")
    identity = json.loads((directory / "identity.json").read_text(encoding="utf-8"))
    _require(identity["source_sha"] == sha, "Foreign source SHA")
    _require(identity["workflow_id"] == workflow, "Foreign producer workflow")
    _require(str(identity["job_number"]).isdigit(), "Invalid producer job")
    _require(identity["check_count"] == 18, "Incomplete Scorecard check set")
    _require(identity["sarif_uploaded"] is False, "Report already marked uploaded")
    _require(
        identity["public_results_published"] is False, "Unexpected publication claim"
    )
    for name in ("results.json", "results.sarif"):
        path = directory / name
        _require(path.is_file() and not path.is_symlink(), "Missing or linked report")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        _require(identity["sha256"][name] == digest, "Report digest mismatch")
    raw = (directory / "results.sarif").read_bytes()
    sarif = json.loads(raw)
    _require(sarif["version"] == "2.1.0" and bool(sarif["runs"]), "Invalid SARIF")
    provenance = [
        {
            "repositoryUri": "https://github.com/" + REPOSITORY,
            "revisionId": sha,
            "branch": "main",
        }
    ]
    for run in sarif["runs"]:
        driver = run["tool"]["driver"]
        _require(driver["name"] == "Scorecard", "Unexpected analysis tool")
        _require(driver["semanticVersion"] == "v5.5.0", "Unexpected Scorecard version")
        _require(run["versionControlProvenance"] == provenance, "Foreign SARIF source")
    return identity, raw


def verify_workflow(identity: dict) -> None:
    """Read the public server state; authentication failures never bypass approval."""
    response = _request(
        "https://circleci.com/api/v2/workflow/" + identity["workflow_id"] + "/job"
    )
    jobs = response["items"]
    producers = [job for job in jobs if job["name"] == "scorecard-analysis"]
    approvals = [job for job in jobs if job["name"] == "scorecard-publish-approval"]
    _require(
        len(producers) == len(approvals) == 1, "Missing or ambiguous producer/approval"
    )
    producer, approval = producers[0], approvals[0]
    _require(producer["status"] == "success", "Producer did not succeed")
    _require(
        str(producer["job_number"]) == str(identity["job_number"]),
        "Foreign producer job",
    )
    _require(
        approval["type"] == "approval"
        and approval["status"] == "success"
        and bool(approval.get("approved_by")),
        "Publication not approved",
    )


def publish(directory: Path, output: Path, environment: dict[str, str]) -> dict:
    """Upload once, wait for GitHub ingestion, then persist a truthful receipt."""
    identity, raw = validate_inputs(directory, environment)
    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    _require(head == identity["source_sha"], "Checkout differs from producer")
    token = environment.get("SARIF_GITHUB_TOKEN", "")
    _require(bool(token), "Missing dedicated SARIF credential")
    verify_workflow(identity)
    main = _request(GITHUB_API + "/git/ref/heads/main", token)
    _require(main["object"]["sha"] == head, "Main changed before publication")
    compressed = gzip.compress(raw, mtime=0)
    _require(len(compressed) < 10_000_000, "SARIF exceeds upload limit")
    result = _request(
        GITHUB_API + "/code-scanning/sarifs",
        token,
        {
            "commit_sha": head,
            "ref": "refs/heads/main",
            "tool_name": "Scorecard",
            "sarif": base64.b64encode(compressed).decode(),
            "validate": True,
        },
    )
    upload_id = result["id"]
    _require(
        re.fullmatch(r"[0-9a-f-]{36}", upload_id) is not None, "Invalid upload identity"
    )
    receipt = {
        "source_sha": head,
        "workflow_id": identity["workflow_id"],
        "producer_job_number": identity["job_number"],
        "upload_id": upload_id,
        "sarif_sha256": hashlib.sha256(raw).hexdigest(),
        "sarif_uploaded": True,
        "processing_status": "pending",
        "public_results_published": False,
    }
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    for _ in range(60):
        status = _request(GITHUB_API + "/code-scanning/sarifs/" + upload_id, token)
        receipt["processing_status"] = status["processing_status"]
        receipt["errors"] = status.get("errors", [])
        output.write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
        _require(
            receipt["processing_status"] != "failed" and not receipt["errors"],
            "GitHub SARIF ingestion failed; inspect receipt",
        )
        if receipt["processing_status"] == "complete":
            return receipt
        _require(receipt["processing_status"] == "pending", "Unknown ingestion status")
        time.sleep(5)
    raise TimeoutError("GitHub SARIF ingestion did not finish; inspect receipt")


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    receipt = publish(args.directory, args.output, dict(os.environ))
    print(
        "Scorecard SARIF ingestion:", receipt["processing_status"], receipt["upload_id"]
    )


if __name__ == "__main__":
    main()
