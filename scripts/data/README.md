# scripts/data — Data Integrity

Data integrity, VCR policy enforcement, checksum/Delta utilities, and DQ baseline management.

## Unified Entry Point

```bash
python -m scripts.data --help
python -m scripts.data <command> [args...]
```

## Commands

| Command | Script | Description |
|---------|--------|-------------|
| `check-vcr-placement` | `check_root_vcr_cassettes.py` | Block VCR cassette anti-patterns |
| `check-vcr-naming` | `check_vcr_filename_policy.py` | Enforce VCR filename policy |
| `check-delta` | `check_delta_integrity.py` | Check Delta Lake integrity |
| `check-data-dir` | `validate_data_dir.py` | Validate data directory structure against allowlist |
| `vacuum` | `vacuum_delta.py` | Vacuum Delta Lake tables |
| `checksums` | `verify_checksums.py` | Generate/verify file checksums |
| `dq-baseline` | `dq_baseline_update.py` | Update DQ baseline metrics |
| `report-null-fields` | `extract_null_fields.py` | Extract null field statistics |
| `report-content-hash` | `generate_content_hash_comparison_report.py` | Generate content hash comparison report |
