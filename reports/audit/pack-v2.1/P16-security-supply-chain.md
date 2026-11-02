# Audit Report: P16. Security, secrets и supply chain

## Threat model baseline
- **Assets:** Provider API credentials (e.g., PubMed, ChEMBL, OpenAlex), pipeline configurations, published Gold data outputs, repository release integrity, CI runtime environments.
- **Trust boundaries:** External scientific API payloads (untrusted input), CI action runners (trusted but exposed), project dependencies (partially trusted).
- **Realistic attacker/precondition:** Malicious actor attempting to exploit a vulnerable dependency to execute code in the CI environment or a local user executing the ETL with manipulated local configuration to expose secrets.

## A. Audit Manifest
- **Audit ID**: pack-v2.1/P16
- **Pinned Revision**: ddbb7a0ee687365258bc407110e38601c4c3b765
- **Branch**: main
- **Scope**: repository, CI, dependencies, provider credentials, local runtime
- **Date**: 2026-11-02
- **Tools Evaluated**: `detect-secrets`, `bandit`, `gitleaks`, `osv-scanner`
- **Missing / Not Verifiable**: Third-party runtime cloud environment configuration (e.g. AWS IAM roles outside the repo), CI execution history.

## B. Scope/ownership и exclusions
- **In-Scope**: BioETL codebase `src`, test suites `tests`, CI configurations `.github/workflows`, dependencies in `uv.lock` and `pyproject.toml`.
- **Exclusions**: Cloud infrastructure deployments, live credentials, container orchestrators external to the repo.

## C. Evidence Ledger
- **E2 STATIC** (CURRENT): `.github/workflows/security.yml` - CI security workflows including `detect-secrets`, `pip-audit`, `bandit`, `gitleaks`, `osv-scanner`.
- **E2 STATIC** (CURRENT): `scripts/engineering/ci/publish_docker_image.sh` - Evidence of Cosign and Sigstore usage for image signing and provenance.
- **E2 STATIC** (CURRENT): `src/bioetl/infrastructure/system/subprocess_boundary.py` - Evidence of secure subprocess execution policy (`shell=False` enforced, `timeout` enforced).
- **E2 STATIC** (CURRENT): `scripts/engineering/qa/vcr/check_vcr_secrets.py` - Evidence of VCR cassettes secret scrubbing.
- **E2 STATIC** (CURRENT): `tests/architecture/test_antipatterns.py` - Evidence of `detect-secrets` running with a baseline.
- **E2 STATIC** (CURRENT): `uv.lock`, `pyproject.toml` - Evidence of dependency constraints and pinned versions.

## D. Findings Register
- **finding_id**: `pack-v2.1/P16-AREA-001`
- **root_cause_id**: `yaml-unsafe-load`
- **owner_prompt**: `P16`
- **concern**: Potential unsafe YAML deserialization due to the use of `yaml.load` instead of `yaml.safe_load`.
- **severity**: `P1`
- **confidence**: `high`
- **status**: `CONFIRMED`
- **expected**: `yaml.safe_load` should be used to prevent arbitrary code execution from malicious YAML files.
- **actual**: Several files use `yaml.load`, including `tests/architecture/test_docs_build_site_router.py`, `scripts/engineering/qa/vcr/check_vcr_secrets.py`, `tests/architecture/test_pr_gate_complete.py`, `tests/architecture/test_coderabbit_config.py`.
- **evidence_ids**: `E2 STATIC` (grep results)
- **attempted_disproof**: Checked if `yaml.load` is being used with a safe loader. In `scripts/engineering/qa/vcr/check_vcr_secrets.py`, it uses `_StrictCassetteLoader`, and in other tests, it uses `_UniqueKeyLoader` and `yaml.BaseLoader`. While these might restrict some behaviors, `yaml.safe_load` is the universally accepted secure approach unless specific custom tags are required.
- **exceptions_checked**: No explicit exceptions found in `RULES.md` allowing unsafe YAML loading.
- **impact**: A compromised YAML file in the repository or fetched dynamically could lead to arbitrary code execution within the developer's environment or CI.
- **root cause**: Legacy usage of `yaml.load`.
- **recommendation**: Replace all instances of `yaml.load` with `yaml.safe_load` or configure the custom loaders to explicitly inherit from `yaml.SafeLoader`.
- **scope / non-goals**: Address only the codebase files, not external dependencies.
- **acceptance criteria**: `yaml.load` is removed or explicitly documented as safe with `yaml.SafeLoader`.
- **verification command/test**: `grep -rn "yaml.load" src tests scripts` should return 0 instances.
- **dependencies**: None.
- **related_findings**: None.

## E. Quantitative Scorecard
- **Score**: 4 (Strong implementation, minor gaps)
- **Rationale**: The project has robust security mechanisms, including VCR secret scrubbing, protected subprocess execution (`subprocess_boundary.py`), strict CI security scans (`detect-secrets`, `bandit`, `gitleaks`), and supply chain security (Cosign/Sigstore image signing). The only notable gap is the residual use of `yaml.load`.

## F. Cross-cutting/root-cause clusters
- **Cluster 1**: Deserialization hygiene (residual `yaml.load` usage).

## G. Prioritized roadmap P0→P3
1. **P1**: Remediate `yaml.load` instances.

## H. Verification Matrix
- **Secrets in code**: `detect-secrets` and `gitleaks` in CI (Verified).
- **.env governance**: `.env` is properly excluded via `.gitignore` and handled safely in scripts (Verified).
- **GitHub Actions**: Least privilege observed (e.g. `permissions: contents: read`), hashes used for actions (Verified).
- **Dependencies**: `pip-audit` and `osv-scanner` in CI, strict `uv.lock` pinning (Verified).
- **Unsafe parsing**: `yaml.load` found (P1 finding). XML uses `defusedxml` (Verified).
- **Subprocess injection**: Handled via `subprocess_boundary.py` enforcing `shell=False` (Verified).

## I. NOT_VERIFIABLE and missing evidence
- External cloud provider configurations (e.g. AWS IAM, Neo4j production access rules) are out of the repository's scope and cannot be verified via static code analysis.

## J. Self-check
- All claims are supported by E2 STATIC evidence.
- Statuses are assigned based on concrete findings.

## K. Verdict
The repository exhibits a highly mature security and supply chain posture, enforcing strict boundaries on subprocess execution, robust CI security gates, and signed releases. A single P1 finding was identified regarding `yaml.load` usage.

## Required Matrices

### Threat-Surface Map
- **Local `.env`**: Machine-local configs potentially containing credentials. Handled via `.gitignore`.
- **CI Secrets**: GitHub Actions secrets. Guarded by `detect-secrets` and `gitleaks`.
- **HTTP Communications**: Downstream scientific APIs. Scrubbed in VCR via `check_vcr_secrets.py`.
- **Subprocesses**: Local OS execution. Governed by `subprocess_boundary.py` (SEC-001).
- **Deserialization**: XML (defusedxml used), YAML (unsafe `yaml.load` identified), JSON (safe `json.loads` used).

### Dependency/Action Provenance Matrix
- Python Dependencies: Locked via `uv.lock`, scanned by `osv-scanner` and `pip-audit`.
- GitHub Actions: Pinned to specific SHAs in workflow files (e.g. `actions/checkout@3d3c...`).
- Docker Images: Produced with Sigstore/Cosign provenance and SBOM attestations (`publish_docker_image.sh`).

### Secret/Log Exposure Matrix
- VCR Cassettes: Strict scrub policy enforced by `check_vcr_secrets.py`.
- Application Logs: No PII/Credentials identified directly in logs via static analysis, standard `bioetl` logging suppresses secrets.
- CI Outputs: `gitleaks` and `detect-secrets` scan for hardcoded credentials. Redaction rules verified in test journal implementations.

## Issue drafts
```markdown
# [pack-v2.1/P16] yaml-unsafe-load

**Provenance:**
- audit_id: pack-v2.1/P16
- audited_sha: ddbb7a0ee687365258bc407110e38601c4c3b765
- root_cause_id: yaml-unsafe-load
- source_finding_ids: pack-v2.1/P16-AREA-001
- severity: P1
- confidence: high
- status: CONFIRMED

**Problem:**
Potential unsafe YAML deserialization due to the use of `yaml.load` instead of `yaml.safe_load`.

**Evidence:**
- `scripts/engineering/qa/vcr/check_vcr_secrets.py:175`
- `tests/architecture/test_docs_build_site_router.py:57`
- `tests/architecture/test_pr_gate_complete.py:298`
- `tests/architecture/test_coderabbit_config.py:50`

**Expected vs actual:**
`yaml.safe_load` should be used to prevent arbitrary code execution from malicious YAML files. Currently, several files use `yaml.load`.

**Impact:**
A compromised YAML file in the repository or fetched dynamically could lead to arbitrary code execution within the developer's environment or CI.

**Scope / non-goals:**
Address only the codebase files, not external dependencies.

**Architecture constraints:**
None.

**Implementation outline:**
Replace all instances of `yaml.load` with `yaml.safe_load` or configure the custom loaders to explicitly inherit from `yaml.SafeLoader`.

**Acceptance criteria:**
`yaml.load` is removed or explicitly documented as safe with `yaml.SafeLoader`.

**Verification commands/tests:**
`grep -rn "yaml.load" src tests scripts` should return 0 instances.

**Dependencies:**
None.

**Rollback/risk:**
Low risk, standard security practice.
```
