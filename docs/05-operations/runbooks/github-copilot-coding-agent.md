______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- Release engineering
- Security lane
Priority: P2
Runtime profile: GitHub Copilot coding agent (cloud); local git + read-only `gh`.
Last verified: '2026-09-12'

______________________________________________________________________

# GitHub Copilot coding agent (operator)

## Trigger

- Start or review a cloud Copilot coding-agent task in
  `SatoryKono/BioactivityDataAcquisition`.
- Escalate `GH-ENV-003` drift (environment `copilot` missing, unprotected, wrong
  branch policy, or environment secrets present).
- Confirm a `copilot/**` pull request before squash-merge.

## Impact

An unprotected `copilot` environment or agent access to publish credentials can
turn a coding-agent session into a write-capable deploy surface. Policy treats
`copilot` as **agent-runtime**, not as `ghcr-publish` / `pypi` / `testpypi` /
`observability-render-host`.

## Preconditions

- Environment `copilot` exists and is protected (`GH-ENV-003`): required
  reviewer `@SatoryKono`, custom branch policy `copilot/**` only, zero
  environment secrets. `#10311` DELETE is superseded; do not delete this env
  to “fix” drift.
- `staging` remains absent (`GH-ENV-002`).
- Instructions: [`.github/copilot-instructions.md`](../../../.github/copilot-instructions.md).
  Do not copy `.codex/skills/**` or `.devin/skills/**` into `.github/prompts`.
- REST `GET /repos/.../copilot` and `/copilot/coding_agent` currently return
  HTTP 404 with the repo PAT. Start a hosted task with documented
  `POST /agents/repos/{owner}/{repo}/tasks` or GitHub UI. MCP/firewall
  confirmation remains **GitHub UI**.

## Procedure

### Start a coding-agent task

1. Open a scoped GitHub issue (docs-only or a single bounded code change).
1. Assign Copilot coding agent from the GitHub UI (not via undocumented REST).
1. Require branch prefix `copilot/<kebab>` (hygiene already allows `copilot/`).
1. Point the agent at `.github/copilot-instructions.md`. Do not paste secrets
   or root `.env` values into the prompt, MCP config, or environment `copilot`.

### MCP / firewall / internet (UI)

Record the date of the live UI check in the issue comment:

- Custom instructions: repository file `.github/copilot-instructions.md`; do
  not duplicate the full profile in the Copilot settings pane.
- MCP: public docs only (Context7 / DeepWiki optional). **No** tokens from
  root `.env`.
- Firewall / internet: `github.com` and documentation hosts; no egress aimed at
  GHCR or PyPI **publish**.
- Do not grant `packages: write` or attach `pypi` / `ghcr-publish` /
  `testpypi` / `observability-render-host` to agent jobs.

### Review a Copilot PR

1. Head ref matches `copilot/**`.
1. No tracked workflow gained `environment: copilot`.
1. No `.env` edits, no publish-environment secrets, no tech-debt budget
   increases, no GitHub CodeQL default setup, no Discussions enablement.
1. `pr-gate-complete` is green. Squash-merge as a human. The agent MUST NOT
   approve its own PR (`can_approve_pull_request_reviews: false`).
1. GitHub review body / inline comments via `gh pr review` stay in Russian.

### GH-ENV-003 drift

```text
python -m scripts.engineering.repo github-settings-review --json-out reports/quality/github-settings-review.json --markdown-out reports/quality/github-settings-review.md
gh api repos/SatoryKono/BioactivityDataAcquisition/environments/copilot
gh api repos/SatoryKono/BioactivityDataAcquisition/environments/copilot/deployment-branch-policies
gh api repos/SatoryKono/BioactivityDataAcquisition/environments/copilot/secrets
```

Expected: `protection_rules` includes `required_reviewers` and
`branch_policy`; branch policy name `copilot/**`; `total_count` of secrets is
`0`; `staging` absent. Do **not** click Code scanning default setup or
Discussions.

If the env is missing, recreate it as protected agent-runtime (reviewer +
`copilot/**`, no secrets). Do not leave it unprotected.

## Verification

- `GH-ENV-002` pass (`staging` absent) and `GH-ENV-003` pass on a review from
  this checkout.
- Prefix-pilot PRs use `copilot/<kebab>` (hygiene allowlist). Do not put
  `environment: copilot` on tracked workflows.
- `pytest tests/architecture/test_github_governance_review.py tests/architecture/test_branch_hygiene_workflow.py -q --no-cov`.
- Quarterly review runbook:
  [github-settings-quarterly-review.md](github-settings-quarterly-review.md).

## Escalation

- Unprotected `copilot` or any environment secret on it → Security lane the
  same day; remove secrets; restore reviewer + `copilot/**`.
- Agent PR touching publish workflows or `.env` → stop merge, tighten T1/T6
  UI, do not raise debt budgets.
- Repo Copilot product REST 404 → use UI or documented agent-tasks POST;
  do not invent undocumented payloads.

## Rollback

Revert policy/tooling on a `fix/*` branch. Do not DELETE environment `copilot`
unless a new dated issue explicitly supersedes `#10371` and owner approves
DELETE by exact phrase.

## Post-incident

Link the live GET, the settings-review artifact (optional commit), and the
Copilot PR URL on #10371 / #10376.

## Compliance

- Environment `copilot` is agent-runtime (`GH-ENV-003`), not a publish surface.
- MUST NOT add environment secrets, attach `pypi` / `ghcr-publish` /
  `testpypi` / `observability-render-host`, or edit `.env`.
- MUST NOT increase tech-debt budgets, enable GitHub CodeQL default setup, or
  enable Discussions.
- `#10311` DELETE is superseded; do not delete `copilot` to clear drift.
- Review automation in `github_settings_review.py` MUST remain read-only.
