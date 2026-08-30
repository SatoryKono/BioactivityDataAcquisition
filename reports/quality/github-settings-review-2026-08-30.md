# GitHub settings review

- Repository: `SatoryKono/BioactivityDataAcquisition`
- Discovered default branch: `main`
- Generated: `2026-08-30T15:53:38.157131+00:00`
- Git HEAD: `4f817cdd916544823cc58e6c03b01150e7bebedf`
- Overall: **drift**
- Mutation posture: read-only; this automation did not change GitHub state.

## Controls

| ID | Status | Risk | Owner | Evidence | Decision | Due |
| --- | --- | --- | --- | --- | --- | --- |
| GH-RULESET-001 | drift | high | Repository administrators | active rulesets: none | Track remediation in existing issue #9800. | 2026-09-29 |
| GH-ACTIONS-001 | pass | high | Security lane | sha_pinning_required=True | No action required. | 2026-09-13 |
| GH-ENV-001 | drift | high | Release engineering | missing=none; unprotected=['staging'] | Track remediation in existing issue #9785. | 2026-09-29 |
| GH-DEPENDABOT-001 | pass | high | Security lane | alerts=True; security_updates=True | No action required. | 2026-09-13 |
| GH-CODEQL-001 | pass | high | Security lane | .github/workflows/codeql.yml exists=True | No action required. | 2026-09-13 |
| GH-SECRET-001 | pass | high | Security lane | secret_scanning=enabled | No action required. | 2026-09-13 |
| GH-CODEOWNERS-001 | pass | medium | BioETL Team | path=.github/CODEOWNERS | No action required. | 2026-09-29 |
| GH-MERGE-001 | pass | medium | Repository administrators | squash=True; merge_commit=False; rebase=False | No action required. | 2026-09-29 |
| GH-WIKI-001 | drift | low | BioETL Team | has_wiki=True | Track remediation in existing issue #9787. | 2026-09-29 |
| GH-INTAKE-001 | pass | medium | BioETL Team | forms=['bug_report.yml', 'feature_request.yml', 'retention_sensitive_cleanup.yml']; config_exists=True | No action required. | 2026-09-29 |
| GH-LABELS-001 | drift | medium | BioETL Team | missing=['api-change', 'automated', 'contract-failure'] | Track remediation in existing issue #9787. | 2026-09-29 |

## Workflow health sample

- Runs sampled: 100
- Conclusions: `{"cancelled": 51, "failure": 4, "in_progress": 15, "pending": 2, "queued": 13, "success": 15}`

## Label inventory

- Total: 210
- Classification counts: `{"canonical": 31, "deprecated": 43, "retained": 136}`

| Label | Classification | Replacement | Description |
| --- | --- | --- | --- |
| __probe__ | deprecated |  |  |
| adapters | retained |  |  |
| adr | retained |  |  |
| ADR-040 | retained |  |  |
| ai | retained |  |  |
| ai-runtime | retained |  |  |
| application | deprecated | layer:application | Application layer |
| application-layer | deprecated | layer:application |  |
| architecture | retained |  |  |
| architecture-tests | retained |  |  |
| archive | retained |  |  |
| audit | retained |  |  |
| audit-tooling | retained |  |  |
| automation | retained |  |  |
| backend | retained |  |  |
| behavior | retained |  |  |
| bootstrap | retained |  |  |
| boundaries | retained |  |  |
| BRC CNLD | deprecated |  |  |
| breaking-change | canonical |  | Requires migration or config update |
| breaking-changes | deprecated | breaking-change | Breaking changes management |
| bug | canonical |  | Something isn't working |
| cardinality | retained |  | autocreated by triage |
| chembl | retained |  |  |
| ci | deprecated | ci/cd |  |
| ci-cd | deprecated | ci/cd |  |
| ci/cd | canonical |  | GitHub Actions, workflows |
| cleanup | canonical |  |  |
| cli | retained |  |  |
| code-quality | retained |  |  |
| coderabbit | retained |  |  |
| codex | retained |  |  |
| compatibility | retained |  |  |
| completed | deprecated |  |  |
| composite | retained |  | Composite pipeline |
| composition | retained |  | Composition / DI |
| concurrency | retained |  |  |
| config | canonical |  | Pipeline/filter/schema YAML configs |
| configs | deprecated | config | Configuration changes |
| configuration | deprecated | config |  |
| contract | retained |  |  |
| contracts | retained |  |  |
| control-plane | retained |  | autocreated by triage |
| coordination | retained |  |  |
| core | retained |  |  |
| correctness | retained |  |  |
| coverage | retained |  |  |
| critical | deprecated | priority:critical |  |
| dashboard | retained |  |  |
| dashboard-design | retained |  | autocreated by triage |
| dashboards | retained |  |  |
| Dashbord | deprecated |  |  |
| data-lineage | retained |  | Data provenance and lineage tracking |
| data-quality | retained |  | DQ rules, validation, schemas |
| datasource | retained |  |  |
| ddd | retained |  |  |
| dead-code | retained |  |  |
| Debit | deprecated |  |  |
| debt-scoring | retained |  |  |
| demo | retained |  |  |
| dependencies | canonical |  | Pull requests that update a dependency file |
| deployment | retained |  |  |
| determinism | retained |  |  |
| developer-experience | retained |  | Developer experience improvements |
| devin | retained |  |  |
| diagrams | retained |  |  |
| docker | retained |  |  |
| docs | deprecated | documentation |  |
| docs-drift | retained |  | autocreated by triage |
| documentation | canonical |  | Improvements or additions to documentation |
| domain | retained |  |  |
| done | deprecated |  |  |
| dq | retained |  | autocreated by triage |
| duplicate | retained |  | This issue or pull request already exists |
| duplication | retained |  |  |
| e2e | retained |  |  |
| enforcement | retained |  |  |
| enhancement | canonical |  | New feature or request |
| evidence | retained |  |  |
| export | retained |  |  |
| final | deprecated |  |  |
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
| high-priority | deprecated | priority:high |  |
| high-risk | retained |  |  |
| Higiene | deprecated |  |  |
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
| medium-priority | deprecated | priority:medium |  |
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
| P0 | deprecated | priority:critical |  |
| P1 | deprecated | priority:high |  |
| P2 | deprecated | priority:medium |  |
| P3 | deprecated | priority:low |  |
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
| priority/P1 | deprecated | priority:high |  |
| priority/P2 | deprecated | priority:medium |  |
| priority/P3 | deprecated | priority:low |  |
| priority/P4 | deprecated | priority:low |  |
| priority/P5 | deprecated | priority:low |  |
| priority/P6 | deprecated | priority:low |  |
| priority/P7 | deprecated | priority:low |  |
| priority/P8 | deprecated | priority:low |  |
| priority:critical | canonical |  | Must fix immediately |
| priority:high | canonical |  | Should fix soon |
| priority:low | canonical |  | Nice to have |
| priority:medium | canonical |  | Normal priority |
| priority:P0 | deprecated | priority:critical |  |
| priority:P1 | deprecated | priority:high |  |
| priority:P2 | deprecated | priority:medium |  |
| priority:P3 | deprecated | priority:low |  |
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
| refactoring | deprecated | refactor | Code restructuring, no functional change |
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
| tech debt | deprecated | technical-debt |  |
| tech-debt | deprecated | technical-debt |  |
| technical debt | deprecated | technical-debt |  |
| technical-debt | canonical |  | Tech debt / refactor |
| test | deprecated | testing |  |
| test-coverage | retained |  |  |
| testing | canonical |  |  |
| tests | deprecated | testing |  |
| tooling | retained |  |  |
| tracing | retained |  | autocreated by triage |
| typing | retained |  |  |
| ux | retained |  | autocreated by triage |
| validation | retained |  |  |
| vcr | retained |  |  |
| vcr-record | retained |  |  |
| verification | retained |  |  |
| wontfix | retained |  | This will not be worked on |
| workflow | deprecated | ci/cd | autocreated by triage |
| workflows | deprecated | ci/cd |  |

## Escalation rule

The workflow never opens or edits issues. For any drift without an existing issue, the accountable owner copies the control ID, evidence, risk, decision, and due date into a manually created `governance` issue and links this report.
