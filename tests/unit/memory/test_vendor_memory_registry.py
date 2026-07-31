"""Governance contracts for vendor-hosted memory evidence."""

from __future__ import annotations

from pathlib import Path

import yaml

_REGISTRY = Path(__file__).parents[3] / "src/memory/catalog/vendor_memory_registry.yaml"


def test_vendor_registry_is_complete_and_fail_closed() -> None:
    payload = yaml.safe_load(_REGISTRY.read_text(encoding="utf-8"))
    vendors = payload["vendors"]

    assert {entry["vendor"] for entry in vendors} == {
        "cursor",
        "devin",
        "github-copilot",
        "google-gemini",
        "jetbrains-junie",
    }
    for entry in vendors:
        assert entry["runtime_status"] in {"VERIFIED", "BLOCKED_EXTERNAL"}
        if entry["runtime_status"] == "VERIFIED":
            assert entry.get("dated_test_evidence")
            assert entry.get("deletion_test") == "PASS"
            assert entry.get("isolation_test") == "PASS"
        else:
            assert entry["blocker"]
        assert not any(
            key in entry
            for key in ("token", "access_token", "refresh_token", "conversation")
        )
