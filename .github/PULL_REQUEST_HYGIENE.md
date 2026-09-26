# Pull Request Hygiene Policy

## Purpose

Keep open pull requests focused on active engineering work.

Debt, governance, and audit follow-up belong in issues first. Draft pull
requests remain useful for traceability, but they must not become the primary
backlog for long-lived technical-debt work.

## Canonical Rule

- Active engineering work may stay open as a pull request.
- Long-lived debt or governance tracking must live in issues, not only in draft
  PRs.
- Report-only or bot-generated draft PRs are not canonical backlog trackers.

## Deterministic Hygiene Closure Rule

The scheduled PR hygiene workflow may auto-close an open PR only when all of
the following are true:

1. the PR is still in `draft` state;
2. the PR already has the `stale` label from the repository stale workflow;
3. the PR has been inactive for at least `21` days;
4. the PR is clearly report-noise because either:
   - the author is a GitHub `Bot`; or
   - the title/body contains one of the deterministic markers:
     `report-only`, `bot-generated`, `generated report`, `generated artifact`.

## Live GitHub state (#10263)

`stale.yml` and `pr-hygiene.yml` are **keep-disabled**
(`disabled_manually`). They do not run. This policy remains the canonical
closure rule for when those lanes are re-enabled together.

- `stale.yml` YAML still uses 14 days to stale and 7 days to close PRs. That
  contradicts this 21-day draft-only rule. Do **not** re-enable `stale.yml`
  until `days-before-pr-*` and exemptions match this document.
- `pr-hygiene.yml` already encodes the 21-day draft + `stale` label +
  report-noise markers. It depends on the `stale` label from `stale.yml`, so
  it stays disabled with that workflow.
- Do not weaken stale automation to close non-draft engineering PRs.

Until both workflows are re-enabled under this policy, close matching draft
report-noise PRs manually and leave a comment that links here.

## Traceability Requirements

- Auto-closure must post a comment that links back to this policy.
- The PR discussion and linked artifacts stay in GitHub history.
- If the work is still needed, reopen it as an issue-backed change rather than
  leaving it buried in dormant draft PR backlog.
