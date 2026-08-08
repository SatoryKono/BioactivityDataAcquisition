---
name: coderabbit-audit
description: Execute comprehensive CodeRabbit code review using hybrid approach (immediate P0 issues, batched P1 findings)
---

# CodeRabbit Comprehensive Audit

## Objective

Execute exhaustive CodeRabbit code review using hybrid approach: immediate P0/critical issues creation, batched P1/major findings publication, following BioETL audit playbook.

## Source Of Truth
- Root runtime contract: `../../../AGENTS.md`
- CodeRabbit playbook: `../../../docs/03-guides/coderabbit-audit-playbook.md`
- Local reviews guide: `../../../docs/03-guides/development/coderabbit-local-reviews.md`
- CodeRabbit config: `../../../.coderabbit.yaml`
- CI workflow: `../../../.github/workflows/coderabbit.yml`
- Memory policy: `../../../docs/00-project/ai/agents/guides/MEMORY_USAGE.md`

## Precedence (do not invert)
1. Code / domain contracts / config
2. Accepted ADRs + RULES
3. Architecture tests and quality gates
4. CodeRabbit findings (must map to evidence above)

**Conflict rule:** code wins. **Never** grow tech-debt budgets to silence CR findings.

## Prerequisites

1. **CodeRabbit CLI**: `coderabbit --version` (0.7.x recommended)
2. **API Key**: `CODERABBIT_API_KEY` environment variable or auth cache
3. **Clean git status**: No uncommitted changes in working directory
4. **Baseline**: Current `main` branch SHA frozen
5. **Output directory**: `reports/quality/coderabbit/YYYYMMDD/` created

## Workflow

### Phase 0: Preflight & Baseline

```bash
# Freeze baseline
export AUDIT_TS=$(date -u +%Y%m%d_%H%M)
export OUT=reports/quality/coderabbit/${AUDIT_TS}
mkdir -p "$OUT"

# Capture baseline state
git rev-parse HEAD > "$OUT/baseline_sha.txt"
git rev-parse main > "$OUT/main_sha.txt"

# Run baseline quality checks
pytest tests/architecture/ -q --tb=no > "$OUT/baseline_arch_tests.txt" 2>&1
python -m scripts.engineering.qa validate-technical-debt-audit > "$OUT/baseline_debt_audit.txt" 2>&1
```

### Phase 1: Scope Matrix Validation

```bash
# Count files per scope (ensure <300 files per scope)
echo "=== File Count Preflight ===" > "$OUT/preflight_file_counts.txt"
git ls-files 'src/bioetl/domain' | wc -l >> "$OUT/preflight_file_counts.txt"
git ls-files 'src/bioetl/application/core' | wc -l >> "$OUT/preflight_file_counts.txt"
git ls-files 'src/bioetl/application/services/control_plane' | wc -l >> "$OUT/preflight_file_counts.txt"
git ls-files 'src/bioetl/infrastructure/adapters' | wc -l >> "$OUT/preflight_file_counts.txt"
git ls-files 'src/bioetl/composition' | wc -l >> "$OUT/preflight_file_counts.txt"
git ls-files 'src/bioetl/interfaces' | wc -l >> "$OUT/preflight_file_counts.txt"
git ls-files 'tests/architecture' | wc -l >> "$OUT/preflight_file_counts.txt"
git ls-files 'configs/quality' | wc -l >> "$OUT/preflight_file_counts.txt"
git ls-files 'docs/00-project' 'docs/02-architecture/decisions' | wc -l >> "$OUT/preflight_file_counts.txt"
```

**If any scope >300 files, split further before proceeding.**

### Phase 2: Sequential Scope Reviews

Use this scope matrix (≤300 files each):

| Scope ID | Paths | Focus | Prompt theme |
|----------|------|-------|--------------|
| S00 | `src/bioetl/domain/**` | Pure domain, ports, aggregates | Domain purity, no I/O |
| S01 | `src/bioetl/application/core/**` | Batch/lifecycle hotspots | Determinism, resource management |
| S02 | `src/bioetl/application/services/control_plane/**` | Manifest/ledger/replay | Idempotency, checkpoint durability |
| S03 | `src/bioetl/infrastructure/adapters/**` | HTTP/resilience | Timeout, retry, rate limiting |
| S04 | `src/bioetl/composition/**` | DI-only, factories | Dependency injection patterns |
| S05 | `src/bioetl/interfaces/**` | Thin CLI/HTTP | Interface boundaries |
| S06 | `tests/architecture/**` | Gate honesty | Test coverage, architecture tests |
| S07 | `configs/quality/**` | Budgets, no growth | Debt governance |
| S08 | `docs/00-project/**`, `docs/02-architecture/decisions/**` | SSOT drift | Documentation accuracy |

**Execution loop:**

```bash
# For each scope in sequence
for scope in S00 S01 S02 S03 S04 S05 S06 S07 S08; do
  echo "=== Starting scope $scope at $(date -u +%Y%m%d_%H%M%S) ===" >> "$OUT/progress.log"
  
  # Run CodeRabbit review
  coderabbit review --base=main --plain \
    | tee "$OUT/review_${scope}.log"
  
  # Extract findings to NDJSON
  # (Parse log output and convert to structured format)
  
  # Rate limiting: wait between scopes
  sleep 30
  
  echo "=== Completed scope $scope at $(date -u +%Y%m%d_%H%M%S) ===" >> "$OUT/progress.log"
done
```

### Phase 3: Immediate P0 Issue Creation

**For each scope immediately after review:**

```bash
# Parse findings for critical/severity
# Extract P0/critical findings
# Create GitHub issues immediately (same-day requirement)

# Finding template for P0:
gh issue create \
  --title "[CR-P0] {scope}: {claim}" \
  --body "### CR-{SCOPE}-{NN}
- Severity: critical
- Path: {path}
- Claim: {claim}
- Evidence: {code/test/ADR reference}
- Scope: {scope_id}
- Audit timestamp: ${AUDIT_TS}
- Baseline SHA: $(cat $OUT/baseline_sha.txt)

### Acceptance
- {acceptance_criteria}

### Context
CodeRabbit comprehensive audit using hybrid approach.
See: reports/quality/coderabbit/${AUDIT_TS}/" \
  --label "quality,priority/P0,coderabbit" \
  --repo $(git config --get remote.origin.url | sed -E 's|git@github.com:|https://github.com/|' | sed -E 's|\.git$||' | sed -E 's|https://github.com/||')
```

### Phase 4: Batch P1 Findings Accumulation

**After all scopes complete:**

```bash
# Normalize all findings into single table
# Columns: id, severity, path, claim, scope, dupe_of, status

# De-dupe policy:
# 1. One open issue per residual path
# 2. Prefer earlier scopes for same path
# 3. Prefer higher severity, then lower issue number
# 4. Implement only canonical issues

# Create issue pack
cat > "$OUT/ISSUE_PACK.md" << 'EOF'
# CodeRabbit Comprehensive Audit — Issue Pack ${AUDIT_TS}

**Published:** $(date -u +%Y-%m-%d)
**Baseline SHA:** $(cat $OUT/baseline_sha.txt)
**Artifacts:** reports/quality/coderabbit/${AUDIT_TS}/

## Severity Summary

| Severity | Count |
| --- | ---: |
| critical | {count} |
| major | {count} |
| minor | {count} |
| trivial | {count} |
| **total** | **{total}** |

## Immediate P0 Issues

{list of P0 issues created in Phase 3}

## Batch P1 Findings

{normalized table of P1 findings for batch publication}

## De-dupe Policy

1. One open issue per residual path
2. Prefer earlier scopes for same path
3. Prefer higher severity, then lower issue number
4. Implement only canonical issues
5. No tech-debt budget growth

## Next Steps

1. Review and triage P1 findings
2. Publish batch P1 issues
3. Implement fixes (one_issue_one_pr)
4. Re-run CR on fixed scopes
5. Closeout with FINAL.md
EOF
```

### Phase 5: Batch P1 Issue Publication

```bash
# After triage, publish P1 issues in batch
# Use GitHub API or gh CLI for bulk creation

# Template for P1 issues:
gh issue create \
  --title "[CR-P1] {scope}: {claim}" \
  --body "### CR-{SCOPE}-{NN}
- Severity: major
- Path: {path}
- Claim: {claim}
- Evidence: {code/test/ADR reference}
- Scope: {scope_id}
- Audit timestamp: ${AUDIT_TS}
- Baseline SHA: $(cat $OUT/baseline_sha.txt)

### Acceptance
- {acceptance_criteria}

### Context
CodeRabbit comprehensive audit using hybrid approach.
Issue pack: reports/quality/coderabbit/${AUDIT_TS}/ISSUE_PACK.md" \
  --label "quality,priority/P1,coderabbit" \
  --repo $(git config --get remote.origin.url | sed -E 's|git@github.com:|https://github.com/|' | sed -E 's|\.git$||' | sed -E 's|https://github.com/||')
```

### Phase 6: Re-audit & Closeout

**After fixes implemented:**

```bash
# Re-run CR only on fixed scopes
for fixed_scope in ${FIXED_SCOPES}; do
  coderabbit review --base=main --plain \
    | tee "$OUT/review_${fixed_scope}_rerun.log"
done

# Create closeout document
cat > "$OUT/FINAL.md" << 'EOF'
# CodeRabbit Comprehensive Audit — Closeout ${AUDIT_TS}

**Completed:** $(date -u +%Y-%m-%d)
**Baseline SHA:** $(cat $OUT/baseline_sha.txt)
**Final SHA:** $(git rev-parse HEAD)

## Campaign Summary

| Metric | Value |
| --- | ---: |
| Tool version | $(coderabbit --version) |
| Scopes reviewed | {count} |
| Total findings | {total} |
| P0 critical | {count} |
| P1 major | {count} |
| P2 minor | {count} |
| Trivial | {count} |

## Issues Published

- P0 immediate: {count} issues
- P1 batch: {count} issues
- Total: {count} issues

## Closeout Checklist

- [ ] FINAL.md: tool version, SHA, scopes, severity counts
- [ ] De-dupe vs prior ARCH-CR / DOC-GOV / epic issues
- [ ] No quality budget growth
- [ ] Relevant gates green (arch / debt / types / docs)
- [ ] Secrets not committed
- [ ] Tag: audit/coderabbit-${AUDIT_TS}

## Related Artifacts

- Issue pack: reports/quality/coderabbit/${AUDIT_TS}/ISSUE_PACK.md
- Review logs: reports/quality/coderabbit/${AUDIT_TS}/review_*.log
- Progress: reports/quality/coderabbit/${AUDIT_TS}/progress.log
EOF

# Create git tag
git tag "audit/coderabbit-${AUDIT_TS}"
```

## Specialized Prompt Contracts

### Domain Layer (S00)
```
You are reviewing BioETL domain layer (hexagonal + DDD).

Focus on domain purity, no I/O, proper DDD patterns.
Check for:
- I/O violations (HTTP, DB, filesystem, env access)
- Infrastructure leakage in domain logic
- Missing invariants and domain rules
- Proper aggregate boundaries
- Port interface correctness

Do not propose increasing quality/debt budgets.
Ignore pure style nits unless they hide correctness risk.

Output for each finding:
1) severity (critical|major|minor|trivial)
2) path
3) claim (one sentence)
4) why it matters (invariant)
5) suggested fix class (code|test|config|docs)
6) acceptance check (command or test name)
```

### Infrastructure Adapters (S03)
```
You are reviewing BioETL infrastructure adapters.

Focus on external provider integration resilience.
Check for:
- Proper timeout configuration
- Retry/backoff logic with exponential backoff
- Pagination handling
- Rate limit compliance
- Schema drift detection
- Secret handling (no hardcoded credentials)
- Error mapping to domain errors
- Telemetry and observability

Do not propose increasing quality/debt budgets.
Ignore pure style nits unless they hide correctness risk.

Output for each finding:
1) severity (critical|major|minor|trivial)
2) path
3) claim (one sentence)
4) why it matters (invariant)
5) suggested fix class (code|test|config|docs)
6) acceptance check (command or test name)
```

### Pipelines (S01, S02)
```
You are reviewing BioETL ETL pipelines.

Focus on determinism, idempotency, and data integrity.
Check for:
- Reproducibility (stable ordering, deterministic outputs)
- Proper units and schema handling
- Data lineage tracking
- Stable ordering for idempotent operations
- Atomic writes (tmp → os.replace pattern)
- Checkpoint durability
- Idempotency contracts
- Quarantine handling for failed records

Do not propose increasing quality/debt budgets.
Ignore pure style nits unless they hide correctness risk.

Output for each finding:
1) severity (critical|major|minor|trivial)
2) path
3) claim (one sentence)
4) why it matters (invariant)
5) suggested fix class (code|test|config|docs)
6) acceptance check (command or test name)
```

## Anti-Patterns (Avoid)

- One CLI run on entire monorepo (hits file cap / noisy)
- Opening issues for every trivial nit
- Treating CR as proof of runtime behavior without tests
- Auditing types without basedpyright snapshot
- Forcing Grafana/Scenes as required for Local-Only
- Re-opening closed architecture epics without regression evidence
- Increasing tech-debt budgets to silence findings

## Rate Limiting & Backoff

- Sequential scopes only (no parallel runs)
- 30-second backoff between scopes
- If rate_limit hit: wait and retry specific scope
- Use `--agent --light` flags for retries if needed

## Artifacts Location

All artifacts under `reports/quality/coderabbit/YYYYMMDD/`:
- `baseline_sha.txt` - Frozen baseline commit
- `main_sha.txt` - Main branch reference
- `preflight_file_counts.txt` - File count validation
- `progress.log` - Campaign progress tracking
- `review_*.log` - Per-scope review logs
- `ISSUE_PACK.md` - Normalized findings table
- `FINAL.md` - Closeout document

## Notes

- Treat this skill file as canonical for runtime trigger
- Use memory plus repo search for related architecture tests, ADRs, docs
- Adapt command examples to active shell and toolchain
- Report findings with failing tests/checks and actionable next fixes
- Follow `.coderabbit.yaml` configuration (profile: assertive)
- CI workflow: `.github/workflows/coderabbit.yml` for trusted execution