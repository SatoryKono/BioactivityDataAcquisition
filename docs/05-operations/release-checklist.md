______________________________________________________________________

Version: 2.0.1
Status: active
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-10-06'

______________________________________________________________________

# Release Checklist Template (v6.x)

> **Purpose**: Canonical release template for BioETL v6.x.
> 
> **How to use**: Copy this file for a concrete release (e.g. `release-checklist-v6.2.0.md`), fill all fields, attach evidence links, and mark each line item `PASS`/`FAIL`.

GitHub Actions are disabled. Record CircleCI jobs and the exact candidate SHA.
The prepared `release-validation` lane builds and verifies artifacts; it does
not publish them. Protected package promotion, signed provenance and release
asset upload remain pending in #11931. A build-only success cannot satisfy a
publish checkpoint. See the [migration workflow map](ci-workflow-map.md).

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
| Architecture boundaries and import policy | Architecture Owner | PR diff + architecture test output | CircleCI `arch-tests`, `lint-arch`; RULES §1.4/§4.4 | **PASS** if architecture + import-linter jobs green and no new boundary violations. **FAIL** otherwise. |
| Runtime compatibility (Codex/Junie mirrors and runtime guardrails) | Runtime Owner | Runtime-surface diff (`.codex/**`, `.junie/**`, `.devin/**`, `docs/00-project/ai/**`) | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` | **PASS** if runtime-source updates are synced to mirrors when required and mirror drift is documented. **FAIL** if unsynced runtime behavior exists. |
| Data quality policy readiness (DQ thresholds/hash/medallion) | Data Quality Owner | DQ configs/tests + policy evidence | CircleCI `dq-consistency`, `schema-governance`, `semantic-governance`; RULES §2.4/§2.8 | **PASS** if DQ checks green and the release scope validates the active threshold surface explicitly (`configs/base/quality.yaml` currently hard-fail 25%; contract/runtime fallbacks currently hard-fail 20%). **FAIL** on any blocking DQ gate. |
| Documentation governance readiness | Docs Owner | Updated docs set + links matrix | CircleCI `docs-governance`, `skills-consistency`; RULES §6 | **PASS** if docs governance jobs green and changed contracts/behavior are documented. **FAIL** if docs gate fails or contract docs missing. |
| Type/lint/test baseline | QA Owner | CI run for branch head | CircleCI `test-fast`, `test-integration`, `mypy`, `lint-ruff` | **PASS** if required CI checks are green on release candidate SHA. **FAIL** otherwise. |
| Security & secret hygiene | Security Owner | Security scan outputs + VCR sanitization report | CircleCI `security-scans`, `compiled-artifacts` | **PASS** if no blocking HIGH/CRITICAL findings for release policy and no secret leaks. **FAIL** otherwise. |

---

## 2) Release

| Checkpoint | Owner | Input artifact | Quality gate / policy workflow | Done criteria (PASS / FAIL) |
|---|---|---|---|---|
| Version and changelog freeze | Release Manager | `pyproject.toml`, `CHANGELOG.md`, release notes draft | RULES release/deprecation governance | **PASS** if version/tag/changelog aligned to same `v6.x.y` and approved. **FAIL** on mismatch. |
| Tag creation and signed release record | Release Manager | Git tag + tag annotation | CircleCI `release-validation` plus release-manager evidence | **PASS** if annotated tag created for approved SHA and the validated artifact identity matches that exact approved SHA. **FAIL** if wrong SHA/tag metadata. |
| Build artifacts production (wheel/sdist) | Release Engineer | CI artifacts from release run | CircleCI `release-validation` plus release-manager evidence | **PASS** if wheel+sdist build succeeds and artifacts attached to release run. **FAIL** on missing/failed artifacts. |
| Publish and provenance | Release Engineer | Publish logs, package registry record | Protected promotion (not yet accepted; #11931) | **PASS** if publish steps complete and provenance/identity checks pass per workflow output. **FAIL** otherwise. |
| Runtime compatibility confirmation for released assets | Runtime Owner | Install/run smoke evidence for released package | CircleCI `release-install`, release tests and local smoke notes | **PASS** if package install and CLI/runtime smoke pass for release artifact. **FAIL** on runtime regressions. |

---

## 3) Post-release

| Checkpoint | Owner | Input artifact | Quality gate / policy workflow | Done criteria (PASS / FAIL) |
|---|---|---|---|---|
| Post-release regression watch (24–48h) | QA Owner | First post-release CI window | CircleCI test lanes and the retained local-only contract campaign | **PASS** if no critical regressions in first monitoring window. **FAIL** if production-blocking regression found. |
| Contract and schema drift watch | Data Contract Owner | Drift reports, governance checks | CircleCI `schema-governance`, `semantic-governance`, `provider-contract-drift` | **PASS** if no unapproved contract/schema drift introduced by release. **FAIL** if drift gate breaks. |
| Documentation and migration follow-up | Docs Owner | Published release notes + migration notes | CircleCI `docs-governance`; RULES contract/versioning policy | **PASS** if release notes and migration notes published and linked from canonical docs. **FAIL** if migration guidance missing for breaking/behavior changes. |
| Quality debt and backlog capture | Architecture Owner | Follow-up issues/ADR notes | Canonical local debt audits and architecture policy docs; disabled automation stays disabled | **PASS** if actionable follow-ups captured with owners/dates. **FAIL** if known release debt has no tracked issue. |
| Final release sign-off | Release Manager | Completed checklist + evidence package | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` | **PASS** if all mandatory checks are PASS (or approved waiver recorded). **FAIL** if unresolved mandatory FAIL exists. |

---

## Mandatory v6.x check bundle

Use this block as a hard checklist before sign-off:

- [ ] **Architecture**: CircleCI `arch-tests` + `lint-arch` green.
- [ ] **Data quality**: DQ/schema/contract gates green for touched pipelines/entities.
- [ ] **Documentation**: docs governance and mirror consistency checks green.
- [ ] **Runtime compatibility**: runtime source + mirrors consistency verified; release artifact smoke verified.

If any mandatory item is not green, release decision = **FAIL** unless explicit waiver is approved and documented.

---

## Evidence to attach

Attach these links in the concrete release checklist/PR:

1. **CI run links**
   - CircleCI test job URLs and exact source SHA
   - CircleCI `mypy` job URL
   - CircleCI `arch-tests` / `lint-arch` job URLs
   - CircleCI `docs-governance` job URL
   - CircleCI schema/semantic governance job URLs
   - CircleCI `release-validation` URL plus separately approved publication receipt
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
