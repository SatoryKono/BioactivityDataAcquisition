# CodeRabbit Comprehensive Audit Skill

## Quick Start

### Using the Skill (Devin/Codex)
```
Invoke the coderabbit-audit skill to run comprehensive CodeRabbit review.
```

### Using the Shell Script
```bash
# From repository root
./scripts/ops/run-coderabbit-comprehensive-audit.sh
```

## Prerequisites

1. **CodeRabbit CLI**: Install from https://cli.coderabbit.ai/
   ```bash
   coderabbit --version  # Should be 0.7.x
   ```

2. **API Key**: Set environment variable or authenticate
   ```bash
   export CODERABBIT_API_KEY=your_key_here
   # OR
   coderabbit auth login --api-key your_key_here
   ```

3. **GitHub CLI** (for issue creation):
   ```bash
   gh auth login
   ```

4. **Clean git state**: No uncommitted changes

## What It Does

The hybrid approach audit:

1. **Phase 0**: Preflight & baseline capture
2. **Phase 1**: Scope matrix validation (≤300 files per scope)
3. **Phase 2**: Sequential CodeRabbit reviews on 9 scopes
4. **Phase 3**: Immediate P0/critical issue creation
5. **Phase 4**: Batch P1 findings accumulation
6. **Phase 5**: Batch P1 issue publication (after triage)
7. **Phase 6**: Closeout document and git tag

## Scope Matrix

| Scope | Paths | Focus |
|-------|-------|-------|
| S00 | `src/bioetl/domain/**` | Domain purity, no I/O |
| S01 | `src/bioetl/application/core/**` | Determinism, resource management |
| S02 | `src/bioetl/application/services/control_plane/**` | Idempotency, checkpoints |
| S03 | `src/bioetl/infrastructure/adapters/**` | HTTP resilience, timeouts |
| S04 | `src/bioetl/composition/**` | DI patterns, factories |
| S05 | `src/bioetl/interfaces/**` | Interface boundaries |
| S06 | `tests/architecture/**` | Architecture gate honesty |
| S07 | `configs/quality/**` | Debt governance |
| S08 | `docs/00-project/**`, `docs/02-architecture/decisions/**` | Documentation drift |

## Output Artifacts

All artifacts created under `reports/quality/coderabbit/YYYYMMDD_HHMM/`:

- `baseline_sha.txt` - Frozen baseline commit
- `main_sha.txt` - Main branch reference
- `preflight_file_counts.txt` - File count validation
- `progress.log` - Campaign progress tracking
- `review_*.log` - Per-scope CodeRabbit review logs
- `ISSUE_PACK.md` - Normalized findings table
- `FINAL.md` - Closeout document

## Manual Steps Required

The script automates the review execution, but some steps require manual intervention:

1. **P0 Issue Creation**: Script parses logs but actual issue creation may need manual review
2. **P1 Triage**: Review `ISSUE_PACK.md` and prioritize findings
3. **Batch Publication**: Confirm P1 findings before bulk issue creation
4. **Fix Implementation**: Manual implementation of fixes
5. **Re-audit**: Run script again on fixed scopes only

## Customization

### Modify Scope Matrix
Edit the `SCOPES` array in `run-coderabbit-comprehensive-audit.sh`:
```bash
declare -A SCOPES=(
    ["S00"]="src/bioetl/domain"
    # Add or modify scopes here
)
```

### Adjust Rate Limiting
Change the sleep duration in Phase 2:
```bash
sleep 30  # Adjust as needed
```

### Skip Issue Creation
Run without GitHub CLI to skip automatic issue creation:
```bash
# The script will warn and continue without gh
```

## Troubleshooting

### Rate Limiting
If CodeRabbit CLI hits rate limits:
- Wait and retry the specific scope
- Use `--agent --light` flags for retries
- Increase backoff time between scopes

### File Count Exceeded
If a scope has >300 files:
- Split the scope into smaller sub-scopes
- Update the `SCOPES` array accordingly

### Authentication Issues
If API key issues:
- Verify `CODERABBIT_API_KEY` is set
- Run `coderabbit auth status` to check
- Re-authenticate if needed

## Related Documentation

- **Playbook**: `docs/03-guides/coderabbit-audit-playbook.md`
- **Local Reviews**: `docs/03-guides/development/coderabbit-local-reviews.md`
- **Config**: `.coderabbit.yaml`
- **CI Workflow**: `.github/workflows/coderabbit.yml`

## Anti-Patterns

Avoid:
- One CLI run on entire monorepo (file cap / noisy)
- Opening issues for every trivial nit
- Treating CR as proof without tests
- Increasing tech-debt budgets to silence findings

## Support

For issues or questions:
1. Check the playbook documentation
2. Review existing audit artifacts in `reports/quality/coderabbit/`
3. Consult GitHub issues tagged with `coderabbit`