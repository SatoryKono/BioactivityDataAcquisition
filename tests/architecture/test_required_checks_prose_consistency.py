"""#12047: catalog policy prose claims stay aligned with governance docs.

Offline consistency is not live ruleset evidence. A green coordinator check
does not prove that GitHub is blocking merge.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import pytest
import yaml

_ANCHOR = re.compile(r"policy-anchor:([a-z0-9-]+)")

pytestmark = pytest.mark.architecture

ROOT = Path(__file__).resolve().parents[2]
CATALOG = ROOT / "configs/quality/github_required_checks.yaml"


def _load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise AssertionError(f"{path} must be a mapping")
    return data


def check_required_checks_prose(
    catalog: dict[str, Any],
    documents: dict[str, str],
) -> list[str]:
    """Return consistency errors. Empty means the supplied texts agree."""

    errors: list[str] = []
    policy = catalog.get("policy")
    if not isinstance(policy, dict):
        return ["policy block missing"]
    if policy.get("enforcement_verified_date_is_live_protection_evidence") is not False:
        errors.append(
            "enforcement_verified_date_is_live_protection_evidence must be false"
        )
    doc_paths = policy.get("prose_claim_doc_paths")
    claims = policy.get("prose_claims")
    forbidden = policy.get("prose_forbidden_substrings")
    if not isinstance(doc_paths, list) or not doc_paths:
        errors.append("prose_claim_doc_paths must be a non-empty list")
        return errors
    if not isinstance(claims, list) or not claims:
        errors.append("prose_claims must be a non-empty list")
        return errors
    if not isinstance(forbidden, list):
        errors.append("prose_forbidden_substrings must be a list")
        return errors

    declared_ids = {
        str(claim.get("id")) for claim in claims if isinstance(claim, dict)
    }
    declared_anchors = {f"policy-anchor:{claim_id}" for claim_id in declared_ids}
    for doc_path in doc_paths:
        text = documents.get(str(doc_path))
        if text is None:
            errors.append(f"missing document text: {doc_path}")
            continue
        for phrase in forbidden:
            if str(phrase) in text:
                errors.append(f"{doc_path} contains forbidden phrase: {phrase}")
        found_ids = set(_ANCHOR.findall(text))
        for claim_id in sorted(found_ids - declared_ids):
            errors.append(f"{doc_path} has undeclared policy-anchor:{claim_id}")
        present = {f"policy-anchor:{item}" for item in found_ids}
        for anchor in sorted(declared_anchors - present):
            errors.append(f"{doc_path} missing {anchor}")
        for claim in claims:
            if not isinstance(claim, dict):
                errors.append("prose claim must be a mapping")
                continue
            claim_id = str(claim.get("id"))
            for substring in claim.get("required_substrings") or []:
                if str(substring) not in text:
                    errors.append(f"{doc_path} claim {claim_id} missing {substring!r}")
    return errors


def _repo_documents(root: Path, doc_paths: list[str]) -> dict[str, str]:
    return {
        doc_path: (root / doc_path).read_text(encoding="utf-8") for doc_path in doc_paths
    }


def test_catalog_prose_matches_declared_documents() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    assert policy["enforcement_verified_date"] == "2026-10-09"
    assert policy["enforcement_verified_date_is_live_protection_evidence"] is False
    assert policy["github_ruleset_13643213_enforcement"] == "disabled"
    assert policy["github_ruleset_15730586_enforcement"] == "disabled"
    errors = check_required_checks_prose(
        catalog,
        _repo_documents(ROOT, list(policy["prose_claim_doc_paths"])),
    )
    assert errors == []


def test_one_character_prose_drift_fails() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = policy["prose_claim_doc_paths"][0]
    documents[target] = documents[target].replace(
        "not proof of active merge protection",
        "not proof of active merge protectio",
        1,
    )
    errors = check_required_checks_prose(catalog, documents)
    assert any("not proof of active merge protection" in error for error in errors)


def test_undeclared_policy_anchor_fails() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = policy["prose_claim_doc_paths"][0]
    documents[target] += "\npolicy-anchor:not-in-catalog\n"
    errors = check_required_checks_prose(catalog, documents)
    assert any("undeclared policy-anchor:not-in-catalog" in error for error in errors)


def test_forbidden_active_circleci_phrase_fails() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = policy["prose_claim_doc_paths"][1]
    documents[target] += "\nActive main rulesets\n"
    errors = check_required_checks_prose(catalog, documents)
    assert any("Active main rulesets" in error for error in errors)
