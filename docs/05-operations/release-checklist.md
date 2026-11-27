______________________________________________________________________

Version: 2.1.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-15'

______________________________________________________________________

# Release Checklist Template (v6.x)

> **Purpose**: Canonical release template for BioETL v6.x.
> 
> **How to use**: Copy this file for a concrete release (e.g. `release-checklist-v6.2.0.md`), fill all fields, attach evidence links, and mark each line item `PASS`/`FAIL`.

Record the candidate SHA and the `pr-gate-complete` result. A successful coordinator job does not by itself block merge: on the 2026-10-16 read, classic branch protection was absent and rulesets `13643213` and `15730586` were `enforcement: disabled`.
<!-- policy-anchor:deployment-provider --> `deployment.provider=github_actions`. <!-- policy-anchor:ruleset-enforcement-mode --> Ruleset `13643213` is `enforcement: active` (GET 2026-11-06); rulesets `15730586` and `24517966` were deleted on 2026-11-02 (settings-audit phase 0). <!-- policy-anchor:stored-ruleset-contexts --> The active rule requires `pr-gate-complete` (GET 2026-11-06); the rule binds this context to GitHub Actions App 15368 (integration_id=15368). <!-- policy-anchor:target-gha-context --> `pr-gate-complete` is the context stored on ruleset `13643213` since 2026-11-02. <!-- policy-anchor:enforcement-verified-date --> `2026-10-09` is not proof of active merge protection. <!-- policy-anchor:merge-block --> A successful `pr-gate-complete` does not by itself block merge; the active server rule requires it. An offline catalog match does not confirm live server rulesets. Positive/negative merge acceptance was not run in this audit.
GitHub Actions `release.yml` is manually dispatched: it builds distributions,
tests installation and can publish to TestPyPI on a non-dry run. Its definition
does not publish to production PyPI or upload GitHub Release assets. A build-only
success cannot satisfy a publish checkpoint. See the [migration workflow map](ci-workflow-map.md).

## Release metadata

- **Release version**: `<v6.x.y>`
- **Release date (UTC)**: `<YYYY-MM-DD>`
- **Release manager**: `<name>`
- **Approvers**: `<name1, name2>`
- **Commit SHA**: `<sha>`
- **Release tag**: `<v6.x.y>`
- **Scope summary**: `<what changed>`

---

## 1) Pre-release

| Checkpoint | Owner | Input artifact | Quality gate / policy workflow | Done criteria (PASS / FAIL) |
|---|---|---|---|---|
| Architecture boundaries and import policy | Architecture Owner | PR diff + architecture test output | GitHub Actions `pr-required.yml` applicable `lint-arch` steps; RULES §1.4/§4.4 | **PASS** if required architecture and import checks are evidenced and no new boundary violations exist. **FAIL** otherwise. |
| Runtime compatibility (Codex/Junie mirrors and runtime guardrails) | Runtime Owner | Runtime-surface diff (`.codex/**`, `.junie/**`, `.devin/**`, `docs/00-project/ai/**`) | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` | **PASS** if runtime-source updates are synced to mirrors when required and mirror drift is documented. **FAIL** if unsynced runtime behavior exists. |
| Data quality policy readiness (DQ thresholds/hash/medallion) | Data Quality Owner | DQ configs/tests + policy evidence | Scope-specific DQ, schema and contract evidence; RULES §2.4/§2.8 | **PASS** if DQ checks green and the release scope validates the active threshold surface explicitly (`configs/base/quality.yaml` currently hard-fail 0.50; contract/runtime fallbacks currently hard-fail 20%). **FAIL** on any blocking DQ gate. |
| Documentation governance readiness | Docs Owner | Updated docs set + links matrix | GitHub Actions `pr-required.yml` docs lane and applicable mirror checks; RULES §6 | **PASS** if docs governance jobs green and changed contracts/behavior are documented. **FAIL** if docs gate fails or contract docs missing. |
| Type/lint/test baseline | QA Owner | CI runs with tested checkout SHA, PR head and base SHAs | GitHub Actions `pr-required.yml` applicable class-lane steps | **PASS** if required checks are green for the relevant PR merge candidate and exact release candidate SHA evidence is separately recorded. **FAIL** otherwise. |
| Security & secret hygiene | Security Owner | Security scan outputs + VCR sanitization report | GitHub Actions applicable security checks and release `security-gate` | **PASS** if no blocking HIGH/CRITICAL findings for release policy and no secret leaks. **FAIL** otherwise. |

---

## 2) Release

| Checkpoint | Owner | Input artifact | Quality gate / policy workflow | Done criteria (PASS / FAIL) |
|---|---|---|---|---|
| Version and changelog freeze | Release Manager | `pyproject.toml`, `CHANGELOG.md`, release notes draft | RULES release/deprecation governance | **PASS** if version/tag/changelog aligned to same `v6.x.y` and approved. **FAIL** on mismatch. |
| Tag creation and signed release record | Release Manager | Git tag + tag annotation | Release-manager evidence and exact-SHA build evidence | **PASS** if annotated tag created for approved SHA and the validated artifact identity matches that exact approved SHA. **FAIL** if wrong SHA/tag metadata. |
| Build artifacts production (wheel/sdist) | Release Engineer | CI artifacts from release run | GitHub Actions `release.yml` build plus release-manager evidence | **PASS** if wheel+sdist build succeeds and artifacts attached to release run. **FAIL** on missing/failed artifacts. |
| Publish and provenance | Release Engineer | Publish logs, package registry record | Protected promotion (not yet accepted; #11931) | **PASS** if publish steps complete and provenance/identity checks pass per workflow output. **FAIL** otherwise. |
| Runtime compatibility confirmation for released assets | Runtime Owner | Install/run smoke evidence for released package | GitHub Actions `release.yml` test-install and release tests; local smoke notes | **PASS** if package install and CLI/runtime smoke pass for release artifact. **FAIL** on runtime regressions. |

---

## 3) Post-release

| Checkpoint | Owner | Input artifact | Quality gate / policy workflow | Done criteria (PASS / FAIL) |
|---|---|---|---|---|
| Post-release regression watch (24–48h) | QA Owner | First post-release CI window | GitHub Actions test evidence and the retained local-only contract campaign | **PASS** if no critical regressions in first monitoring window. **FAIL** if production-blocking regression found. |
| Contract and schema drift watch | Data Contract Owner | Drift reports, governance checks | Scope-specific contract and schema checks | **PASS** if no unapproved contract/schema drift introduced by release. **FAIL** if drift gate breaks. |
| Documentation and migration follow-up | Docs Owner | Published release notes + migration notes | GitHub Actions docs governance; RULES contract/versioning policy | **PASS** if release notes and migration notes published and linked from canonical docs. **FAIL** if migration guidance missing for breaking/behavior changes. |
| Quality debt and backlog capture | Architecture Owner | Follow-up issues/ADR notes | Canonical local debt audits and architecture policy docs; disabled automation stays disabled | **PASS** if actionable follow-ups captured with owners/dates. **FAIL** if known release debt has no tracked issue. |
| Final release sign-off | Release Manager | Completed checklist + evidence package | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` | **PASS** if all mandatory checks are PASS (or approved waiver recorded). **FAIL** if unresolved mandatory FAIL exists. |

---

## Mandatory v6.x check bundle

Use this block as a hard checklist before sign-off:

- [ ] **Architecture**: applicable GitHub Actions architecture and import checks green, with additional scope evidence where needed.
- [ ] **Data quality**: DQ/schema/contract gates green for touched pipelines/entities.
- [ ] **Documentation**: docs governance and mirror consistency checks green.
- [ ] **Runtime compatibility**: runtime source + mirrors consistency verified; release artifact smoke verified.

If any mandatory item is not green, release decision = **FAIL** unless explicit waiver is approved and documented.

---

## Evidence to attach

Attach these links in the concrete release checklist/PR:

1. **CI run links**
   - GitHub Actions run and applicable test, mypy, architecture and docs job URLs, with the actual tested checkout SHA and, for PR runs, head and base SHAs. PR class-lane checkout uses the synthetic merge SHA, not the head SHA; do not treat its result as exact-head or release-artifact evidence without separate verification.
   - Scope-specific schema and semantic governance evidence
   - GitHub Actions `release.yml` run URL plus separately approved publication receipt
2. **Build and publish artifacts**
   - wheel artifact URL
   - sdist artifact URL
   - package publish log URL / registry page URL
3. **Release notes**
   - GitHub Release page URL
   - changelog entry permalink
4. **Migration notes**
   - migration guide URL (required for breaking changes)
   - compatibility notes URL (runtime/config/schema changes)
5. **Waivers (if any)**
   - issue/ADR link
   - approver + expiry date

---

## Decision log (for this release instance)

| Item | Status | Link / Note |
|---|---|---|
| Go / No-Go decision | `<GO / NO-GO>` | `<meeting note or issue>` |
| Approved waivers | `<none / list>` | `<links>` |
| Final sign-off timestamp (UTC) | `<YYYY-MM-DD HH:MM>` | `<owner>` |

______________________________________________________________________

*Template published: 2026-05-26 (UTC)*
*Applies to: BioETL v6.x releases*
