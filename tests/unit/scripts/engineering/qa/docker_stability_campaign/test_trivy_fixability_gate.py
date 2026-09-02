from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.engineering.qa.docker_stability_campaign.trivy_baseline import (
    build_fixability_audit,
    is_strict_blocking_finding,
    main,
)

pytestmark = pytest.mark.unit


def _payload() -> dict[str, object]:
    return {
        "Results": [
            {
                "Target": "bioetl:test",
                "Vulnerabilities": [
                    {
                        "VulnerabilityID": "CVE-2026-0001",
                        "PkgName": "fixable-package",
                        "InstalledVersion": "1.0.0",
                        "FixedVersion": "1.0.1",
                        "Severity": "HIGH",
                        "Status": "affected",
                    },
                    {
                        "VulnerabilityID": "CVE-2026-0002",
                        "PkgName": "unfixed-package",
                        "InstalledVersion": "2.0.0",
                        "FixedVersion": "",
                        "Severity": "CRITICAL",
                        "Status": "affected",
                    },
                    {
                        "VulnerabilityID": "CVE-2026-0003",
                        "PkgName": "not-affected-package",
                        "InstalledVersion": "3.0.0",
                        "FixedVersion": "3.0.1",
                        "Severity": "MEDIUM",
                        "Status": "not_affected",
                    },
                    {
                        "VulnerabilityID": "CVE-2026-0004",
                        "PkgName": "low-package",
                        "InstalledVersion": "4.0.0",
                        "FixedVersion": "4.0.1",
                        "Severity": "LOW",
                        "Status": "affected",
                    },
                ],
            }
        ]
    }


def test_audit_keeps_all_findings_but_blocks_only_fixable_severity_findings() -> None:
    audit = build_fixability_audit(_payload())

    assert audit["policy"] == {
        "blocking_severities": ["CRITICAL", "HIGH", "MEDIUM"],
        "block_only_when_fixed_version_available": True,
        "sarif_evidence_required": True,
        "recheck_trigger": "every_container_build",
    }
    assert audit["summary"] == {
        "all_findings": 4,
        "fixable_blocking_findings": 1,
        "unfixed_or_deferred_blocking_severity_findings": 2,
        "severity_counts": {
            "CRITICAL": 1,
            "HIGH": 1,
            "MEDIUM": 1,
            "LOW": 1,
            "UNKNOWN": 0,
        },
    }
    assert audit["fixable_blocking_findings"] == [
        {
            "fixed_version": "1.0.1",
            "installed_version": "1.0.0",
            "package": "fixable-package",
            "severity": "HIGH",
            "status": "affected",
            "target": "bioetl:test",
            "vulnerability_id": "CVE-2026-0001",
        }
    ]
    assert len(audit["all_findings"]) == 4
    assert len(audit["unfixed_or_deferred_findings"]) == 2


def test_cli_writes_deterministic_audit_and_fails_for_fixable_finding(
    tmp_path: Path,
) -> None:
    trivy_json = tmp_path / "trivy-results.json"
    output = tmp_path / "trivy-fixability-audit.json"
    trivy_json.write_text(json.dumps(_payload()), encoding="utf-8")

    assert main(["--trivy-json", str(trivy_json), "--output", str(output)]) == 0
    expected = output.read_text(encoding="utf-8")
    assert (
        main(
            [
                "--trivy-json",
                str(trivy_json),
                "--output",
                str(output),
                "--fail-on-fixable",
            ]
        )
        == 1
    )
    assert output.read_text(encoding="utf-8") == expected


def test_cli_strict_gate_blocks_unfixed_medium_plus_finding(tmp_path: Path) -> None:
    payload = _payload()
    results = payload["Results"]
    assert isinstance(results, list)
    result = results[0]
    assert isinstance(result, dict)
    vulnerabilities = result["Vulnerabilities"]
    assert isinstance(vulnerabilities, list)
    result["Vulnerabilities"] = [vulnerabilities[1]]
    trivy_json = tmp_path / "trivy-results.json"
    output = tmp_path / "trivy-fixability-audit.json"
    trivy_json.write_text(json.dumps(payload), encoding="utf-8")

    common = ["--trivy-json", str(trivy_json), "--output", str(output)]
    assert main([*common, "--fail-on-fixable"]) == 0
    assert main([*common, "--fail-on-blocking"]) == 1


@pytest.mark.parametrize(
    ("severity", "status", "expected"),
    [
        ("CRITICAL", "affected", True),
        ("HIGH", "fixed", True),
        ("MEDIUM", "affected", True),
        ("MEDIUM", "not_affected", False),
        ("LOW", "affected", False),
        ("UNKNOWN", "affected", False),
    ],
)
def test_strict_gate_matches_trivy_medium_plus_policy(
    severity: str, status: str, expected: bool
) -> None:
    assert (
        is_strict_blocking_finding({"severity": severity, "status": status})
        is expected
    )


@pytest.mark.parametrize(
    ("payload", "message"),
    [
        ({}, "Trivy JSON Results must be a non-empty list"),
        ({"Results": []}, "Trivy JSON Results must be a non-empty list"),
        ({"Results": {}}, "Trivy JSON Results must be a non-empty list"),
        (
            {"Results": [{"Vulnerabilities": {}}]},
            "Trivy JSON Vulnerabilities must be a list",
        ),
        (
            {
                "Results": [
                    {
                        "Vulnerabilities": [
                            {
                                "VulnerabilityID": "CVE-2026-0005",
                                "PkgName": "package",
                            }
                        ]
                    }
                ]
            },
            "Trivy vulnerability is missing identity fields",
        ),
    ],
)
def test_audit_preserves_trivy_validation_errors(
    payload: dict[str, object],
    message: str,
) -> None:
    with pytest.raises(ValueError, match=message):
        build_fixability_audit(payload)


def test_audit_ignores_null_vulnerabilities() -> None:
    assert (
        build_fixability_audit({"Results": [{"Vulnerabilities": None}]})["all_findings"]
        == []
    )
