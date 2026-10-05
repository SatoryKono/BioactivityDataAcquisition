"""Fail-closed publication guards, executed without credentials or network writes."""

from __future__ import annotations

import base64
import hashlib
import io
import json
from pathlib import Path
import re

import pytest
import yaml

pytestmark = pytest.mark.unit

ROOT = next(
    path
    for path in Path(__file__).resolve().parents
    if (path / ".circleci/config.yml").is_file()
)
SHA = "a" * 40
IMAGE_ID = "sha256:" + "b" * 64
DIGEST = "sha256:" + "c" * 64
REQUIRED = {
    "bioetl-image-id.txt",
    "bioetl-image-provenance.txt",
    "bioetl-pip-freeze.txt",
    "bioetl.spdx.json",
    "docker-build-metadata.json",
    "github-trivy-alerts.json",
    "trivy-alerts.csv",
    "trivy-base-results.json",
    "trivy-fixability-audit.json",
    "trivy-results.json",
    "trivy-results.sarif",
    "trivy-version.json",
}


def _write(path, value):
    Path(path).write_text(json.dumps(value), encoding="utf-8")


@pytest.fixture
def guard(tmp_path, monkeypatch):
    source = (ROOT / "scripts/engineering/ci/publish_docker_image.sh").read_text(
        encoding="utf-8"
    )
    blocks = dict(re.findall(r"python3 - <<'([A-Z]+)'\n(.*?)^\1$", source, re.M | re.S))
    monkeypatch.chdir(tmp_path)
    for key, value in {
        "CIRCLE_SHA1": SHA,
        "CIRCLE_WORKFLOW_ID": "workflow-proof",
        "IMAGE_DIGEST": DIGEST,
    }.items():
        monkeypatch.setenv(key, value)

    def execute(name, response=None):
        monkeypatch.setattr(
            "urllib.request.urlopen",
            lambda *args, **kwargs: io.BytesIO(json.dumps(response).encode()),
        )
        exec(compile(blocks[name], "publication-" + name, "exec"), {})

    return execute


@pytest.fixture
def manifest(guard):
    for name in REQUIRED | {"bioetl-scanned-image.tar.zst"}:
        Path(name).write_text("{}", encoding="utf-8")
    lines = [
        hashlib.sha256(Path(name).read_bytes()).hexdigest() + "  " + name
        for name in sorted(REQUIRED)
    ]
    Path("baseline.sha256").write_text("\n".join(lines) + "\n", encoding="utf-8")
    Path("scanned-image.sha256").write_text(
        "0" * 64 + "  bioetl-scanned-image.tar.zst\n", encoding="utf-8"
    )
    return lines


def test_complete_manifest_is_accepted(guard, manifest):
    guard("MANIFEST")


@pytest.mark.parametrize(
    "corruption", ["missing", "duplicate", "traversal", "absent-file"]
)
def test_incomplete_or_unsafe_manifest_is_rejected(guard, manifest, corruption):
    if corruption == "missing":
        manifest.pop()
    elif corruption == "duplicate":
        manifest.append(manifest[0])
    elif corruption == "traversal":
        manifest[0] = manifest[0].replace("  ", "  ../")
    else:
        Path("bioetl-image-id.txt").unlink()
    Path("baseline.sha256").write_text("\n".join(manifest) + "\n", encoding="utf-8")
    with pytest.raises(AssertionError):
        guard("MANIFEST")


@pytest.fixture
def metadata(guard):
    value = {
        "producer": "circleci",
        "source_sha": SHA,
        "run_attempt": "workflow-proof",
        "image_ref": "bioetl:" + SHA,
        "run_id": "123",
        "image_id": IMAGE_ID,
    }
    _write("docker-build-metadata.json", value)
    Path("bioetl-image-id.txt").write_text(IMAGE_ID + "\n", encoding="utf-8")
    _write(
        "trivy-results.json",
        {
            "Metadata": {"ImageID": IMAGE_ID},
            "Results": [{"Target": "probe", "Vulnerabilities": []}],
        },
    )
    return value


def test_matching_clean_producer_is_accepted(guard, metadata):
    guard("VERIFY")


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("source_sha", "d" * 40),
        ("run_attempt", "foreign"),
        ("image_ref", "bioetl:foreign"),
        ("producer", "local"),
    ],
)
def test_foreign_provenance_is_rejected(guard, metadata, field, value):
    _write("docker-build-metadata.json", dict(metadata, **{field: value}))
    with pytest.raises(AssertionError):
        guard("VERIFY")


@pytest.mark.parametrize("corruption", ["image", "vulnerability", "empty"])
def test_scan_substitution_and_blocking_findings_are_rejected(
    guard, metadata, corruption
):
    scan = json.loads(Path("trivy-results.json").read_text())
    if corruption == "image":
        scan["Metadata"]["ImageID"] = "sha256:" + "d" * 64
    elif corruption == "empty":
        scan["Results"] = []
    else:
        scan["Results"][0]["Vulnerabilities"] = [
            {
                "VulnerabilityID": "CVE-2099-0001",
                "PkgName": "probe",
                "InstalledVersion": "1",
                "FixedVersion": "2",
                "Severity": "HIGH",
            }
        ]
    _write("trivy-results.json", scan)
    with pytest.raises((AssertionError, ValueError)):
        guard("VERIFY")


@pytest.mark.parametrize(
    "corruption", [None, "unapproved", "foreign-producer", "failed-producer"]
)
def test_server_approval_binds_successful_producer(guard, metadata, corruption):
    jobs = [
        {
            "name": "docker-publish-approval",
            "id": "approval-id",
            "status": "success",
            "approved_by": "human-id",
        },
        {"name": "docker-security-baseline", "status": "success", "job_number": 123},
    ]
    if corruption == "unapproved":
        jobs[0]["status"] = "on_hold"
    elif corruption == "foreign-producer":
        jobs[1]["job_number"] = 999
    elif corruption == "failed-producer":
        jobs[1]["status"] = "failed"
    if corruption:
        with pytest.raises(AssertionError):
            guard("APPROVAL", {"items": jobs})
    else:
        guard("APPROVAL", {"items": jobs})
        assert (
            json.loads(Path("approval.json").read_text())["producer_job_number"] == 123
        )


@pytest.mark.parametrize("current", [True, False])
def test_stale_main_is_rejected(guard, current):
    response = {"object": {"sha": SHA if current else "d" * 40}}
    if current:
        guard("CURRENT", response)
    else:
        with pytest.raises(SystemExit, match="no longer current main"):
            guard("CURRENT", response)


@pytest.mark.parametrize("same_image", [True, False])
def test_sha_tag_cannot_be_rebound(guard, metadata, same_image):
    _write(
        "existing-manifest.json",
        {"config": {"digest": IMAGE_ID if same_image else "sha256:" + "d" * 64}},
    )
    if same_image:
        guard("EXISTING")
    else:
        with pytest.raises(AssertionError, match="different image"):
            guard("EXISTING")


@pytest.mark.parametrize("corruption", [None, "predicate", "digest"])
def test_verified_attestations_bind_predicates_and_digest(guard, corruption):
    for output, source in [
        ("provenance-verification.json", "provenance.json"),
        ("sbom-verification.json", "bioetl.spdx.json"),
    ]:
        predicate = {"expected": source}
        _write(source, predicate)
        statement = {
            "subject": [{"digest": {"sha256": DIGEST.removeprefix("sha256:")}}],
            "predicate": predicate,
        }
        if corruption == "predicate":
            statement["predicate"] = {"wrong": True}
        elif corruption == "digest":
            statement["subject"][0]["digest"]["sha256"] = "d" * 64
        _write(
            output,
            {"payload": base64.b64encode(json.dumps(statement).encode()).decode()},
        )
    if corruption:
        with pytest.raises(AssertionError, match="No verified attestation"):
            guard("CLAIMS")
    else:
        guard("CLAIMS")


def test_publish_requires_main_security_approval_and_restricted_context():
    config = yaml.safe_load((ROOT / ".circleci/config.yml").read_text(encoding="utf-8"))
    lane = config["workflows"]["docker-publish"]
    assert {"equal": ["main", "<< pipeline.git.branch >>"]} in lane["when"]["and"]
    jobs = {name: args for row in lane["jobs"] for name, args in row.items()}
    assert jobs["docker-security-baseline"]["context"] == "bioetl-github-read-only"
    assert jobs["docker-publish-approval"] == {
        "type": "approval",
        "requires": ["docker-security-baseline"],
    }
    assert jobs["docker-publish"]["requires"] == ["docker-publish-approval"]
    assert jobs["docker-publish"]["context"] == "bioetl-ghcr-publish"
    assert jobs["docker-publish"]["serial-group"].endswith("/docker-publication")
