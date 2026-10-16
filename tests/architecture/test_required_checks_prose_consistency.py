"""#12047: catalog policy prose claims stay aligned with governance docs.

Offline consistency is not live ruleset evidence. A green coordinator check
does not prove that GitHub is blocking merge.
"""

from __future__ import annotations

import copy
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
        errors.extend(
            _scoped_forbidden_errors(
                str(doc_path),
                text,
                policy.get("prose_scoped_forbidden_phrases"),
            )
        )
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


def _scoped_forbidden_errors(
    doc_path: str,
    text: str,
    rules: object,
) -> list[str]:
    """Flag a current-configuration claim without rejecting a marked exception."""

    if rules is None:
        return []
    if not isinstance(rules, list):
        return ["prose_scoped_forbidden_phrases must be a list"]
    errors: list[str] = []
    lines = text.splitlines()
    for rule in rules:
        if not isinstance(rule, dict):
            errors.append("scoped forbidden phrase must be a mapping")
            continue
        phrase = str(rule.get("phrase") or "")
        allow = [str(token) for token in rule.get("line_allow_if_contains_any") or []]
        if not phrase:
            errors.append("scoped forbidden phrase is empty")
            continue
        for index, line in enumerate(lines):
            if phrase not in line:
                continue
            context = line
            for previous in range(index - 1, -1, -1):
                if lines[previous].lstrip().startswith("#"):
                    context = lines[previous] + "\n" + line
                    break
            folded = context.casefold()
            if any(token.casefold() in folded for token in allow):
                continue
            errors.append(
                f"{doc_path} current-configuration claim {phrase!r} at line {index + 1}"
            )
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


def test_current_actions_disabled_claim_fails() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = "GitHub Actions are disabled.\n" + documents[target]
    errors = check_required_checks_prose(catalog, documents)
    assert any("GitHub Actions are disabled" in error and target in error for error in errors)


def test_historical_actions_disabled_sentence_is_allowed() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = (
        "### Historical record\nGitHub Actions are disabled.\n" + documents[target]
    )
    errors = check_required_checks_prose(catalog, documents)
    assert errors == []


def test_individual_workflow_disable_instruction_is_allowed() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    allow = policy["prose_scoped_forbidden_phrases"][0]["line_allow_if_contains_any"]
    assert allow == [
        "historical",
        "keep-disabled",
        "disabled_manually",
        "individual workflow",
    ]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = (
        "Disable an individual workflow: GitHub Actions are disabled for stale.yml only.\n"
        "coderabbit.yml is keep-disabled because GitHub Actions are disabled for that file.\n"
        "labeler.yml is disabled_manually: GitHub Actions are disabled for that workflow.\n"
        + documents[target]
    )
    errors = check_required_checks_prose(catalog, documents)
    assert errors == []


def test_historical_heading_does_not_allow_other_forbidden_phrases() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = "### Historical record\nActive main rulesets\n" + documents[target]
    errors = check_required_checks_prose(catalog, documents)
    assert any("Active main rulesets" in error for error in errors)


def test_each_declared_document_is_checked() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    doc_paths = [str(path) for path in policy["prose_claim_doc_paths"]]
    assert doc_paths
    documents = _repo_documents(ROOT, doc_paths)
    for doc_path in doc_paths:
        assert (ROOT / doc_path).is_file()
        mutated = dict(documents)
        mutated[doc_path] = mutated[doc_path].replace(
            "policy-anchor:merge-block",
            "policy-anchor:merge-bloc",
        )
        errors = check_required_checks_prose(catalog, mutated)
        assert any(doc_path in error and "merge-block" in error for error in errors), doc_path


def test_live_protection_boolean_true_is_rejected() -> None:
    from scripts.engineering.ci.pr_gate import load_catalog

    loaded = load_catalog(CATALOG)
    assert loaded["schema_version"] == 1
    assert loaded["policy"]["enforcement_verified_date_is_live_protection_evidence"] is False
    catalog = copy.deepcopy(_load_yaml(CATALOG))
    catalog["policy"]["enforcement_verified_date_is_live_protection_evidence"] = True
    documents = _repo_documents(ROOT, list(catalog["policy"]["prose_claim_doc_paths"]))
    errors = check_required_checks_prose(catalog, documents)
    assert any("must be false" in error for error in errors)
