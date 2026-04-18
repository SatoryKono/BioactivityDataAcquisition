"""Unit tests for the testing-roadmap GitHub issue splitter script."""

from __future__ import annotations

import json

import pytest

from scripts.engineering.repo import split_testing_roadmap_issue as module


def test_build_child_issue_templates_tracks_parent_issue() -> None:
    templates = module._build_child_issue_templates(2511)

    assert len(templates) == 3
    assert all("#2511" in template.body for template in templates)
    assert (
        templates[0].title
        == "Unit Test Standards Baseline for Pure Transformation Logic"
    )


def test_build_parent_comment_references_child_issues() -> None:
    child_issues = [
        module.IssueRecord(
            number=2601,
            title="Unit Test Standards Baseline for Pure Transformation Logic",
            url="https://example.test/2601",
            state="open",
        ),
        module.IssueRecord(
            number=2602,
            title="Integration and VCR Policy Tightening for Supported Pipelines",
            url="https://example.test/2602",
            state="open",
        ),
    ]

    comment = module._build_parent_comment(
        parent_issue=2511,
        child_issues=child_issues,
    )

    assert "#2601 Unit Test Standards Baseline for Pure Transformation Logic" in comment
    assert (
        "#2602 Integration and VCR Policy Tightening for Supported Pipelines" in comment
    )
    assert "#2594 Pandera Schema Drift Checks for Selected Pipelines" in comment
    assert "Parent roadmap remains #2511." in comment


def test_run_dry_run_json_outputs_planned_items(capsys: object) -> None:
    rc = module.run(["--json"])

    assert rc == 3
    out = capsys.readouterr().out
    payload = json.loads(out)

    assert payload["parent_issue"] == 2511
    assert len(payload["child_issues"]) == 3
    assert all(item["state"] == "planned" for item in payload["child_issues"])


def test_resolve_retry_delay_uses_retry_after_header() -> None:
    delay = module._resolve_retry_delay_seconds(retry_after="3", attempt=2)

    assert delay == pytest.approx(3.0)


def test_resolve_retry_delay_falls_back_to_linear_backoff() -> None:
    delay = module._resolve_retry_delay_seconds(retry_after=None, attempt=3)

    assert delay == pytest.approx(4.5)


def test_run_apply_reuses_existing_issues_and_skips_comment(
    monkeypatch: object,
) -> None:
    existing_issue = module.IssueRecord(
        number=2601,
        title="Unit Test Standards Baseline for Pure Transformation Logic",
        url="https://example.test/2601",
        state="open",
    )
    created_issues: list[module.IssueTemplate] = []
    posted_comments: list[str] = []

    monkeypatch.setattr(module, "_require_token", lambda _token_env: "token")
    monkeypatch.setattr(
        module,
        "_list_repo_issues",
        lambda _owner, _repo, _token: [existing_issue],
    )

    def _fake_create_issue(
        *,
        owner: str,
        repo: str,
        token: str,
        template: module.IssueTemplate,
    ) -> module.IssueRecord:
        created_issues.append(template)
        return module.IssueRecord(
            number=2600 + len(created_issues) + 1,
            title=template.title,
            url=f"https://example.test/{2600 + len(created_issues) + 1}",
            state="open",
        )

    monkeypatch.setattr(module, "_create_issue", _fake_create_issue)
    monkeypatch.setattr(
        module,
        "_post_parent_comment",
        lambda **kwargs: posted_comments.append(str(kwargs["body"])),
    )

    rc = module.run(["--apply"])

    assert rc == 3
    assert len(created_issues) == 2
    assert posted_comments == []
