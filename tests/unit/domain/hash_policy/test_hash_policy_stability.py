"""Contract tests for hash policy stability and change management rules."""

from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from typing import Any

import pytest
import yaml

from bioetl.domain.transformations import generate_content_hash

pytestmark = pytest.mark.unit

UPDATE_SNAPSHOTS = os.environ.get("UPDATE_SNAPSHOTS", "0") == "1"
ROOT = Path(__file__).resolve().parents[4]
FIXTURES_DIR = ROOT / "tests/fixtures/hash_policy"
SNAPSHOTS_DIR = Path(__file__).parent / "snapshots"
POLICY_DIR = ROOT / "tests/fixtures/hash_policy/policy"


def _load_yaml(path: Path) -> dict[str, Any]:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _save_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )


def _policy_fingerprint(policy: dict[str, Any]) -> str:
    policy_payload = {
        "include_fields": policy["hash_policy"]["include_fields"],
        "exclude_fields": policy["hash_policy"]["exclude_fields"],
        "exclude_patterns": policy["hash_policy"].get("exclude_patterns", []),
        "normalization": policy["hash_policy"]["normalization"],
    }
    canonical = json.dumps(policy_payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _parse_semver(version: str) -> tuple[int, int, int]:
    major, minor, patch = version.split(".")
    return int(major), int(minor), int(patch)


class TestHashPolicyStability:
    """Hash policy contract tests for fixed fixtures and change governance."""

    def test_hash_stability_snapshot_for_fixed_fixtures(self) -> None:
        """Content hash MUST remain stable for fixed fixture records."""
        fixture_path = FIXTURES_DIR / "chembl_activity.yaml"
        fixture = _load_yaml(fixture_path)

        current_hashes = {
            record["name"]: generate_content_hash(record["input"], fixture["provider"])
            for record in fixture["records"]
        }

        snapshot_path = SNAPSHOTS_DIR / "chembl_activity_hashes.json"
        if UPDATE_SNAPSHOTS or not snapshot_path.exists():
            _save_json(snapshot_path, current_hashes)
            return

        assert current_hashes == _load_json(snapshot_path)

    def test_hash_policy_contract_fields_are_explicit(self) -> None:
        """Policy file MUST explicitly define include/exclude and normalization rules."""
        policy_path = POLICY_DIR / "chembl_activity.yaml"
        policy = _load_yaml(policy_path)

        hash_policy = policy["hash_policy"]
        assert hash_policy.get("include_fields"), "include_fields MUST be explicit"
        assert hash_policy.get("exclude_fields"), "exclude_fields MUST be explicit"
        assert hash_policy.get("normalization"), "normalization MUST be explicit"

        normalization = hash_policy["normalization"]
        assert normalization.get("trim_strings") is True
        assert normalization["round_floats"]["enabled"] is True
        assert normalization["round_floats"]["precision"] == 10
        assert normalization["dates"]["format"] == "YYYY-MM-DD"
        assert normalization["null_handling"]["nan_to_null"] is True
        assert normalization["null_handling"]["inf_to_null"] is True

    def test_policy_change_requires_version_bump_and_migration_note(self) -> None:
        """Policy changes MUST bump contract version and include migration note."""
        policy_path = POLICY_DIR / "chembl_activity.yaml"
        snapshot_path = SNAPSHOTS_DIR / "chembl_activity_policy.json"

        policy = _load_yaml(policy_path)
        contract = policy["contract"]
        current = {
            "provider": policy["provider"],
            "entity": policy["entity"],
            "contract_version": contract["version"],
            "policy_fingerprint": _policy_fingerprint(policy),
            "migration_note": contract["migration_note"],
        }

        if UPDATE_SNAPSHOTS or not snapshot_path.exists():
            _save_json(snapshot_path, current)
            return

        previous = _load_json(snapshot_path)
        policy_changed = current["policy_fingerprint"] != previous["policy_fingerprint"]

        assert current["migration_note"].strip(), "migration_note MUST be non-empty"

        if policy_changed:
            assert _parse_semver(current["contract_version"]) > _parse_semver(
                previous["contract_version"]
            ), (
                "Hash policy changed but contract.version was not bumped. "
                "Increment SemVer and provide migration note."
            )

        assert current["provider"] == previous["provider"]
        assert current["entity"] == previous["entity"]
