# Audit Report: P16. Security, secrets и supply chain

## Threat model baseline
- **Assets:** Provider API credentials (e.g., PubMed, ChEMBL, OpenAlex), pipeline configurations, published Gold data outputs, repository release integrity, CI runtime environments.
- **Trust boundaries:** External scientific API payloads (untrusted input), CI action runners (trusted but exposed), project dependencies (partially trusted).
- **Realistic attacker/precondition:** Malicious actor attempting to exploit a vulnerable dependency to execute code in the CI environment or a local user executing the ETL with manipulated local configuration to expose secrets.

## A. Audit Manifest
- **Audit ID**: pack-v2.1/P16
- **Pinned Revision**: a06384063113094698e342b3f0e294f5ec338741
- **Branch**: `chore/audit-p16-security-7103150260510390917` (honesty tip; originally sampled from `main` @ `ddbb7a0ee687365258bc407110e38601c4c3b765`)
- **Scope**: repository, CI, dependencies, provider credentials, local runtime
- **Date**: 2026-11-02
- **Tools Evaluated**: `detect-secrets`, `bandit`, `gitleaks`, `osv-scanner`
- **Missing / Not Verifiable**: Third-party runtime cloud environment configuration (e.g. AWS IAM roles outside the repo), CI execution history.
- **Pin note**: Pinned Revision equals the tip on which local `rg` verification was re-run (below). A follow-up docs-only commit that only realigns these stamps does not change `yaml.load` call sites.

## B. Scope/ownership и exclusions
- **In-Scope**: BioETL codebase `src`, test suites `tests`, CI configurations `.github/workflows`, dependencies in `uv.lock` and `pyproject.toml`.
- **Exclusions**: Cloud infrastructure deployments, live credentials, container orchestrators external to the repo.

## C. Evidence Ledger
- **E2 STATIC** (CURRENT): `.github/workflows/security.yml` - CI security workflows including `detect-secrets`, `pip-audit`, `bandit`, `gitleaks`, `osv-scanner`.
- **E2 STATIC** (CURRENT): `scripts/engineering/ci/publish_docker_image.sh` - Evidence of Cosign and Sigstore usage for image signing and provenance.
- **E2 STATIC** (CURRENT): `src/bioetl/infrastructure/system/subprocess_boundary.py` — `shell=False` is hard-coded on `Popen` / `run_protected_command`. `timeout` is an optional caller argument (`float | None = None`); this audit does **not** claim timeouts are enforced for every call site (full caller coverage **NOT_VERIFIABLE**).
- **E2 STATIC** (CURRENT): `scripts/engineering/qa/vcr/check_vcr_secrets.py` — fail-closed **static secret-safety check** of already-written VCR cassettes (flags unredacted credential-shaped fields); it is **not** a scrubber / scrub-policy enforcer. `_StrictCassetteLoader(yaml.SafeLoader)` used for parsing. Live redaction writers elsewhere: **NOT_VERIFIABLE** in this pass (not re-traced).
- **E2 STATIC** (CURRENT): `tests/architecture/test_antipatterns.py` - Evidence of `detect-secrets` running with a baseline.
- **E2 STATIC** (CURRENT): `uv.lock`, `pyproject.toml` - Evidence of dependency constraints and pinned versions.
- **E2 STATIC** (CURRENT): `rg -n 'yaml\.load\(' src tests scripts` — scoped to **direct** `yaml.load(` only; result: **5 hits**, **0 under `src/`**. This `rg` does **not** assert Loader bases and does **not** cover `yaml.unsafe_load` / `full_load` / `load_all`, Loader class imports, or import aliases. Loader-base claims below come from **separate** file:line reads of those hits.

## D. Findings Register
- **finding_id**: `pack-v2.1/P16-AREA-001`
- **root_cause_id**: `yaml-load-api-surface`
- **owner_prompt**: `P16`
- **concern**: Residual use of the `yaml.load(..., Loader=...)` API instead of the `yaml.safe_load` alias.
- **severity**: `P3`
- **confidence**: `high`
- **status**: `DISPROVED` (as unsafe/RCE deserialization); residual style note only
- **expected**: YAML parsing must not allow arbitrary Python object construction from untrusted documents.
- **actual**:
  - **Scoped `rg` only** (`rg -n 'yaml\.load\(' src tests scripts`): 5 direct `yaml.load(` sites; 0 under `src/`. No whole-repo / other-API claim.
  - **Separate Loader-base file:line reads** (not implied by `rg`):
    - `scripts/engineering/qa/vcr/check_vcr_secrets.py:175` → `Loader=_StrictCassetteLoader`; class `:72` `_StrictCassetteLoader(yaml.SafeLoader)`
    - `tests/architecture/test_pr_gate_complete.py:298` → `Loader=_UniqueKeyLoader`; nested class `:266` `_UniqueKeyLoader(yaml.SafeLoader)`
    - `tests/architecture/test_coderabbit_config.py:50,79` → `Loader=_UniqueKeyLoader`; class `:27` `_UniqueKeyLoader(yaml.SafeLoader)`
    - `tests/architecture/test_docs_build_site_router.py:57` → `Loader=yaml.BaseLoader`
- **evidence_ids**: `E2 STATIC` (`rg` hit list + separate class/Loader reads)
- **attempted_disproof**: For each of the five `rg` hits, open-file inspection confirmed SafeLoader subclass or BaseLoader; default/`UnsafeLoader` absent at those sites. Initial P1 RCE framing is therefore false for this scoped set.
- **exceptions_checked**: Custom loaders exist specifically to reject duplicate keys while remaining on `SafeLoader`.
- **impact**: No demonstrated arbitrary-code-execution path from these call sites. Residual risk is limited to future edits that drop the explicit `Loader=` argument.
- **root cause**: Historical preference for explicit `Loader=` with SafeLoader subclasses rather than the `safe_load` alias.
- **recommendation**: Optional hygiene — prefer `yaml.safe_load` / document that custom loaders MUST subclass `yaml.SafeLoader`; keep CI/grep guard against bare `yaml.load(` without `Loader=`.
- **scope / non-goals**: No mandatory mass rewrite; do not treat SafeLoader subclasses as vulnerabilities.
- **acceptance criteria**: N/A for security closeout; optional lint if product owners want API uniformity.
- **verification command/test**: (1) `rg -n 'yaml\.load\(' src tests scripts` for the hit list; (2) separately open each hit and its Loader class definition to confirm SafeLoader/BaseLoader.
- **dependencies**: None.
- **related_findings**: None.

## E. Quantitative Scorecard
- **Score**: 5 (Mature controls + signed supply chain + no confirmed in-repo deserialization RCE)
- **Rationale**: VCR cassette secret-safety gate (`check_vcr_secrets.py`), subprocess `shell=False` boundary, CI security jobs **Configured**, Cosign/Sigstore provenance **Configured**. Scoped `rg` found 5 direct `yaml.load(` sites (0 under `src/`); separate file:line reads of those sites show SafeLoader/BaseLoader — not a whole-repo YAML API audit.

## F. Cross-cutting/root-cause clusters
- **Cluster 1**: YAML API surface hygiene (style-only; SafeLoader/BaseLoader already enforced).

## G. Prioritized roadmap P0→P3
1. **P3 (optional)**: Prefer `yaml.safe_load` alias or document SafeLoader subclass invariant for custom loaders.

## H. Verification Matrix
Statuses below distinguish **workflow/config presence** from **executed CI outcomes**. CI job history was **not** re-fetched in this pass.

- **Secrets in code**: `detect-secrets` and `gitleaks` jobs **Configured** in `.github/workflows/security.yml` (**E2 STATIC**). CI run results / baseline hit rates: **NOT_VERIFIABLE** (history not inspected).
- **.env governance**: `.env` / `.env.*` entries present in `.gitignore` (**E2 STATIC**). Live secret-manager posture: **NOT_VERIFIABLE**.
- **GitHub Actions**: Least-privilege/`permissions` and action SHA pins observed in workflow YAML (**E2 STATIC** / **Configured**). Successful green history of those jobs: **NOT_VERIFIABLE**.
- **Dependencies**: `uv.lock` pinning + `pip-audit` / `osv-scanner` jobs **Configured** in `security.yml` (**E2 STATIC**). Note: `osv-scanner` step uses `continue-on-error: true` (outcome gated elsewhere in workflow — config only here). Scanner exit codes from CI: **NOT_VERIFIABLE**.
- **Unsafe parsing (YAML)**:
  - **`rg` result (local E2)**: command `rg -n 'yaml\.load\(' src tests scripts`; revision `a06384063113094698e342b3f0e294f5ec338741` (= **Pinned Revision**); date `2026-11-02T21:39:12Z`; exit `0`; artifact: local stdout — **5 hits**, **0 under `src/`**. Does **not** prove Loader bases; does **not** cover `unsafe_load` / `full_load` / `load_all` / Loader imports / aliases.
  - **Separate Loader-base checks (local E2)**: open-file reads of those five call sites + class defs (`check_vcr_secrets.py:72/175`, `test_pr_gate_complete.py:266/298`, `test_coderabbit_config.py:27/50/79`, `test_docs_build_site_router.py:57`) → SafeLoader subclasses or `yaml.BaseLoader`.
- **Unsafe parsing (XML)**: PubMed paths import `defusedxml` (**E2 STATIC**); no full XML attack-suite re-run (**NOT_VERIFIABLE** as dynamic proof).
- **Subprocess injection**: `subprocess_boundary.py` hard-codes `shell=False` (**E2 STATIC**). Timeouts are caller-supplied (`timeout: float | None = None`); mandatory timeout coverage across callers **NOT_VERIFIABLE**. Runtime fuzz/red-team: **NOT_VERIFIABLE**.

### Checks run vs skipped (this honesty pass)
- **Run (local)**: `rg -n 'yaml\.load\(' src tests scripts` (exit 0); static reads of `.github/workflows/security.yml`, `.gitignore`, `subprocess_boundary.py`, PubMed `defusedxml` imports, VCR SafeLoader class bases.
- **Skipped / not run**: `detect-secrets`, `gitleaks`, `bandit`, `pip-audit`, `osv-scanner` (no local re-execution); GitHub Actions run history / artifacts for `security.yml` (not fetched); live cloud IAM / secret stores.
- **Runtime mirror-sync**: **N/A** — no edits under `.codex/**` / `.junie/**` / `.devin/**` in this PR.

## I. NOT_VERIFIABLE and missing evidence
- External cloud provider configurations (e.g. AWS IAM, Neo4j production access rules) are out of the repository's scope and cannot be verified via static code analysis.
- Live CI execution history / historical secret-scan hit rates were not re-run as E3 in this pass (`NOT_VERIFIABLE` for runtime CI outcomes). Presence of scanners in YAML must not be read as a green run.

## J. Self-check
- Claims use **Configured** / **E2 STATIC** / **Verified (local)** / **NOT_VERIFIABLE** without conflating workflow presence and CI results.
- Statuses distinguish DISPROVED security claims from optional style hygiene.
- No silent softening of real gaps; the P1 RCE claim was retracted after loader-base verification.

## K. Verdict
The repository exhibits a mature security and supply chain posture: subprocess boundaries, CI secret/dependency scanners, and signed Docker provenance. No confirmed in-repo unsafe YAML deserialization finding remains after loader inheritance review.

## Required Matrices

### Threat-Surface Map
- **Local `.env`**: Machine-local configs potentially containing credentials. Ignore rules in `.gitignore` (**E2 STATIC**).
- **CI Secrets**: GitHub Actions secrets. Scanner jobs **Configured** (`detect-secrets`, `gitleaks`); run outcomes **NOT_VERIFIABLE** here.
- **HTTP Communications**: Downstream scientific APIs. Cassette secret-safety **check** via `check_vcr_secrets.py` (**E2 STATIC**; not a scrub writer).
- **Subprocesses**: Local OS execution. `shell=False` in `subprocess_boundary.py` (**E2 STATIC**); timeout not claimed enforced globally.
- **Deserialization**: XML (`defusedxml` imports, **E2 STATIC**), YAML (scoped `rg`: 5 direct `yaml.load(` / 0 in `src/`; Loader bases from separate file:line reads), JSON (`json.loads`).

### Dependency/Action Provenance Matrix
- Python Dependencies: Locked via `uv.lock`; `osv-scanner` / `pip-audit` jobs **Configured** in CI YAML (run results **NOT_VERIFIABLE**).
- GitHub Actions: SHA pins present in workflow files (**E2 STATIC** / **Configured**).
- Docker Images: Cosign/Sigstore + SBOM steps present in `publish_docker_image.sh` (**E2 STATIC** / **Configured**); live publish evidence **NOT_VERIFIABLE**.

### Secret/Log Exposure Matrix
- VCR Cassettes: Secret-safety **static check** of tracked cassettes via `check_vcr_secrets.py` (**E2 STATIC**). Does not itself scrub; redaction writers not re-verified here (**NOT_VERIFIABLE**).
- Application Logs: No hardcoded credentials spotted in a narrow static skim (**E2 STATIC**); exhaustive log-path proof **NOT_VERIFIABLE**.
- CI Outputs: `gitleaks` / `detect-secrets` jobs **Configured** in `security.yml`; redaction/test-journal coverage is code-level (**E2 STATIC**), not a cited green CI artifact.

## Issue drafts
```markdown
# [pack-v2.1/P16] yaml-load-api-surface (optional hygiene)

**Provenance:**
- audit_id: pack-v2.1/P16
- audited_sha: a06384063113094698e342b3f0e294f5ec338741
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
