# Source of truth map (docs-pipeline)

HEAD `32d77a51`. Проверено 2026-09-25.

| Surface | Source of truth | Generator | Validator | Tracked | Publish |
| --- | --- | --- | --- | --- | --- |
| Nav / site config | `mkdocs.yml` | n/a | `check-links`; strict mkdocs build | yes | build only, Pages off |
| Verify chain | `scripts/docs/checks/verify.py` | n/a | `docs.yml` `python -m scripts.docs verify` | yes | n/a |
| Cleanup inventory | tracked docs + routing yaml | `generate-cleanup-inventory` | `--check` inside verify | yes | repo-only |
| Normalization matrix | schemas / profiles | `generate-pipeline-normalization-matrix` | `--check` inside verify and provider-contract-drift.yml | yes | repo-only |
| Structural contract JSON | runtime structural policy | `export-matrix-structural-contract` | `--check` in tests.yml | yes | repo-only |
| Workbook xlsx | README calls it canonical | matrix sync/normalize scripts | tests.yml skip + exit 0 if missing | no, gitignored, absent | n/a |
| Dictionaries | routing says tracked curated | `build-matrix-dicts` | not in verify; no `--check` | no, gitignored, absent | n/a |
| Activity field matrix | code schemas | `generate-field-matrix` | `--check` exists; not in verify | no, ignored_local_output | n/a |
| API pages | curated `docs/04-reference/api/` | none | `test_api_reference_public_facades.py` | yes | MkDocs |
| Site HTML | mkdocs.yml `site_dir: docs/site` | `build-site` (strict default) / verify temp dir | strict build exit 0 this run | no, gitignored | unpublished |
| Passports | configs + src facts | `scripts.docs passports` | `passports check` in docs-governance | yes | repo |
| AI-surface drift | runtime policy | n/a | pytest in docs-governance; not a verify flag | n/a | n/a |
