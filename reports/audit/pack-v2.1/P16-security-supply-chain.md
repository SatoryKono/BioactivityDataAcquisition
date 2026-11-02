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
- **E2 STATIC** (CURRENT): `scripts/engineering/qa/vcr/check_vcr_secrets.py` - Evidence of VCR cassettes secret scrubbing; `_StrictCassetteLoader(yaml.SafeLoader)`.
- **E2 STATIC** (CURRENT): `tests/architecture/test_antipatterns.py` - Evidence of `detect-secrets` running with a baseline.
- **E2 STATIC** (CURRENT): `uv.lock`, `pyproject.toml` - Evidence of dependency constraints and pinned versions.
- **E2 STATIC** (CURRENT): `rg 'yaml\.load' src tests scripts` — zero hits under `src/`; remaining call sites use `SafeLoader` subclasses or `yaml.BaseLoader` (no default/`UnsafeLoader`).

## D. Findings Register
- **finding_id**: `pack-v2.1/P16-AREA-001`
- **root_cause_id**: `yaml-load-api-surface`
- **owner_prompt**: `P16`
- **concern**: Residual use of the `yaml.load(..., Loader=...)` API instead of the `yaml.safe_load` alias.
- **severity**: `P3`
- **confidence**: `high`
- **status**: `DISPROVED` (as unsafe/RCE deserialization); residual style note only
- **expected**: YAML parsing must not allow arbitrary Python object construction from untrusted documents.
- **actual**: All repository `yaml.load` call sites pass an explicit safe loader:
  - `scripts/engineering/qa/vcr/check_vcr_secrets.py:175` → `Loader=_StrictCassetteLoader` where `_StrictCassetteLoader(yaml.SafeLoader)`
  - `tests/architecture/test_pr_gate_complete.py:298` → `Loader=_UniqueKeyLoader` where `_UniqueKeyLoader(yaml.SafeLoader)`
  - `tests/architecture/test_coderabbit_config.py:50,79` → same `_UniqueKeyLoader(yaml.SafeLoader)`
  - `tests/architecture/test_docs_build_site_router.py:57` → `Loader=yaml.BaseLoader` (no custom constructors / no Python object tags)
  - No `yaml.load` under `src/`
- **evidence_ids**: `E2 STATIC` (grep + class bases)
- **attempted_disproof**: Confirmed loader inheritance/`BaseLoader` on every hit; default `Loader` / `UnsafeLoader` absent. Initial P1 RCE framing is therefore false.
- **exceptions_checked**: Custom loaders exist specifically to reject duplicate keys while remaining on `SafeLoader`.
- **impact**: No demonstrated arbitrary-code-execution path from these call sites. Residual risk is limited to future edits that drop the explicit `Loader=` argument.
- **root cause**: Historical preference for explicit `Loader=` with SafeLoader subclasses rather than the `safe_load` alias.
- **recommendation**: Optional hygiene — prefer `yaml.safe_load` / document that custom loaders MUST subclass `yaml.SafeLoader`; keep CI/grep guard against bare `yaml.load(` without `Loader=`.
- **scope / non-goals**: No mandatory mass rewrite; do not treat SafeLoader subclasses as vulnerabilities.
- **acceptance criteria**: N/A for security closeout; optional lint if product owners want API uniformity.
- **verification command/test**: `rg -n 'yaml\.load\(' src tests scripts` and confirm each hit passes `SafeLoader`/`BaseLoader`.
- **dependencies**: None.
- **related_findings**: None.

## E. Quantitative Scorecard
- **Score**: 5 (Mature controls + signed supply chain + no confirmed in-repo deserialization RCE)
- **Rationale**: Robust VCR secret scrubbing, protected subprocess execution (`subprocess_boundary.py`), CI security scans (`detect-secrets`, `bandit`, `gitleaks`, `osv-scanner`/`pip-audit`), Cosign/Sigstore image signing. The only `yaml.load` hits are SafeLoader/BaseLoader-bound and outside `src/`.

## F. Cross-cutting/root-cause clusters
- **Cluster 1**: YAML API surface hygiene (style-only; SafeLoader/BaseLoader already enforced).

## G. Prioritized roadmap P0→P3
1. **P3 (optional)**: Prefer `yaml.safe_load` alias or document SafeLoader subclass invariant for custom loaders.

## H. Verification Matrix
- **Secrets in code**: `detect-secrets` and `gitleaks` in CI (Verified).
- **.env governance**: `.env` is properly excluded via `.gitignore` and handled safely in scripts (Verified).
- **GitHub Actions**: Least privilege observed (e.g. `permissions: contents: read`), hashes used for actions (Verified).
- **Dependencies**: `pip-audit` and `osv-scanner` in CI, strict `uv.lock` pinning (Verified).
- **Unsafe parsing**: Bare/`UnsafeLoader` `yaml.load` **not** found; XML uses `defusedxml` (Verified).
- **Subprocess injection**: Handled via `subprocess_boundary.py` enforcing `shell=False` (Verified).

## I. NOT_VERIFIABLE and missing evidence
- External cloud provider configurations (e.g. AWS IAM, Neo4j production access rules) are out of the repository's scope and cannot be verified via static code analysis.
- Live CI execution history / historical secret-scan hit rates were not re-run as E3 in this pass (`NOT_VERIFIABLE` for runtime cloud).

## J. Self-check
- All claims are supported by E2 STATIC evidence.
- Statuses distinguish DISPROVED security claims from optional style hygiene.
- No silent softening of real gaps; the P1 RCE claim was retracted after loader-base verification.

## K. Verdict
The repository exhibits a mature security and supply chain posture: subprocess boundaries, CI secret/dependency scanners, and signed Docker provenance. No confirmed in-repo unsafe YAML deserialization finding remains after loader inheritance review.

## Required Matrices

### Threat-Surface Map
- **Local `.env`**: Machine-local configs potentially containing credentials. Handled via `.gitignore`.
- **CI Secrets**: GitHub Actions secrets. Guarded by `detect-secrets` and `gitleaks`.
- **HTTP Communications**: Downstream scientific APIs. Scrubbed in VCR via `check_vcr_secrets.py`.
- **Subprocesses**: Local OS execution. Governed by `subprocess_boundary.py` (SEC-001).
- **Deserialization**: XML (`defusedxml`), YAML (SafeLoader/BaseLoader at all `yaml.load` sites; none in `src/`), JSON (`json.loads`).

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
# [pack-v2.1/P16] yaml-load-api-surface (optional hygiene)

**Provenance:**
- audit_id: pack-v2.1/P16
- audited_sha: ddbb7a0ee687365258bc407110e38601c4c3b765
- root_cause_id: yaml-load-api-surface
- source_finding_ids: pack-v2.1/P16-AREA-001
- severity: P3
- confidence: high
- status: DISPROVED as unsafe deserialization; optional style follow-up only

**Problem:**
Call sites still use `yaml.load(..., Loader=SafeLoaderSubclass|BaseLoader)` rather than the `yaml.safe_load` alias. Initial audit framing as P1 RCE was incorrect.

**Evidence:**
- `scripts/engineering/qa/vcr/check_vcr_secrets.py:72,175` — `_StrictCassetteLoader(yaml.SafeLoader)`
- `tests/architecture/test_docs_build_site_router.py:57` — `yaml.BaseLoader`
- `tests/architecture/test_pr_gate_complete.py:266,298` — `_UniqueKeyLoader(yaml.SafeLoader)`
- `tests/architecture/test_coderabbit_config.py:27,50` — `_UniqueKeyLoader(yaml.SafeLoader)`
- `rg 'yaml\.load' src` → empty

**Expected vs actual:**
Unsafe/`default` Loader must not appear. Actual loaders are SafeLoader subclasses or BaseLoader.

**Impact:**
No current RCE path from these sites. Residual only if a future edit drops `Loader=`.

**Scope / non-goals:**
Do not mass-rewrite SafeLoader subclasses as “vulnerabilities.”

**Architecture constraints:**
Duplicate-key rejection loaders must keep subclassing `yaml.SafeLoader`.

**Implementation outline (optional):**
Document the SafeLoader invariant; optional lint against bare `yaml.load(`.

**Acceptance criteria:**
N/A for security closeout.

**Verification commands/tests:**
`rg -n 'yaml\.load\(' src tests scripts`

**Dependencies:**
None.

**Rollback/risk:**
N/A (docs/hygiene only).
```
