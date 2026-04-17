# scripts/data — Compatibility Data Facade

Compatibility command router for data integrity, VCR policy enforcement,
checksum/Delta utilities, and DQ baseline management.

Canonical homes:
- operational data checks: `scripts/ops/data/`
- VCR governance checks: `scripts/engineering/qa/vcr/`
- DQ baseline maintenance: `scripts/engineering/baselines/`

Canonical replay/refresh policy for integration and E2E tests lives in
`configs/quality/integration_vcr_policy.yaml` and is explained in
`docs/03-guides/testing.md`.

## Unified Entry Point

```bash
python -m scripts.data --help
python -m scripts.data <command> [args...]
python -m scripts.ops.data --help
python -m scripts.engineering.qa.vcr --help
```

## Commands

| Command               | Script                                                    | Description                                         |
| --------------------- | --------------------------------------------------------- | --------------------------------------------------- |
| `check-vcr-placement` | `scripts/engineering/qa/vcr/check_root_vcr_cassettes.py`                | Block VCR cassette anti-patterns                    |
| `check-vcr-naming`    | `scripts/engineering/qa/vcr/check_vcr_filename_policy.py`               | Enforce VCR filename policy                         |
| `check-vcr-secrets`   | `scripts/engineering/qa/vcr/check_vcr_secrets.py`                       | Detect potential secret leaks in VCR cassettes      |
| `check-delta`         | `scripts/ops/data/check_delta_integrity.py`                   | Check Delta Lake integrity                          |
| `check-data-dir`      | `scripts/ops/data/validate_data_dir.py`                       | Validate data directory structure against allowlist |
| `vacuum`              | `scripts/ops/data/vacuum_delta.py`                            | Vacuum Delta Lake tables                            |
| `checksums`           | `scripts/ops/data/verify_checksums.py`                        | Generate/verify file checksums                      |
| `dq-baseline`         | `scripts/engineering/baselines/dq_baseline_update.py`                      | Update DQ baseline metrics                          |
| `report-null-fields`  | `scripts/ops/data/extract_null_fields.py`                     | Extract null field statistics                       |
| `report-content-hash` | `scripts/ops/data/generate_content_hash_comparison_report.py` | Generate content hash comparison report             |

## When to Use

| Command               | When                                                                                                 | Trigger                      |
| --------------------- | ---------------------------------------------------------------------------------------------------- | ---------------------------- |
| `check-vcr-placement` | After adding VCR cassettes; blocks cassettes placed outside `tests/fixtures/vcr/`                    | Pre-commit hook              |
| `check-vcr-naming`    | After adding/renaming VCR cassettes; enforces filename policy and extension rules                    | Pre-commit hook              |
| `check-vcr-secrets`   | Before commit/PR after recording cassettes; verifies keys/tokens/emails are redacted in YAML         | Pre-commit hook or manual    |
| `check-delta`         | When Delta Lake tables show unexpected behavior; verifies table structure and file consistency       | Manual, troubleshooting      |
| `check-data-dir`      | After adding files to `data/`; validates tracked files against size limits and allowlist             | CI gate or manual            |
| `vacuum`              | Weekly maintenance; cleans old Delta Lake files from Silver tables (`--retention-days`, `--dry-run`) | Weekly scheduled or manual   |
| `checksums`           | After DR recovery or data migration; verifies file checksums against committed baselines             | Manual, post-recovery        |
| `dq-baseline`         | After model changes or periodically; recalculates Data Quality baseline from historical runs         | Manual, periodic maintenance |
| `report-null-fields`  | When investigating data quality; extracts null-valued field statistics from CSV                      | Manual, data exploration     |
| `report-content-hash` | After hash algorithm changes; compares legacy vs current content hash results                        | Manual, validation           |

## VCR Governance Quick Path

For cassette work, the supported lightweight sequence is:

```bash
python -m scripts.data check-vcr-placement
python -m scripts.data check-vcr-naming
# run targeted pytest with --vcr-record=new_episodes
python -m scripts.data check-vcr-secrets
python -m scripts.engineering.qa report-vcr-metadata --check
```

Use explicit replay (`--vcr-record=none`) for ordinary local integration/E2E
runs and reserve `new_episodes` for targeted refresh only.
