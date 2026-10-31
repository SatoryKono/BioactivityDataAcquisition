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
    """Load one YAML file and require a mapping."""
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


def _final_anchor_end(text: str, start: int) -> int:
    """Stop the last anchor at the next blank line or heading, not at EOF."""

    consumed = 0
    for index, line in enumerate(text[start:].splitlines(keepends=True)):
        if index > 0 and (not line.strip() or line.lstrip().startswith("#")):
            return start + consumed
        consumed += len(line)
    return len(text)


def _anchor_regions(text: str) -> dict[str, list[str]]:
    """Return the text of every anchor, ending at the next anchor.

    The last anchor in a document ends at the following blank line or heading.
    A later paragraph must not satisfy that anchor.
    """

    matches = list(_ANCHOR.finditer(text))
    regions: dict[str, list[str]] = {}
    for index, match in enumerate(matches):
        if index + 1 < len(matches):
            end = matches[index + 1].start()
        else:
            end = _final_anchor_end(text, match.end())
        regions.setdefault(match.group(1), []).append(text[match.start() : end])
    return regions


def _repo_documents(root: Path, doc_paths: list[str]) -> dict[str, str]:
    """Read each declared prose document as UTF-8 text."""
    return {
        doc_path: (root / doc_path).read_text(encoding="utf-8")
        for doc_path in doc_paths
    }


def test_catalog_prose_matches_declared_documents() -> None:
    """Declared documents satisfy every catalog prose claim."""
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
    """One edited character in a required phrase fails the checker."""
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
    """An anchor id that is not a declared claim fails the checker."""
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = policy["prose_claim_doc_paths"][0]
    documents[target] += "\npolicy-anchor:not-in-catalog\n"
    errors = check_required_checks_prose(catalog, documents)
    assert any("undeclared policy-anchor:not-in-catalog" in error for error in errors)


def test_forbidden_active_circleci_phrase_fails() -> None:
    """A current active-CircleCI phrase fails even inside a historical heading."""
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = policy["prose_claim_doc_paths"][1]
    documents[target] += "\nActive main rulesets\n"
    errors = check_required_checks_prose(catalog, documents)
    assert any("Active main rulesets" in error for error in errors)


def test_current_actions_disabled_claim_fails() -> None:
    """A bare current claim that GitHub Actions are disabled fails."""
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
    """The same sentence is allowed on the first paragraph under a historical heading."""
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
    """One blank line after a historical heading still belongs to the first paragraph."""
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
    """The paragraph after that first paragraph stays forbidden."""
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
    """A current anchor cannot borrow a required phrase from another region."""
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


def test_acceptance_checkout_is_recorded_per_job() -> None:
    """Acceptance names the base checkout and the observed synthetic merge."""
    text = (ROOT / "docs/05-operations/ci-cd-integration.md").read_text(
        encoding="utf-8"
    )
    start = text.index("## Acceptance")
    end = text.index("## Historical CircleCI lane names")
    acceptance = text[start:end]
    for needle in (
        "classify-changes",
        "pr-gate-complete",
        "fast-governance",
        "class-lane",
        "github.event.pull_request.base.sha",
        "40fa210b9279c5a10568783815230a8955cc1d02",
        "4e39da041f29f57e6ba0d5ad75ccccae305c89a2",
        "refs/pull/<number>/merge",
        "refs/pull/12234/merge",
    ):
        assert needle in acceptance, needle
    assert "Jobs on `pull_request` check out the synthetic merge ref" not in text


def test_active_merge_wall_phrase_fails() -> None:
    """Restoring the merge-wall sentence in a contributor guide fails."""
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = "docs/03-guides/github-local-workflow.md"
    documents[target] += "\nGitHub-required merge wall is exactly `pr-gate-complete`\n"
    errors = check_required_checks_prose(catalog, documents)
    assert any(
        target in error and "GitHub-required merge wall" in error for error in errors
    )


def test_last_anchor_does_not_read_the_next_paragraph() -> None:
    """A later paragraph cannot satisfy the document's final policy anchor."""
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = "docs/05-operations/ci-cd-integration.md"
    original = (
        "A successful `pr-gate-complete` does not by itself block merge, "
        "because classic branch protection is absent"
    )
    replacement = (
        "A successful `pr-gate-complete` is enough by itself to block merge, "
        "because classic branch protection is absent"
    )
    assert original in documents[target]
    documents[target] = documents[target].replace(original, replacement, 1)
    errors = check_required_checks_prose(catalog, documents)
    assert any(target in error and "merge-block" in error for error in errors)


def test_github_required_context_phrase_fails() -> None:
    """Restoring the required-context table sentence fails."""
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = "docs/04-reference/github-actions-workflows.md"
    documents[target] += "\nGitHub required context is job `pr-gate-complete`\n"
    errors = check_required_checks_prose(catalog, documents)
    assert any(
        target in error and "GitHub required context is job" in error
        for error in errors
    )


def test_requires_only_final_context_phrase_fails() -> None:
    """Restoring the ruleset-requires-final-context sentence fails."""
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = "docs/00-project/governance/05-github-policy.md"
    documents[target] += (
        "\nruleset `13643213` requires only the final `pr-gate-complete` context\n"
    )
    errors = check_required_checks_prose(catalog, documents)
    assert any(
        target in error and "requires only the final" in error for error in errors
    )


def test_coordinator_workflow_stays_in_prose_claim_documents() -> None:
    """The coordinator file itself is a required prose document."""
    catalog = _load_yaml(CATALOG)
    paths = [str(item) for item in catalog["policy"]["prose_claim_doc_paths"]]
    assert catalog["coordinator_workflow"] in paths
    assert catalog["deployment"]["config_path"] in paths


def test_enforces_required_context_phrase_fails() -> None:
    """Restoring the enforcing-ruleset sentence in CONTRIBUTING fails."""
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = ".github/CONTRIBUTING.md"
    documents[target] += "\nenforces exactly one required status context\n"
    errors = check_required_checks_prose(catalog, documents)
    assert any(
        target in error and "enforces exactly one required status context" in error
        for error in errors
    )


def test_contributing_ruleset_region_cannot_borrow_disabled_wording() -> None:
    """A contradictory ruleset sentence in CONTRIBUTING cannot reuse another document."""
    catalog = _load_yaml(CATALOG)
    policy = catalog["policy"]
    documents = _repo_documents(ROOT, list(policy["prose_claim_doc_paths"]))
    target = ".github/CONTRIBUTING.md"
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


def _coordinator_step(workflow: str, step_id: str) -> str:
    """Return one Fast governance step, from its name through the next step."""

    marker = f"id: {step_id}\n"
    start = workflow.index(marker)
    head = workflow.rfind("\n      - name:", 0, start)
    nxt = workflow.find("\n      - name:", start)
    if nxt < 0:
        nxt = len(workflow)
    return workflow[head:nxt]


def test_every_prose_doc_selects_docs_governance() -> None:
    """Every declared prose path selects docs-governance."""
    from scripts.engineering.ci.pr_gate import classify_changes, load_catalog

    catalog = load_catalog(CATALOG)
    for doc_path in catalog["policy"]["prose_claim_doc_paths"]:
        matrix = classify_changes(catalog, [str(doc_path)], head_sha="a" * 40)
        assert matrix["decisions"]["docs-governance"]["decision"] == "required", (
            doc_path
        )


def test_prose_only_change_runs_pytest_without_lint_arch() -> None:
    """Prose-only paths skip lint-arch and still execute docs-lane prose pytest."""
    from scripts.engineering.ci.pr_gate import (
        NOT_APPLICABLE,
        classify_changes,
        load_catalog,
    )
    from scripts.engineering.ci.pr_lane_results import DOCS_LANE, OWNER_STEPS

    catalog = load_catalog(CATALOG)
    coordinator = (ROOT / ".github/workflows/pr-required.yml").read_text(
        encoding="utf-8"
    )
    docs_workflow = (ROOT / ".github/workflows/docs.yml").read_text(encoding="utf-8")
    assert "docs-governance'] != 'not_applicable'" in coordinator
    assert (
        "uses: SatoryKono/BioactivityDataAcquisition/.github/workflows/docs.yml@"
        in (coordinator)
    )
    assert "tests/architecture/test_required_checks_prose_consistency.py" in (
        docs_workflow
    )
    assert "lint-arch" not in docs_workflow.split("jobs:", maxsplit=1)[0]
    assert "docs-governance" in OWNER_STEPS[DOCS_LANE]

    prose_only: list[str] = []
    for doc_path in catalog["policy"]["prose_claim_doc_paths"]:
        matrix = classify_changes(catalog, [str(doc_path)], head_sha="b" * 40)
        assert matrix["decisions"]["docs-governance"]["decision"] == "required"
        if matrix["decisions"]["lint-arch"]["decision"] == NOT_APPLICABLE:
            prose_only.append(str(doc_path))
    assert prose_only == [
        ".github/CONTRIBUTING.md",
        ".github/SECURITY.md",
        "docs/00-project/governance/05-github-policy.md",
        "docs/03-guides/github-local-workflow.md",
        "docs/03-guides/github-quick-reference.md",
        "docs/04-reference/github-actions-workflows.md",
        "docs/05-operations/ci-cd-integration.md",
        "docs/05-operations/ci-workflow-map.md",
        "docs/05-operations/release-checklist.md",
        "docs/05-operations/runbooks/github-settings-quarterly-review.md",
    ]


def test_individual_workflow_disable_instruction_is_allowed() -> None:
    """Workflow disable markers allow the phrase only on the same line."""
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
    """A historical heading does not allow other whole-file forbidden phrases."""
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
    """A later section does not inherit a historical heading."""
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
    """A later paragraph in the same historical section stays forbidden."""
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
    """A workflow marker does not allow the phrase in the next paragraph."""
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
    """A workflow marker in a heading does not allow the body."""
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
    """Removing the merge-block anchor from any declared document fails."""
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
    """The live-protection boolean must stay false."""
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
