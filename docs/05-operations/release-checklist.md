______________________________________________________________________

Version: 2.0.0
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-05-26'

______________________________________________________________________

# Release Checklist Template (v6.x)

> **Purpose**: Canonical release template for BioETL v6.x.
> 
> **How to use**: Copy this file for a concrete release (e.g. `release-checklist-v6.2.0.md`), fill all fields, attach evidence links, and mark each line item `PASS`/`FAIL`.

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
| Architecture boundaries and import policy | Architecture Owner | PR diff + architecture test output | `.github/workflows/architecture.yml`, `.github/workflows/import-linter.yml`; RULES §1.4/§4.4 | **PASS** if architecture + import-linter jobs green and no new boundary violations. **FAIL** otherwise. |
| Runtime compatibility (Codex/Gemini mirrors + runtime guardrails) | Runtime Owner | Runtime-surface diff (`.codex/**`, `.gemini/**`, `docs/00-project/ai/**`) | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` | **PASS** if runtime-source updates are synced to mirrors when required and mirror drift is documented. **FAIL** if unsynced runtime behavior exists. |
| Data quality policy readiness (DQ thresholds/hash/medallion) | Data Quality Owner | DQ configs/tests + policy evidence | `.github/workflows/tests.yml` (DQ-related jobs), `.github/workflows/schema-governance.yml`; RULES §2.4/§2.8 | **PASS** if DQ checks green and thresholds/policies for release scope are validated (soft 5%, hard 20%). **FAIL** on any blocking DQ gate. |
| Documentation governance readiness | Docs Owner | Updated docs set + links matrix | `.github/workflows/docs.yml`, `.github/workflows/skills-consistency.yml`; RULES §6 | **PASS** if docs governance jobs green and changed contracts/behavior are documented. **FAIL** if docs gate fails or contract docs missing. |
| Type/lint/test baseline | QA Owner | CI run for branch head | `.github/workflows/tests.yml`, `.github/workflows/type-checking.yml` | **PASS** if required CI checks are green on release candidate SHA. **FAIL** otherwise. |
| Security & secret hygiene | Security Owner | Security scan outputs + VCR sanitization report | `.github/workflows/security.yml`, `.github/workflows/compiled-artifacts-block.yml` | **PASS** if no blocking HIGH/CRITICAL findings for release policy and no secret leaks. **FAIL** otherwise. |

---

## 2) Release

| Checkpoint | Owner | Input artifact | Quality gate / policy workflow | Done criteria (PASS / FAIL) |
|---|---|---|---|---|
| Version and changelog freeze | Release Manager | `pyproject.toml`, `CHANGELOG.md`, release notes draft | RULES release/deprecation governance | **PASS** if version/tag/changelog aligned to same `v6.x.y` and approved. **FAIL** on mismatch. |
| Tag creation and signed release record | Release Manager | Git tag + tag annotation | `.github/workflows/release.yml` | **PASS** if annotated tag created for approved SHA and release workflow starts for that tag. **FAIL** if wrong SHA/tag metadata. |
| Build artifacts production (wheel/sdist) | Release Engineer | CI artifacts from release run | `.github/workflows/release.yml` | **PASS** if wheel+sdist build succeeds and artifacts attached to release run. **FAIL** on missing/failed artifacts. |
| Publish and provenance | Release Engineer | Publish logs, package registry record | `.github/workflows/release.yml` (publish jobs) | **PASS** if publish steps complete and provenance/identity checks pass per workflow output. **FAIL** otherwise. |
| Runtime compatibility confirmation for released assets | Runtime Owner | Install/run smoke evidence for released package | `.github/workflows/tests.yml` smoke jobs + local smoke notes | **PASS** if package install and CLI/runtime smoke pass for release artifact. **FAIL** on runtime regressions. |

---

## 3) Post-release

| Checkpoint | Owner | Input artifact | Quality gate / policy workflow | Done criteria (PASS / FAIL) |
|---|---|---|---|---|
| Post-release regression watch (24–48h) | QA Owner | First post-release CI window | `.github/workflows/tests.yml`, `.github/workflows/contract-tests.yml` | **PASS** if no critical regressions in first monitoring window. **FAIL** if production-blocking regression found. |
| Contract and schema drift watch | Data Contract Owner | Drift reports, governance checks | `.github/workflows/contract-governance-fast-check.yml`, `.github/workflows/schema-governance.yml`, `.github/workflows/provider-contract-drift.yml` | **PASS** if no unapproved contract/schema drift introduced by release. **FAIL** if drift gate breaks. |
| Documentation and migration follow-up | Docs Owner | Published release notes + migration notes | `.github/workflows/docs.yml`; RULES contract/versioning policy | **PASS** if release notes and migration notes published and linked from canonical docs. **FAIL** if migration guidance missing for breaking/behavior changes. |
| Quality debt and backlog capture | Architecture Owner | Follow-up issues/ADR notes | `.github/workflows/quality-debt-weekly.yml` + architecture policy docs | **PASS** if actionable follow-ups captured with owners/dates. **FAIL** if known release debt has no tracked issue. |
| Final release sign-off | Release Manager | Completed checklist + evidence package | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` | **PASS** if all mandatory checks are PASS (or approved waiver recorded). **FAIL** if unresolved mandatory FAIL exists. |

---

## Mandatory v6.x check bundle

Use this block as a hard checklist before sign-off:

- [ ] **Architecture**: `architecture.yml` + `import-linter.yml` green.
- [ ] **Data quality**: DQ/schema/contract gates green for touched pipelines/entities.
- [ ] **Documentation**: docs governance and mirror consistency checks green.
- [ ] **Runtime compatibility**: runtime source + mirrors consistency verified; release artifact smoke verified.

If any mandatory item is not green, release decision = **FAIL** unless explicit waiver is approved and documented.

---

## Evidence to attach

Attach these links in the concrete release checklist/PR:

1. **CI run links**
   - `tests.yml` run URL
   - `type-checking.yml` run URL
   - `architecture.yml` / `import-linter.yml` run URLs
   - `docs.yml` run URL
   - `schema-governance.yml` / `contract-governance-fast-check.yml` run URLs
   - `release.yml` run URL
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
