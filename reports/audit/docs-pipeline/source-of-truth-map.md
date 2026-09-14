# Source of truth map (docs-pipeline)

| Surface | Source of truth | Generator | Validator | Tracked artifact? | Publish |
| --- | --- | --- | --- | --- | --- |
| MkDocs config / nav | `mkdocs.yml` | n/a | `check-links` nav classification; `test_mkdocs_nav_references_existing_markdown_files` | yes | build only |
| Unified docs CLI | `scripts/docs/__main__.py` | n/a | unit dispatch tests | yes | n/a |
| Verify chain | `scripts/docs/checks/verify.py` | n/a | docs.yml `python -m scripts.docs verify` | yes | n/a |
| Cleanup inventory | git-tracked docs + `configs/quality/generated_artifact_routing.yaml` | `generate-cleanup-inventory --update` | `--check` in verify + `test_documentation_cleanup_inventory_check_passes` | yes (`docs/reports/generated/documentation-cleanup-inventory.*`) | repo-only |
| Passports | pipeline/workflow facts | `scripts.docs passports` | `passports check` in docs-governance | yes | mixed |
| ADR registry | `docs/02-architecture/decisions/` | `scripts/generate_adr_registry.py` | architecture count/latest test; **no verify --check** | yes, **published nav** | MkDocs nav |
| Normalization matrix | schemas / normalization profiles | `generate-pipeline-normalization-matrix` | `--check` in provider-contract-drift.yml only | yes | repo-only generated |
| API landing pages | curated markdown under `docs/04-reference/api/` | none (not autogen) | `test_api_reference_public_facades.py` | yes | MkDocs |
| Live API objects | `src/` via mkdocstrings at build | mkdocs build | strict build | no (HTML ignored) | local/CI HTML |
| Site HTML | mkdocs.yml + docs | `mkdocs build` / `build-site` | `--strict` in verify | no (`site/`, `docs/site/` gitignored) | unpublished |
| Diagrams | `.mmd`/`.mermaid` | `docs/.../render.sh` | mermaid jobs path-filtered | svg tracked; png policy split | MkDocs images |
| KPI weekly | n/a | `check-kpi` | keep-disabled workflow | CI artifact if enabled | n/a |
