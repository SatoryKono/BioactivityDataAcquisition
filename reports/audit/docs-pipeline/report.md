# docs-pipeline

- **prompt:** `prompt.audit.docs-pipeline`
- **HEAD:** `e1c184857e460461bbb3e20829e60ab8bb262e2f` (origin/main)
- **surface_score:** **1**
- **proven:** 9; **P0/P1:** 0; **blocked:** нет

## Резюме

Каноническая команда `python -m scripts.docs verify` на чистом checkout **не проходит** на этом HEAD: ломаются `check-links` (workflow inventory triggers), `check-drift` (freshness RULES), `generate-cleanup-inventory --check` и `generate-pipeline-normalization-matrix --check`. При этом `mkdocs build --strict --clean` в temp site dir завершается **exit 0** (~56s). Toolchain закреплён через `uv.lock` (mkdocs `>=1.6,<2.0`). Публикация GitHub Pages отключена (`mkdocs.yml`: `site_url` omitted).

Score **1**: pipeline частично воспроизводим, но blocking verify chain красная; не score 0, потому что strict-сборка и link-check (кроме inventory claims) не «сломан build tool».

## Проверки (worktree nine-domain-audit, 2026-09-26)

| Команда | Результат |
| --- | --- |
| `python -m scripts.docs verify --skip-build` | **exit 1** (останов на check-links) |
| `python -m scripts.docs check-links --workflow-inventory` | **exit 1**, 4 trigger mismatches |
| `python -m scripts.docs check-drift --ports --classes --runtime-mirrors --freshness --modules` | **exit 1**, 1 freshness ERROR |
| `python -m scripts.docs generate-cleanup-inventory --check` | **exit 1**, drift + coderabbit paths |
| `python -m scripts.docs generate-pipeline-normalization-matrix --check` | **exit 1**, без stdout |
| `python -m scripts.docs check-docstrings --summary` | exit 0 |
| `python -m mkdocs build --strict --clean --site-dir $TEMP` | exit 0 |

Секретов в выводе команд не обнаружено. Режим audit: без publish/push.

## Findings (кратко)

| ID | P | Status | Суть |
| --- | --- | --- | --- |
| DOCS-PIPE-001 | P2 | PROVEN | Workflow inventory triggers ≠ YAML после #11234 |
| DOCS-PIPE-002 | P2 | PROVEN | documentation-cleanup-inventory drift (coderabbit reports) |
| DOCS-PIPE-003 | P2 | PROVEN | Freshness: ai/rules/README vs RULES 6.1.13 |
| DOCS-PIPE-004 | P2 | PROVEN | Tracked normalization matrix --check fail |
| DOCS-PIPE-005 | P3 | PROVEN | Silent --check в normalization matrix |
| DOCS-PIPE-006 | P2 | PROVEN | proof-or-stop: `verify --skip-build` |
| DOCS-PIPE-007 | P3 | PROVEN | verify без passports |
| DOCS-PIPE-008 | P3 | PROVEN | verify drift без --ai-surfaces |
| DOCS-PIPE-009 | P3 | PROVEN | render-diagrams job `if: false` |

## Не входит в scope / снято с прошлого прогона

- **Workbook xlsx skip exit 0 в tests.yml:** на e1c184857e46 CI опирается на `export-matrix-structural-contract --check` (tests.yml:658-659); sync workbook не вызывается.
- **matrix-dictionaries tracked vs gitignore:** routing `ignored_local_output` согласован (generated_artifact_routing.yaml:180-186); `build_matrix_dicts` пишет через temp+`os.replace`, `source_workbook` = имя файла.

## Top remediations

1. Обновить `docs/04-reference/github-actions-workflows.md` (Triggers) под фактические `on:`.
2. `generate-cleanup-inventory --update` или убрать ephemeral tracked coderabbit paths.
3. Sync версии RULES в `docs/00-project/ai/rules/README.md`.
4. Перегенерировать pipeline normalization matrix + улучшить сообщения `--check`.
