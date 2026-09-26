# GitHub settings review

- Repository: `SatoryKono/BioactivityDataAcquisition`
- Discovered default branch: `main`
- Generated: `2026-09-10T16:27:36.452081+00:00`
- Git HEAD: `ad125412f467daf951794bd502510f1780ea4733`
- Overall: **drift**
- Mutation posture: read-only; this automation did not change GitHub state.

## Controls

| ID | Status | Risk | Owner | Evidence | Decision | Due |
| --- | --- | --- | --- | --- | --- | --- |
| GH-RULESET-001 | pass | high | Repository administrators | active rulesets: ['main'] | No action required. | 2026-10-10 |
| GH-ACTIONS-001 | pass | high | Security lane | sha_pinning_required=True | No action required. | 2026-09-24 |
| GH-ENV-001 | pass | high | Release engineering | missing=none; unprotected=none | No action required. | 2026-10-10 |
| GH-DEPENDABOT-001 | pass | high | Security lane | alerts=True; security_updates=True | No action required. | 2026-09-24 |
| GH-CODEQL-001 | pass | high | Security lane | .github/workflows/codeql.yml exists=True | No action required. | 2026-09-24 |
| GH-CODEQL-002 | pass | high | Security lane | state=not-configured; hosted=['active'] | No action required. | 2026-09-24 |
| GH-SECRET-001 | pass | high | Security lane | secret_scanning=enabled | No action required. | 2026-09-24 |
| GH-SECRET-002 | drift | high | Security lane | secret_scanning_validity_checks=disabled | Track remediation in existing issue #10310. | 2026-09-24 |
| GH-SECRET-003 | pass | medium | Security lane | secret_scanning_non_provider_patterns=disabled | No action required. | 2026-10-10 |
| GH-ACTIONS-002 | pass | high | Security lane | allowed_actions=selected; sha_pinning_required=True | No action required. | 2026-09-24 |
| GH-ACTIONS-003 | pass | high | Security lane | github_owned_allowed=True; verified_allowed=False; missing=none; extra=none | No action required. | 2026-09-24 |
| GH-ENV-002 | pass | medium | Release engineering | present=none | No action required. | 2026-09-24 |
| GH-CODEOWNERS-001 | pass | medium | BioETL Team | path=.github/CODEOWNERS | No action required. | 2026-10-10 |
| GH-MERGE-001 | pass | medium | Repository administrators | squash=True; merge_commit=False; rebase=False | No action required. | 2026-10-10 |
| GH-WIKI-001 | pass | low | BioETL Team | has_wiki=False | No action required. | 2026-10-10 |
| GH-INTAKE-001 | pass | medium | BioETL Team | forms=['bug_report.yml', 'feature_request.yml', 'retention_sensitive_cleanup.yml']; config_exists=True | No action required. | 2026-10-10 |
| GH-LABELS-001 | pass | medium | BioETL Team | missing=none | No action required. | 2026-10-10 |

## Workflow health sample

- Runs sampled: 100
- Conclusions: `{"cancelled": 13, "failure": 6, "in_progress": 4, "queued": 2, "success": 74, "waiting": 1}`

## Label inventory

- Total: 214
- Classification counts: `{"canonical": 34, "deprecated": 43, "retained": 137}`

| Label | Classification | Replacement | Description |
| --- | --- | --- | --- |
| [gh actions opt] | retained |  | GitHub Actions optimization work |
| __probe__ | deprecated |  | [deprecated until 2026-11-30] Retained for migration; do not use on new work. |
| adapters | retained |  |  |
| adr | retained |  |  |
| ADR-040 | retained |  |  |
| ai | retained |  |  |
| ai-runtime | retained |  |  |
| api-change | canonical |  | API contract or compatibility change |
| application | deprecated | layer:application | [deprecated until 2026-11-30] Use layer:application. |
| application-layer | deprecated | layer:application | [deprecated until 2026-11-30] Use layer:application. |
| architecture | retained |  |  |
| architecture-tests | retained |  |  |
| archive | retained |  |  |
| audit | retained |  |  |
| audit-tooling | retained |  |  |
| automated | canonical |  | Created or maintained by repository automation |
| automation | retained |  |  |
| backend | retained |  |  |
| behavior | retained |  |  |
| bootstrap | retained |  |  |
| boundaries | retained |  |  |
| BRC CNLD | deprecated |  | [deprecated until 2026-11-30] Retained for migration; do not use on new work. |
| breaking-change | canonical |  | Requires migration or config update |
| breaking-changes | deprecated | breaking-change | [deprecated until 2026-11-30] Use breaking-change. |
| bug | canonical |  | Something isn't working |
| cardinality | retained |  | autocreated by triage |
| chembl | retained |  |  |
| ci | deprecated | ci/cd | [deprecated until 2026-11-30] Use ci/cd. |
| ci-cd | deprecated | ci/cd | [deprecated until 2026-11-30] Use ci/cd. |
| ci/cd | canonical |  | GitHub Actions, workflows |
| cleanup | canonical |  |  |
| cli | retained |  |  |
| code-quality | retained |  |  |
| coderabbit | retained |  |  |
| codex | retained |  |  |
| compatibility | retained |  |  |
| completed | deprecated |  | [deprecated until 2026-11-30] Retained for migration; do not use on new work. |
| composite | retained |  | Composite pipeline |
| composition | retained |  | Composition / DI |
| concurrency | retained |  |  |
| config | canonical |  | Pipeline/filter/schema YAML configs |
| configs | deprecated | config | [deprecated until 2026-11-30] Use config. |
| configuration | deprecated | config | [deprecated until 2026-11-30] Use config. |
| contract | retained |  |  |
| contract-failure | canonical |  | Automated contract test failure requiring triage |
| contracts | retained |  |  |
| control-plane | retained |  | autocreated by triage |
| coordination | retained |  |  |
| core | retained |  |  |
| correctness | retained |  |  |
| coverage | retained |  |  |
| critical | deprecated | priority:critical | [deprecated until 2026-11-30] Use priority:critical. |
| dashboard | retained |  |  |
| dashboard-design | retained |  | autocreated by triage |
| dashboards | retained |  |  |
| Dashbord | deprecated |  | [deprecated until 2026-11-30] Retained for migration; do not use on new work. |
| data-lineage | retained |  | Data provenance and lineage tracking |
| data-quality | retained |  | DQ rules, validation, schemas |
| datasource | retained |  |  |
| ddd | retained |  |  |
| dead-code | retained |  |  |
| Debit | deprecated |  | [deprecated until 2026-11-30] Retained for migration; do not use on new work. |
| debt-scoring | retained |  |  |
| demo | retained |  |  |
| dependencies | canonical |  | Pull requests that update a dependency file |
| deployment | retained |  |  |
| determinism | retained |  |  |
| developer-experience | retained |  | Developer experience improvements |
| devin | retained |  |  |
| diagrams | retained |  |  |
| docker | retained |  |  |
| docs | deprecated | documentation | [deprecated until 2026-11-30] Use documentation. |
| docs-drift | retained |  | autocreated by triage |
| documentation | canonical |  | Improvements or additions to documentation |
| domain | retained |  |  |
| done | deprecated |  | [deprecated until 2026-11-30] Retained for migration; do not use on new work. |
| dq | retained |  | autocreated by triage |
| duplicate | retained |  | This issue or pull request already exists |
| duplication | retained |  |  |
| e2e | retained |  |  |
| enforcement | retained |  |  |
| enhancement | canonical |  | New feature or request |
| evidence | retained |  |  |
| export | retained |  |  |
| final | deprecated |  | [deprecated until 2026-11-30] Retained for migration; do not use on new work. |
| final-report | retained |  |  |
| full-audit | retained |  |  |
| gitignore | retained |  |  |
| gold | retained |  |  |
| golden | retained |  |  |
| good first issue | retained |  | Good for newcomers |
| governance | canonical |  | Governance / policy / registries |
| grafana | retained |  | autocreated by triage |
| guardrails | canonical |  |  |
| guides | retained |  |  |
| help wanted | retained |  | Extra attention is needed |
| hexagonal-architecture | retained |  |  |
| high-priority | deprecated | priority:high | [deprecated until 2026-11-30] Use priority:high. |
| high-risk | retained |  |  |
| Higiene | deprecated |  | [deprecated until 2026-11-30] Retained for migration; do not use on new work. |
| hotspot | retained |  |  |
| http | retained |  |  |
| hygiene | retained |  |  |
| imports | retained |  |  |
| infrastructure | retained |  | Infrastructure layer changes |
| interfaces | retained |  | Interfaces layer |
| invalid | retained |  | This doesn't seem right |
| javascript | retained |  | Pull requests that update javascript code |
| knowledge | retained |  |  |
| layer:application | canonical |  | Application layer |
| layer:composition | canonical |  | Composition layer |
| layer:domain | canonical |  | Domain layer |
| layer:infrastructure | canonical |  | Infrastructure layer |
| layer:interfaces | canonical |  | Interfaces / CLI layer |
| lifecycle | retained |  |  |
| linting | retained |  |  |
| loki | retained |  | autocreated by triage |
| low-risk | retained |  |  |
| mcp | retained |  |  |
| medium-priority | deprecated | priority:medium | [deprecated until 2026-11-30] Use priority:medium. |
| medium-risk | retained |  |  |
| memory-sync | retained |  |  |
| meta | retained |  |  |
| metrics | retained |  |  |
| monitoring | retained |  |  |
| naming | retained |  |  |
| neo4j | retained |  |  |
| observability | retained |  |  |
| operations | retained |  |  |
| optimization | retained |  |  |
| P0 | deprecated | priority:critical | [deprecated until 2026-11-30] Use priority:critical. |
| P1 | deprecated | priority:high | [deprecated until 2026-11-30] Use priority:high. |
| P2 | deprecated | priority:medium | [deprecated until 2026-11-30] Use priority:medium. |
| P3 | deprecated | priority:low | [deprecated until 2026-11-30] Use priority:low. |
| performance | retained |  | Speed, memory, optimization |
| phase-1 | retained |  |  |
| phase-2 | retained |  |  |
| phase-3 | retained |  |  |
| phase-4 | retained |  |  |
| phase-4-6 | retained |  |  |
| phase-5 | retained |  |  |
| phase-6 | retained |  |  |
| pipeline | retained |  |  |
| pipelines | retained |  |  |
| priority/P1 | deprecated | priority:high | [deprecated until 2026-11-30] Use priority:high. |
| priority/P2 | deprecated | priority:medium | [deprecated until 2026-11-30] Use priority:medium. |
| priority/P3 | deprecated | priority:low | [deprecated until 2026-11-30] Use priority:low. |
| priority/P4 | deprecated | priority:low | [deprecated until 2026-11-30] Use priority:low. |
| priority/P5 | deprecated | priority:low | [deprecated until 2026-11-30] Use priority:low. |
| priority/P6 | deprecated | priority:low | [deprecated until 2026-11-30] Use priority:low. |
| priority/P7 | deprecated | priority:low | [deprecated until 2026-11-30] Use priority:low. |
| priority/P8 | deprecated | priority:low | [deprecated until 2026-11-30] Use priority:low. |
| priority:critical | canonical |  | Must fix immediately |
| priority:high | canonical |  | Should fix soon |
| priority:low | canonical |  | Nice to have |
| priority:medium | canonical |  | Normal priority |
| priority:P0 | deprecated | priority:critical | [deprecated until 2026-11-30] Use priority:critical. |
| priority:P1 | deprecated | priority:high | [deprecated until 2026-11-30] Use priority:high. |
| priority:P2 | deprecated | priority:medium | [deprecated until 2026-11-30] Use priority:medium. |
| priority:P3 | deprecated | priority:low | [deprecated until 2026-11-30] Use priority:low. |
| process | retained |  |  |
| prometheus | retained |  |  |
| promql | retained |  | autocreated by triage |
| provider-health | retained |  | autocreated by triage |
| provider:chembl | canonical |  | ChEMBL pipeline |
| provider:crossref | canonical |  | CrossRef pipeline |
| provider:openalex | canonical |  | OpenAlex pipeline |
| provider:pubchem | canonical |  | PubChem pipeline |
| provider:pubmed | canonical |  | PubMed pipeline |
| provider:semantic-scholar | canonical |  | Semantic Scholar pipeline |
| provider:uniprot | canonical |  | UniProt pipeline |
| providers | retained |  |  |
| python:uv | retained |  | Pull requests that update python:uv code |
| quality | retained |  |  |
| quarantine | retained |  | autocreated by triage |
| question | retained |  | Further information is requested |
| refactor | canonical |  | Refactoring / cleanup |
| refactoring | deprecated | refactor | [deprecated until 2026-11-30] Use refactor. |
| release-blocker | retained |  |  |
| replay | retained |  |  |
| replay-safety | retained |  |  |
| reporting | retained |  |  |
| reproducibility | retained |  | Scientific reproducibility |
| requirements | retained |  |  |
| resource-management | retained |  |  |
| runbook | retained |  | autocreated by triage |
| runtime | retained |  | autocreated by triage |
| schema-evolution | retained |  | Schema versioning and evolution |
| scripts | retained |  |  |
| security | canonical |  |  |
| skills | retained |  |  |
| sonarqube | retained |  |  |
| stale | canonical |  |  |
| static-analysis | retained |  |  |
| synchronization | retained |  |  |
| tech debt | deprecated | technical-debt | [deprecated until 2026-11-30] Use technical-debt. |
| tech-debt | deprecated | technical-debt | [deprecated until 2026-11-30] Use technical-debt. |
| technical debt | deprecated | technical-debt | [deprecated until 2026-11-30] Use technical-debt. |
| technical-debt | canonical |  | Tech debt / refactor |
| test | deprecated | testing | [deprecated until 2026-11-30] Use testing. |
| test-coverage | retained |  |  |
| testing | canonical |  |  |
| tests | deprecated | testing | [deprecated until 2026-11-30] Use testing. |
| tooling | retained |  |  |
| tracing | retained |  | autocreated by triage |
| typing | retained |  |  |
| ux | retained |  | autocreated by triage |
| validation | retained |  |  |
| vcr | retained |  |  |
| vcr-record | retained |  |  |
| verification | retained |  |  |
| wontfix | retained |  | This will not be worked on |
| workflow | deprecated | ci/cd | [deprecated until 2026-11-30] Use ci/cd. |
| workflows | deprecated | ci/cd | [deprecated until 2026-11-30] Use ci/cd. |

## Escalation rule

The workflow never opens or edits issues. For any drift without an existing issue, the accountable owner copies the control ID, evidence, risk, decision, and due date into a manually created `governance` issue and links this report.
