______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- Security lane
- Release engineering
Priority: P2
Runtime profile: Local-Only governance review; GitHub API read-only access.
Last verified: '2026-08-30'

______________________________________________________________________

# Quarterly read-only GitHub settings review

## Trigger

- Scheduled on the first day of January, April, July, and October by
  .github/workflows/github-settings-quarterly-review.yml.
- Run manually after migrations affecting rulesets, protected branches, merge
  methods, Actions policy, environments, security settings, CODEOWNERS, labels,
  Issue Forms, or Wiki ownership.
- Run before closing a governance issue whose acceptance criteria depend on
  live repository settings.

## Impact

Configuration drift can leave required checks unenforced, publishing
environments unprotected, security automation unavailable, or contributor
intake inconsistent. The review records drift without changing repository
state.

## Preconditions

- Use the checkout of the branch whose policy is being reviewed.
- Discover repository identity and the default branch dynamically.
- Provide a read-capable GH_TOKEN or GITHUB_TOKEN. Local execution may use one
  of the GitHub tokens in the repository-root .env; never print it.
- Read docs/00-project/governance/05-github-policy.md,
  docs/00-project/governance/github-label-taxonomy.md, and
  configs/quality/github_governance_policy.json.

## Procedure

1. Run the workflow with workflow_dispatch or execute locally:

       python -m scripts.engineering.repo github-settings-review --json-out reports/quality/github-settings-review.json --markdown-out reports/quality/github-settings-review.md

1. Confirm the report records the discovered repository/default branch and
   automation_mutated_github: false.
1. Review every control: rulesets, merge settings, Actions SHA policy,
   protected environments, Dependabot, CodeQL, secret scanning, workflow
   health, CODEOWNERS, Wiki, Issue Forms, and automation labels.
1. For an existing mapped issue, link the evidence there. For new drift, the
   accountable human creates a governance issue containing control ID,
   evidence, owner, risk, decision, due date, and artifact URL.
1. Do not make settings changes from this workflow. Settings, secrets,
   branches, labels, environments, and issues are outside its write surface.
1. Attach the JSON and Markdown artifacts to the review record. The scheduled
   workflow retains them for 30 days.

The initial baseline is
reports/quality/github-settings-review-2026-08-30.json and its Markdown
companion.

## Verification

- The workflow token permissions contain read scopes only.
- The tool accepts only gh repo view and GET-form gh api commands and rejects
  method, field, input, and issue-creation arguments.
- Every live label appears once as canonical, deprecated, or retained.
- Every non-pass control has evidence, owner, risk, decision, and due date.
- Existing drift links to an existing issue where configured; automation never
  opens the issue.
- The workflow artifact contains both JSON and Markdown output.

## Escalation

- If an endpoint is unavailable to GITHUB_TOKEN, record unavailable and have
  the owner rerun locally with a read-capable token from root .env.
- If live state conflicts with GitHub Policy, treat live state as evidence and
  the policy/configuration as expected state; open or update the mapped issue.
- Escalate high-risk drift to the Security lane or Release engineering on the
  same review day.
- Never broaden token permissions silently merely to make a control pass.

## Rollback

The review itself is read-only and has no GitHub-state rollback. If a report
was generated from the wrong checkout or repository, discard that artifact,
rerun with the correct source, and retain the failed run link for traceability.
Revert policy/tooling changes through the normal pull-request workflow.

## Post-incident

- Record the workflow run, report artifact, issues created or updated, and
  final decisions.
- Rerun after remediation and link the confirming report.
- Update the policy, configuration, tests, and this runbook together when a
  control or ownership decision changes.

## Compliance

- Review automation MUST remain read-only.
- No drift may be hidden by weakening a rule, increasing a debt budget, or
  removing a control.
- Label deletion remains forbidden until the configured migration window and
  exit criteria are satisfied.
