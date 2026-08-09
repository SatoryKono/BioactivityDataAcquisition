# CodeRabbit Comprehensive Audit - Quick Start

## One-Line Command

```bash
./scripts/ops/run-coderabbit-comprehensive-audit.sh
```

## Prerequisites Check

```bash
# Check CodeRabbit CLI
coderabbit --version

# Check authentication
coderabbit auth status

# Check GitHub CLI (for issue creation)
gh auth status

# Check git status
git status
```

## Setup (if needed)

```bash
# Install CodeRabbit CLI
bash <(curl -s https://cli.coderabbit.ai/install.sh)

# Authenticate
export CODERABBIT_API_KEY=your_key_here
# OR
coderabbit auth login --api-key your_key_here

# Authenticate GitHub CLI
gh auth login
```

## What Happens

The script runs through 6 phases:

1. **Preflight** - Captures baseline SHA, runs quality checks
2. **Scope Validation** - Ensures each scope has ≤300 files
3. **Sequential Reviews** - Runs CodeRabbit on 9 scopes with rate limiting
4. **P0 Issues** - Creates immediate GitHub issues for critical findings
5. **Batch Accumulation** - Creates issue pack with P1 findings
6. **Closeout** - Generates final report and git tag

## Output Location

```
reports/quality/coderabbit/YYYYMMDD_HHMM/
├── baseline_sha.txt
├── main_sha.txt
├── preflight_file_counts.txt
├── progress.log
├── review_S00.log
├── review_S01.log
├── ...
├── ISSUE_PACK.md
└── FINAL.md
```

## Manual Steps After Script

1. **Review findings**: Open `ISSUE_PACK.md`
2. **Triage P1 findings**: Prioritize and categorize
3. **Publish batch issues**: Confirm and create GitHub issues
4. **Implement fixes**: One PR per issue
5. **Re-audit**: Run script again on fixed scopes
6. **Closeout**: Update `FINAL.md` and create git tag

## Troubleshooting

### Rate Limiting
```bash
# Wait and retry specific scope
coderabbit review --base=main --dir src/bioetl/domain --agent --light
```

### Skip Issue Creation
```bash
# Run without GitHub CLI to skip automatic issue creation
# Script will warn and continue
```

### Dry Run
```bash
# Comment out the actual review execution in the script
# to test the workflow without running CodeRabbit
```

## Related Documentation

- **Operator policy**: `docs/03-guides/coderabbit-audit-playbook.md`
- **Playbook**: `docs/03-guides/coderabbit-audit-playbook.md`
- **Config**: `.coderabbit.yaml`
