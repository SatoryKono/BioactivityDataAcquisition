# docs-pipeline

- prompt: `prompt.audit.docs-pipeline`
- HEAD: `32d77a51e556de60d6dc0daf871a442becc709c5`
- surface_score: **2**
- proven: 2; P0/P1: 0; blocked: нет

Основная цепочка на этом checkout живая: `check-links` exit 0 (2026-09-25T08:43:16Z–08:43:21Z), полный `check-drift` exit 0 (0 errors / 0 warnings), `generate-cleanup-inventory --check` синхронен, `mkdocs build --strict --clean` exit 0 за 96.97s (site во временном каталоге, не в дереве). CI: `docs.yml` → `python -m scripts.docs verify`; pin `uv.lock` mkdocs 1.6.1, `--frozen`. GitHub Pages не публикуется (`site_url` нет). Score 2: сборка и link/drift/inventory воспроизводимы, а workbook/dictionary — скрытый local-only контур со skip exit 0.

## Checks

| Команда | Результат |
| --- | --- |
| `python -m scripts.docs check-links --report-json reports/audit/docs-pipeline/link-report.json` | exit 0, violations 0 |
| `python -m scripts.docs check-drift --json` | exit 0, `drift-report.json` status PASS |
| `python -m scripts.docs generate-cleanup-inventory --check` | exit 0, inventory synchronized |
| `python -m mkdocs build --strict --clean --site-dir $TEMP` | exit 0, Documentation built in 96.97 seconds |

`--update` не использовался. Секретов в логе сборки нет.

## Findings

- **DOCS-PIPE-001** P2 PROVEN `REQ-DOC-001` `.github/workflows/tests.yml:647-654` — xlsx `docs/reports/chembl_pipeline_silver_matrices_v12.xlsx` gitignored и отсутствует; CI sync `--check` делает skip и exit 0.
- **DOCS-PIPE-002** P2 PROVEN `REQ-DOC-001` `scripts/docs/matrix/build_matrix_dicts.py:285-290` — dictionaries заявлены tracked, но gitignored, без `--check` в verify, со штампом `datetime.now` и абсолютным `source_workbook`.
- **DOCS-PIPE-003** P3 NOT_PROVEN `GAP` `scripts/docs/checks/verify.py:74-88` — verify без `--ai-surfaces`; чекер всё же вызывается pytest-ом в docs-governance.
- **DOCS-PIPE-004** P3 NOT_PROVEN `GAP` `scripts/docs/checks/documentation_cleanup_inventory.py:1573-1582` — голый вызов идёт в update. Этот прогон передал `--check`.

## Не дефекты этого HEAD

`build-site` по умолчанию добавляет `--strict` (`mkdocs_build.py:29-38`). Локальные `.png`/`.svg` в `check-links` проверяются (`check_links.py:693-696`). `mkdocs.yml` plugins: только `search`. API-страницы curated (`test_api_reference_public_facades.py`). `render-diagrams` остаётся `if: false`; description indexes в `validate-mkdocs` идут с `--check` и нормализацией штампа.

## Remediations

- Убрать skip-exit-0 для workbook либо перестать называть отсутствующий xlsx каноническим SoT.
- Согласовать `matrix-dictionaries-curated-docs` с `.gitignore`, убрать wall-clock и absolute path, добавить `--check`.
- Не публиковать сайт из audit mode.
