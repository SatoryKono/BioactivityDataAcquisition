# BioETL Operational Runbooks

Runbooks for common operational scenarios in the BioETL pipeline system.

## Index

| Runbook | Description | When to Use |
|---------|-------------|-------------|
| [Pipeline Failure Recovery](pipeline-failure-recovery.md) | Recovering from failed pipeline runs | Pipeline exits with non-zero code |
| [VACUUM Procedures](vacuum-procedures.md) | Manual Delta Lake maintenance | Table optimization needed |
| [Checkpoint Debugging](checkpoint-debugging.md) | Troubleshooting checkpoint issues | Pipeline resumes incorrectly |
| [DQ Failure Investigation](dq-failure-investigation.md) | Data quality issue analysis | DQ threshold exceeded |

## Quick Reference

### Exit Codes

| Code | Meaning | Action |
|------|---------|--------|
| 0 | Success | None required |
| 1 | General error | Check logs, see [Pipeline Failure Recovery](pipeline-failure-recovery.md) |
| 2 | Invalid arguments | Check CLI arguments |
| 10 | Data quality hard threshold | See [DQ Failure Investigation](dq-failure-investigation.md) |
| 130 | SIGINT (Ctrl+C) | Graceful shutdown, check checkpoint |
| 143 | SIGTERM | Graceful shutdown, check checkpoint |

### Key Directories

```
data/
├── bronze/v1/{provider}/{entity}/{date}/   # Raw JSONL files
├── silver/{table_name}/                     # Delta Lake tables
├── gold/{table_name}/                       # Aggregated Delta tables
├── checkpoints/{provider}_{entity}.json    # Pipeline state
└── quarantine/{provider}/{entity}/         # Failed records
```

### Useful Commands

```bash
# Check pipeline status
bioetl status

# Resume from checkpoint
bioetl run --provider chembl --entity activity --resume

# Force full refresh
bioetl run --provider chembl --entity activity --full-refresh

# Dry run (no writes)
bioetl run --provider chembl --entity activity --dry-run
```

## Prerequisites

- Python 3.11+
- Access to `data/` directory
- Environment variables configured (see `.env.example`)
