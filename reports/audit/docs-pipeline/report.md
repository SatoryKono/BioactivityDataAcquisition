# Docs pipeline audit

- domain: `docs-pipeline`
- prompt_id: `prompt.audit.docs-pipeline`
- MODE: audit / AUDIT_MODE: full
- LANGUAGE: ru
- SCOPE: `scripts/docs/` `mkdocs.yml` `docs/`
- checked_at_utc: `2026-09-14T06:13:47Z`
- surface_score: **2** (pipeline воспроизводим; часть semantic/--check ворот ручные или вне verify)
- blocked: false

## Executive summary

Каноническая цепочка **generate → validate → build** есть: unified CLI
`python -m scripts.docs`, `verify` (links, drift, docstrings, cleanup-inventory,
strict mkdocs), CI owner `.github/workflows/docs.yml` (вызывается из
`pr-required.yml` как `docs-governance`). Публикации GitHub Pages нет
(`site_url` опущен; policy это фиксирует). Секретов в generated pages/logs не
найдено.

`python -m scripts.docs generate-cleanup-inventory --check` на текущем дереве
завершился **exit 0** (inventory synchronized). Exit 0 генератора **не**
считался доказательством семантической корректности остальных derived docs.

Оценка 2, не 3: двойной `site_dir`; hidden precondition extra `docs` на Windows;
ADR registry с wall-clock вне verify; matrix `--check` вне docs.yml; disabled
package-family шаг при string-only тесте.

P0/P1 нет.

## Pipeline map

| Step | Entrypoint | Inputs | Outputs | Local vs CI | Failure |
| --- | --- | --- | --- | --- | --- |
| generate inventory | `python -m scripts.docs generate-cleanup-inventory` | git ls-files, routing YAML | `docs/reports/generated/documentation-cleanup-inventory.{json,md}` | local `--update`; CI `--check` via verify | exit 1 on drift |
| generate passports | `python -m scripts.docs passports check` | pipeline/workflow facts | tracked passport projections | CI docs-governance (не в verify) | exit 1 on drift |
| generate ADR registry | `python scripts/generate_adr_registry.py` | `docs/02-architecture/decisions/` | `docs/02-architecture/adr-registry/**` | manual; не в verify | timestamps always dirty |
| generate matrices | `python -m scripts.docs generate-pipeline-normalization-matrix --check` | schemas/profiles | `docs/reports/generated/pipeline_normalization_field_matrix/` | не в verify/docs.yml | --check unused by docs owner |
| validate links | `python -m scripts.docs check-links` | docs/, mkdocs.yml | optional `reports/docs-link-check-report.json` | CI validate-mkdocs + verify | exit 1 |
| validate drift | `python -m scripts.docs check-drift --ports --classes --runtime-mirrors --freshness --modules` | docs + runtime | stdout | verify | exit 1 |
| build | `mkdocs build --strict --clean` (verify tempfile) / `build-site` → `docs/site` | mkdocs.yml, docs/ | ignored HTML | CI validate-mkdocs uses verify | exit 1 |
| publish | none | n/a | n/a | GitHub Pages unpublished | n/a |

Toolchain: `uv --frozen --no-build`; Python 3.13 в docs.yml; extra `docs` в
pyproject (`mkdocs>=1.6,<2.0`, material, mkdocstrings, pymdown-extensions,
backrefs, **и неиспользуемый mermaid2**).

## Checks run

| Check | Result |
| --- | --- |
| `python -m scripts.docs generate-cleanup-inventory --check` | exit 0, `inventory is synchronized` @ 2026-09-14T06:13:47Z |
| `.venv-win` `import mkdocs` | exit 1, ModuleNotFoundError |
| inspection `mkdocs.yml`, `scripts/docs/__main__.py`, `verify.py`, `docs.yml` | completed |
| live GitHub Actions API state | skipped (`REQUIRE_GH_TRACKING=false`); inventory snapshot 2026-09-10 |
| full `mkdocs build --strict` | skipped (mkdocs not in `.venv-win`; extra docs not installed) |
| `--update` / publish / push | forbidden in audit mode |

## Findings (8 PROVEN, 0 P0/P1)

1. **DOCS-PIPE-001** P2 — dual site_dir (`site/` vs `docs/site/`).
2. **DOCS-PIPE-002** P2 — verify strict-build + Windows venv extra/docs path.
3. **DOCS-PIPE-003** P2 — ADR registry wall-clock, вне unified verify.
4. **DOCS-PIPE-004** P2 — normalization matrix `--check` вне docs.yml/verify.
5. **DOCS-PIPE-005** P2 — package-family `--check` `if: false`, тест по строке YAML.
6. **DOCS-PIPE-006** P2 — cleanup-inventory `--update` не atomic.
7. **DOCS-PIPE-007** P3 — unused `mkdocs-mermaid2-plugin`.
8. **DOCS-PIPE-008** P3 — README weekly KPI vs KEEP-DISABLED lane.

Детали: `findings.json`.

## Disjoint / not duplicated

Не аудировались narrative Diátaxis, stale prose, IA nav copy — это
`prompt.audit.docs-content`. `mkdocs.yml` `not_in_nav` / `exclude_docs` смотрелись
только как pipeline classification, не как content quality.

## Residual risk

- Weekly freshness вне path-filtered docs PR отсутствует, пока KPI lane
  keep-disabled (намеренно #10263).
- Full-corpus diagram render в docs.yml тоже `if: false`; targeted ChEMBL
  render и source-vs-SVG drift остаются.
- `validation.links.not_found: info` ослабляет mkdocs file-level; markdown
  links закрывает `check-links` (policy 06-doc-publication-policy.md).
- Passports check в docs-governance, не в `verify` — задокументировано.

## Top remediations

1. Свести `mkdocs.yml` `site_dir` и `build-site` к `docs/site/`.
2. Зафиксировать extra `docs` / fail-fast в verify; `.venv-win` в shell adapter.
3. Детерминировать ADR registry и встроить `--check` в `scripts.docs verify`.
4. Добавить `generate-pipeline-normalization-matrix --check` в активный docs.yml
   (не re-enable disabled workflow).
5. Убрать ложный package-family coverage claim либо включить реально
   исполняемый bounded `--check`.
6. Atomic write для cleanup-inventory.
