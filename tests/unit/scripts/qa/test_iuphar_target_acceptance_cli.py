"""Smoke checks for the offline IUPHAR acceptance CLI entrypoint."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from scripts.engineering.qa import iuphar_target_acceptance
from scripts.engineering.qa.iuphar_target_acceptance import main

pytestmark = pytest.mark.unit


def test_iuphar_target_acceptance_help_imports_load_profile() -> None:
    with pytest.raises(SystemExit) as exited:
        main(["--help"])
    assert exited.value.code == 0


def test_iuphar_target_acceptance_forwards_matching_policy(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    matching_policy = "rf002-uniprot-roles-2026-11-23"
    profile = SimpleNamespace(
        snapshot=SimpleNamespace(
            snapshot=SimpleNamespace(snapshot_id="test-snapshot"),
            completeness=SimpleNamespace(publishable=True),
            retrieved_at="2026-11-23T00:00:00Z",
            snapshot_manifest_sha256="a" * 64,
            species_taxon_ids=frozenset({"9606"}),
        ),
        normalization_version="bioetl-iuphar-input-v1",
        rules_version="local-rules-2026.11.23",
        classification_schema_version="3.1.0",
        matching_policy_version=matching_policy,
    )
    requests = []

    def capture_request(request, **_kwargs):
        requests.append(request)
        return {"status": "PASS"}

    monkeypatch.setattr(
        iuphar_target_acceptance, "load_profile", lambda *_a, **_kw: profile
    )
    monkeypatch.setattr(
        iuphar_target_acceptance, "run_integration_acceptance", capture_request
    )
    monkeypatch.setattr(
        iuphar_target_acceptance, "publish_acceptance_reports", lambda *_a, **_kw: None
    )

    result = main(
        [
            "--profile",
            "profile.json",
            "--profile-sha256",
            "a" * 64,
            "--stage0-manifest",
            "stage0.json",
            "--expected-labels",
            "labels.json",
            "--expected-labels-sha256",
            "b" * 64,
            "--run-id",
            "test-run",
            "--run-started-at",
            "2026-11-23T00:00:00Z",
            "--output-dir",
            "unwritten",
        ]
    )

    assert result == 0
    assert len(requests) == 1
    assert requests[0].provenance.matching_policy_version == matching_policy
