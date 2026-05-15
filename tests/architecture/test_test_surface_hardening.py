"""Architecture checks for the 2026-05-15 test-audit remediation surface."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
HARDENING_PATH = ROOT / "configs" / "quality" / "test_surface_hardening.yaml"

YamlMap = dict[str, Any]


def _load_yaml(path: Path) -> YamlMap:
    with path.open(encoding="utf-8") as handle:
        return cast(YamlMap, yaml.safe_load(handle))


def _issue_ids(payload: YamlMap) -> set[str]:
    return {
        str(entry["id"])
        for entry in cast(list[YamlMap], payload.get("issues", []))
        if isinstance(entry, dict)
    }


def _iter_helper_targets(payload: YamlMap) -> list[YamlMap]:
    helper_contracts = cast(YamlMap, payload.get("helper_contracts", {}))
    targets: list[YamlMap] = []
    for entries in helper_contracts.values():
        if isinstance(entries, list):
            targets.extend(entry for entry in entries if isinstance(entry, dict))
    return targets


@pytest.mark.architecture
def test_test_surface_hardening_registry_tracks_exact_audit_issue_set() -> None:
    payload = _load_yaml(HARDENING_PATH)

    assert payload.get("schema_version") == 1
    assert payload.get("epic_issue") == "4134"
    assert _issue_ids(payload) == {
        "4134",
        "4135",
        "4136",
        "4137",
        "4138",
        "4139",
        "4140",
        "4141",
        "4142",
        "4143",
        "4144",
    }


@pytest.mark.architecture
def test_test_surface_hardening_evidence_paths_exist() -> None:
    payload = _load_yaml(HARDENING_PATH)

    for entry in cast(list[YamlMap], payload.get("issues", [])):
        for relative_path in cast(list[str], entry.get("evidence_paths", [])):
            assert (ROOT / relative_path).exists(), (
                f"Missing hardening evidence for issue #{entry['id']}: "
                f"{relative_path}"
            )


@pytest.mark.architecture
def test_curated_helper_contract_targets_use_shared_hardening_helpers() -> None:
    payload = _load_yaml(HARDENING_PATH)

    for target in _iter_helper_targets(payload):
        relative_path = cast(str, target["path"])
        file_path = ROOT / relative_path
        text = file_path.read_text(encoding="utf-8")

        required_import = cast(str, target["required_import"])
        assert required_import in text, (
            f"{relative_path} must import {required_import} as part of test-surface "
            "hardening"
        )

        for forbidden in cast(list[str], target.get("forbidden_tokens", [])):
            assert forbidden not in text, (
                f"{relative_path} must not contain forbidden hardening token "
                f"{forbidden!r}"
            )
