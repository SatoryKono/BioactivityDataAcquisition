"""Publication rejects mismatched provenance before making any GitHub write."""

from __future__ import annotations

import base64
import gzip
import hashlib
import json
from pathlib import Path

import pytest
import yaml

from scripts.engineering.ci import publish_scorecard_sarif as publisher

pytestmark = pytest.mark.unit


@pytest.fixture
def publication(tmp_path, monkeypatch):
    sha = "a" * 40
    workflow = "11111111-2222-3333-4444-555555555555"
    environment = {
        "CIRCLECI": "true",
        "CIRCLE_BRANCH": "main",
        "CIRCLE_SHA1": sha,
        "CIRCLE_PROJECT_USERNAME": "SatoryKono",
        "CIRCLE_PROJECT_REPONAME": "BioactivityDataAcquisition",
        "CIRCLE_WORKFLOW_ID": workflow,
        "SARIF_GITHUB_TOKEN": "test-not-a-real-token",
    }
    sarif = {
        "version": "2.1.0",
        "runs": [
            {
                "tool": {"driver": {"name": "Scorecard", "semanticVersion": "v5.5.0"}},
                "versionControlProvenance": [
                    {
                        "repositoryUri": "https://github.com/" + publisher.REPOSITORY,
                        "revisionId": sha,
                        "branch": "main",
                    }
                ],
                "results": [],
            }
        ],
    }
    for name, value in (("results.json", {}), ("results.sarif", sarif)):
        (tmp_path / name).write_text(json.dumps(value), encoding="utf-8")
    identity = {
        "source_sha": sha,
        "workflow_id": workflow,
        "job_number": "123",
        "check_count": 18,
        "sarif_uploaded": False,
        "public_results_published": False,
        "sha256": {
            name: hashlib.sha256((tmp_path / name).read_bytes()).hexdigest()
            for name in ("results.json", "results.sarif")
        },
    }
    (tmp_path / "identity.json").write_text(json.dumps(identity), encoding="utf-8")
    jobs = [
        {"name": "scorecard-analysis", "status": "success", "job_number": 123},
        {
            "name": "scorecard-publish-approval",
            "status": "success",
            "type": "approval",
            "approved_by": "real-server-actor",
        },
    ]
    calls = []
    status = {"processing_status": "complete"}

    def request(url, token=None, payload=None):
        calls.append((url, token, payload))
        if url.endswith("/job"):
            assert token is None
            return {"items": jobs}
        assert token == environment["SARIF_GITHUB_TOKEN"]
        if url.endswith("/git/ref/heads/main"):
            return {"object": {"sha": sha}}
        if payload:
            return {"id": workflow}
        return status

    monkeypatch.setattr(publisher, "_request", request)
    monkeypatch.setattr(publisher.subprocess, "check_output", lambda *a, **kw: sha)
    monkeypatch.setattr(publisher.time, "sleep", lambda seconds: None)
    return tmp_path, environment, identity, jobs, calls, status


def test_verified_report_upload_preserves_exact_bytes_and_records_completion(
    publication,
):
    path, environment, _, _, calls, _ = publication
    output = path / "receipt.json"
    result = publisher.publish(path, output, environment)
    uploads = [payload for _, _, payload in calls if payload]
    assert len(uploads) == 1
    assert (
        gzip.decompress(base64.b64decode(uploads[0]["sarif"]))
        == (path / "results.sarif").read_bytes()
    )
    assert uploads[0]["commit_sha"] == environment["CIRCLE_SHA1"]
    assert uploads[0]["ref"] == "refs/heads/main"
    assert json.loads(output.read_text()) == result
    assert result["processing_status"] == "complete"
    assert result["public_results_published"] is False
    assert environment["SARIF_GITHUB_TOKEN"] not in output.read_text()


@pytest.mark.parametrize(
    "field,value",
    [
        ("CIRCLECI", "false"),
        ("CIRCLE_BRANCH", "feature"),
        ("CIRCLE_SHA1", "b" * 40),
        ("CIRCLE_PROJECT_REPONAME", "foreign"),
        ("CIRCLE_WORKFLOW_ID", "66666666-2222-3333-4444-555555555555"),
        ("SARIF_GITHUB_TOKEN", ""),
    ],
)
def test_foreign_environment_never_uploads(publication, field, value):
    path, environment, _, _, calls, _ = publication
    environment[field] = value
    with pytest.raises(ValueError):
        publisher.publish(path, path / "receipt.json", environment)
    assert not any(payload for _, _, payload in calls)


@pytest.mark.parametrize(
    "change", ["digest", "approval", "producer", "job-number", "missing"]
)
def test_untrusted_producer_never_uploads(publication, change):
    path, environment, _, jobs, calls, _ = publication
    if change == "digest":
        (path / "results.sarif").write_text("{}")
    elif change == "approval":
        jobs[1]["approved_by"] = None
    elif change == "producer":
        jobs[0]["status"] = "failed"
    elif change == "job-number":
        jobs[0]["job_number"] = 999
    else:
        jobs.pop()
    with pytest.raises(ValueError):
        publisher.publish(path, path / "receipt.json", environment)
    assert not any(payload for _, _, payload in calls)


@pytest.mark.parametrize("status", ["failed", "pending", "unknown"])
def test_ingestion_failure_or_timeout_is_not_success(publication, status):
    path, environment, _, _, calls, response = publication
    response["processing_status"] = status
    output = path / "receipt.json"
    with pytest.raises((ValueError, TimeoutError)):
        publisher.publish(path, output, environment)
    assert len([payload for _, _, payload in calls if payload]) == 1
    assert json.loads(output.read_text())["processing_status"] == status


def test_main_advance_prevents_publication(publication, monkeypatch):
    path, environment, _, _, calls, _ = publication
    original = publisher._request

    def advance(url, token=None, payload=None):
        if url.endswith("/git/ref/heads/main"):
            return {"object": {"sha": "b" * 40}}
        return original(url, token, payload)

    monkeypatch.setattr(publisher, "_request", advance)
    with pytest.raises(ValueError, match="Main changed"):
        publisher.publish(path, path / "receipt.json", environment)
    assert not any(payload for _, _, payload in calls)


def test_writer_is_main_only_and_requires_approved_read_only_analysis():
    root = next(
        path
        for path in Path(__file__).resolve().parents
        if (path / ".circleci/config.yml").is_file()
    )
    config = yaml.safe_load((root / ".circleci/config.yml").read_text(encoding="utf-8"))
    workflow = config["workflows"]["scorecard-publish"]
    assert {"equal": ["main", "<< pipeline.git.branch >>"]} in workflow["when"]["and"]
    jobs = {name: value for entry in workflow["jobs"] for name, value in entry.items()}
    assert jobs["scorecard-analysis"]["context"] == "bioetl-github-read-only"
    assert jobs["scorecard-publish-approval"] == {
        "type": "approval",
        "requires": ["scorecard-analysis"],
    }
    assert jobs["scorecard-publish"]["context"] == "bioetl-security-events-write"
    assert jobs["scorecard-publish"]["requires"] == ["scorecard-publish-approval"]
    assert jobs["scorecard-publish"]["serial-group"].endswith("/scorecard-publication")
