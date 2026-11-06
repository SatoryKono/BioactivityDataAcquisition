# B2 tag protection preflight — 2026-11-06

Status: PARTIAL / NOT_APPROVED / NOT_APPLIED. Ruleset 26429996 remains disabled.
No tag was created, updated, deleted or pushed. No rule or bypass actor was added.

Source tree: 4af92fe06abad38388108c4b8f80b9f57a95d436. Read evidence:
`github-settings-B2-preflight-20261106.json`. Post-change settings receipt:
`github-settings-A1-post-change-20261106.json` (B2 GET 16:45:57.754381 UTC).

## Known mechanisms and authority

| Mechanism / actor | Operation supported by source | Authority | v* impact / limitation |
| --- | --- | --- | --- |
| SatoryKono, sole returned collaborator | Human Git/API tag operations are possible with write authority; no v* operation is established by the returned events | Repository admin; PAT/SSH credential inventory was not read | Human/manual creation, update and deletion remain possible while ruleset is disabled. Credentials and external clients unknown |
| GitHub Actions release.yml | workflow_dispatch, retained publish-testpypi; inspected tracked workflow does not contain a tag-ref mutation command matched by the source search | Job permissions and GITHUB_TOKEN; defaults do not prove every job is read-only | A publish job is not itself proof of tag creation. No broad negative conclusion about reusable or external automation |
| GitHub Actions docker.yml | Container build/publish paths; inspected source does not contain the searched Git tag mutation forms | Job-scoped token permissions, including publication permissions | Container image tags are not Git refs/tags/v* |
| import-linter.yml | fetch refs/tags/evidence/issue-12474-* at lines 221/287 | Read-only Git fetch | Reads evidence tags, outside v*; not a tag creator |
| cleanup_branch_candidates.sh | archive_tag_for produces archive/<branch>-<date>; archive_then_delete creates local archive tags in --apply mode | Local Git process identity; no remote tag push in that function | archive/* is outside v*; source capability is not evidence that the script ran |
| run-coderabbit-comprehensive-audit.sh | Prints an optional git tag audit/coderabbit-<timestamp> instruction requiring confirmation | Operator's local Git identity if the instruction is executed | audit/* is outside v*; instruction is not an observed push |
| Deploy keys / webhooks | Current API lists empty | No deploy-key authority observed; hooks themselves do not grant Git write access | Does not exclude GitHub Apps, account credentials or external polling |
| GitHub Apps | PAT GET /user/installations returns 403 requiring GitHub App authorized access | Full installed-app permissions and repository selection unavailable | Cannot close external tag automation preflight. Connector exposes one accessible installation 80946508 / account SatoryKono / repository_selection=all, not a complete inventory or its write permissions |

Search coverage: full restored .github, .circleci and scripts tree for common
Git/REST tag mutation forms; additionally GitHub indexed code search for git tag,
refs/tags, git push tags, createRef and deleteRef. Exact source hits are attached
in the JSON evidence. This is text-pattern coverage, not proof that no indirect
or external tag mutations exist. The complete source diff is outside B2 scope.

All returned tag pages were read: 326 tags, zero names beginning with v.
The available paginated repository events contained no CreateEvent/DeleteEvent
for tag refs. This bounded event history cannot identify historical tag creators
or establish that no tag automation exists. Tags API does not identify the actor
who created, updated or deleted a ref.

## Do the proposed rules meet the stated goal?

Current disabled proposal: target tag; include refs/tags/v*; rules deletion and
non_fast_forward; bypass actors []. Activating only this proposal would enforce
deletions and force-push restrictions on matching tags. It would not add a
creation restriction, a named publisher allowlist, signed-tag requirement,
release-asset immutability or the separate update rule. Do not describe this as
complete release immutability or authorization of all tag updates.

GitHub documents Restrict updates separately from Block force pushes:
https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets

A goal of prohibiting every existing-tag update requires a separately reviewed
update-rule proposal and compatibility analysis. Neither update/creation rules
nor bypass actors are proposed for application in this task.

## Remaining preflight

Owner read-only Settings / Integrations export or suitable GitHub App authorized
access must establish installed apps, contents write permissions, repository
selection, and known external tag clients. Review any release operator procedure
that intentionally moves or removes v* tags. Keep B2 on separate approval after
those questions are answered. No test tags are authorized, and none were used.

C2: bug_report.md and feature_request.md remain unchanged. The 2026-11-30 migration
window is not an automatic deletion approval for 2026-12-01; migration review and
an explicit owner decision are still required.
