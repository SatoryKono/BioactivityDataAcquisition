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

    declared_ids = {str(claim.get("id")) for claim in claims if isinstance(claim, dict)}
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
        regions = _anchor_regions(text)
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
            claim_regions = regions.get(claim_id) or [""]
            for substring in claim.get("required_substrings") or []:
                needle = str(substring)
                if needle == f"policy-anchor:{claim_id}":
                    continue
                if not all(needle in region for region in claim_regions):
                    errors.append(f"{doc_path} claim {claim_id} missing {needle!r}")
    return errors


def _scoped_forbidden_errors(
    doc_path: str,
    text: str,
    rules: object,
) -> list[str]:
    """Flag a current-configuration claim outside its marked context.

    ``historical`` applies on the same line, or in the first paragraph under a
    heading that contains that word. One blank line after that heading is the
    Markdown separator, not a new paragraph. A later paragraph or a later
    section does not inherit the heading. Workflow markers apply only on the
    same line.
    """

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
        allow = [
            str(token).casefold()
            for token in rule.get("line_allow_if_contains_any") or []
        ]
        if not phrase:
            errors.append("scoped forbidden phrase is empty")
            continue
        workflow_tokens = [token for token in allow if token != "historical"]
        for index, line in enumerate(lines):
            if phrase not in line:
                continue
            if _phrase_context_is_allowed(lines, index, line, allow, workflow_tokens):
                continue
            errors.append(
                f"{doc_path} current-configuration claim {phrase!r} at line {index + 1}"
            )
    return errors


def _phrase_context_is_allowed(
    lines: list[str],
    index: int,
    line: str,
    allow: list[str],
    workflow_tokens: list[str],
) -> bool:
    folded_line = line.casefold()
    if any(token in folded_line for token in workflow_tokens):
        return True
    if "historical" in allow and "historical" in folded_line:
        return True
    if "historical" not in allow:
        return False
    seen_blank = False
    for previous in range(index - 1, -1, -1):
        if not lines[previous].strip():
            if seen_blank:
                return False
            seen_blank = True
            continue
        if lines[previous].lstrip().startswith("#"):
            return "historical" in lines[previous].casefold()
        if seen_blank:
            return False
    return False


def _anchor_regions(text: str) -> dict[str, list[str]]:
    """Return the text of every anchor, ending at the next anchor."""

    matches = list(_ANCHOR.finditer(text))
    regions: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        regions.setdefault(match.group(1), []).append(text[match.start() : end])
    return regions


def _repo_documents(root: Path, doc_paths: list[str]) -> dict[str, str]:
    return {
        doc_path: (root / doc_path).read_text(encoding="utf-8")
        for doc_path in doc_paths
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
    assert any(
        "GitHub Actions are disabled" in error and target in error for error in errors
    )


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


def test_blank_line_after_historical_heading_allows_first_paragraph() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = (
        "### Historical record\n\nGitHub Actions are disabled.\n" + documents[target]
    )
    errors = check_required_checks_prose(catalog, documents)
    assert errors == []


def test_second_paragraph_after_heading_blank_stays_forbidden() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = (
        "### Historical record\n"
        "\n"
        "GitHub Actions are disabled.\n"
        "\n"
        "GitHub Actions are disabled.\n" + documents[target]
    )
    errors = check_required_checks_prose(catalog, documents)
    claim_errors = [error for error in errors if "GitHub Actions are disabled" in error]
    assert claim_errors == [
        f"{target} current-configuration claim 'GitHub Actions are disabled' at line 5"
    ]


def test_anchor_region_does_not_reuse_wording_elsewhere() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = "docs/00-project/governance/05-github-policy.md"
    old = (
        "<!-- policy-anchor:ruleset-enforcement-mode --> Rulesets `13643213` "
        "and `15730586` are `enforcement: disabled`."
    )
    assert old in documents[target]
    documents[target] = documents[target].replace(
        old,
        old.replace("`enforcement: disabled`", "`enforcement: active`"),
        1,
    )
    assert "enforcement: disabled" in documents[target]
    errors = check_required_checks_prose(catalog, documents)
    assert any(
        target in error
        and "ruleset-enforcement-mode" in error
        and "enforcement: disabled" in error
        for error in errors
    )


def test_every_prose_doc_selects_docs_governance() -> None:
    from scripts.engineering.ci.pr_gate import classify_changes, load_catalog

    catalog = load_catalog(CATALOG)
    docs_yml = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert "tests/architecture/test_required_checks_prose_consistency.py" in docs_yml
    for doc_path in catalog["policy"]["prose_claim_doc_paths"]:
        matrix = classify_changes(catalog, [str(doc_path)], head_sha="a" * 40)
        assert matrix["decisions"]["docs-governance"]["decision"] == "required", (
            doc_path
        )


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
    documents[target] = (
        "### Historical record\nActive main rulesets\n" + documents[target]
    )
    errors = check_required_checks_prose(catalog, documents)
    assert any("Active main rulesets" in error for error in errors)


def test_historical_section_does_not_allow_current_claim_later_in_file() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = (
        "### Historical record\n"
        "GitHub Actions are disabled.\n"
        "\n"
        "### Current configuration\n"
        "GitHub Actions are disabled.\n" + documents[target]
    )
    errors = check_required_checks_prose(catalog, documents)
    claim_errors = [error for error in errors if "GitHub Actions are disabled" in error]
    assert claim_errors == [
        f"{target} current-configuration claim 'GitHub Actions are disabled' at line 5"
    ]


def test_later_paragraph_in_historical_section_stays_forbidden() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = (
        "### Historical record\n"
        "GitHub Actions are disabled.\n"
        "\n"
        "GitHub Actions are disabled.\n" + documents[target]
    )
    errors = check_required_checks_prose(catalog, documents)
    claim_errors = [error for error in errors if "GitHub Actions are disabled" in error]
    assert claim_errors == [
        f"{target} current-configuration claim 'GitHub Actions are disabled' at line 4"
    ]


def test_workflow_marker_does_not_allow_the_next_paragraph() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    marked_lines = (
        "coderabbit.yml is keep-disabled because GitHub Actions are disabled for that file.",
        "labeler.yml is disabled_manually: GitHub Actions are disabled for that workflow.",
        "Disable an individual workflow: GitHub Actions are disabled for stale.yml only.",
    )
    for marked in marked_lines:
        sample = dict(documents)
        sample[target] = (
            f"{marked}\n\nGitHub Actions are disabled.\n" + documents[target]
        )
        errors = check_required_checks_prose(catalog, sample)
        claim_errors = [
            error for error in errors if "GitHub Actions are disabled" in error
        ]
        assert claim_errors == [
            f"{target} current-configuration claim 'GitHub Actions are disabled' at line 3"
        ], marked


def test_workflow_marker_in_heading_does_not_allow_the_body() -> None:
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = str(policy["prose_claim_doc_paths"][0])
    documents[target] = (
        "## keep-disabled\nGitHub Actions are disabled.\n" + documents[target]
    )
    errors = check_required_checks_prose(catalog, documents)
    claim_errors = [error for error in errors if "GitHub Actions are disabled" in error]
    assert claim_errors == [
        f"{target} current-configuration claim 'GitHub Actions are disabled' at line 2"
    ]


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
        assert any(doc_path in error and "merge-block" in error for error in errors), (
            doc_path
        )


def test_live_protection_boolean_true_is_rejected() -> None:
    from scripts.engineering.ci.pr_gate import load_catalog

    loaded = load_catalog(CATALOG)
    assert loaded["schema_version"] == 1
    assert (
        loaded["policy"]["enforcement_verified_date_is_live_protection_evidence"]
        is False
    )
    catalog = copy.deepcopy(_load_yaml(CATALOG))
    catalog["policy"]["enforcement_verified_date_is_live_protection_evidence"] = True
    documents = _repo_documents(ROOT, list(catalog["policy"]["prose_claim_doc_paths"]))
    errors = check_required_checks_prose(catalog, documents)
    assert any("must be false" in error for error in errors)
