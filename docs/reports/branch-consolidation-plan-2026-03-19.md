# План консолидации веток за последние 48 часов

Ниже безопасный runbook консолидации. Исхожу из двух фактов: целевая база это `origin/main`, и текущий рабочий каталог грязный, поэтому консолидацию лучше делать в отдельном worktree.

## 0. Подготовка

Создай отдельный worktree от `origin/main`:

```bash
git fetch --all --prune
git worktree add ../BioactivityDataAcquisition2-consolidate -b consolidate/recent-branches-20260319 origin/main
cd ../BioactivityDataAcquisition2-consolidate
```

Проверь базу:

```bash
git status --short
git rev-parse --short HEAD
git branch -vv
```

Ожидаемо: чистое дерево на ветке `consolidate/recent-branches-20260319`.

## 1. Влить независимую workflow-ветку

Единственная ветка, которую имеет смысл брать почти целиком: `origin/dependabot/github_actions/actions/checkout-6`.

```bash
git cherry-pick f401a2a4b
```

Проверка:

```bash
git diff --name-only HEAD~1..HEAD
```

Ожидаемо: только `.github/workflows/**`.

## 2. Поднять scripts-inventory ветку выборочно

Не мержить целиком `origin/bolt-optimize-as-py-8836708768404040860`. Забрать только её действительно уникальный кусок:

```bash
git checkout origin/bolt-optimize-as-py-8836708768404040860 -- scripts/repo/check_scripts_inventory.py
git checkout origin/bolt-optimize-as-py-8836708768404040860 -- tests/architecture/test_scripts_inventory_discovery.py
git checkout origin/bolt-optimize-as-py-8836708768404040860 -- tests/architecture/test_codex_skill_agent_links.py
git add scripts/repo/check_scripts_inventory.py tests/architecture/test_scripts_inventory_discovery.py tests/architecture/test_codex_skill_agent_links.py
git commit -m "chore(scripts): port recent scripts inventory fixes"
```

Проверка:

```bash
cmd.exe /c "cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2-consolidate && .venv\Scripts\python.exe -m pytest -p no:xdist tests\architecture\test_scripts_inventory_discovery.py tests\architecture\test_codex_skill_agent_links.py -q"
```

## 3. Отдельно разобрать pyarrow/perf кластер

`origin/bolt/pyarrow-as-py-optimization-14437032280125748650` и `origin/bolt-optimize-as-py-8836708768404040860` нельзя мержить целиком: там много overlap и CI-churn.

Сначала посмотреть только perf-кусок:

```bash
git diff origin/main...origin/bolt-optimize-as-py-8836708768404040860 -- src/bioetl/domain/serialization.py src/bioetl/infrastructure/export/csv_exporter_table_ops.py
git diff origin/main...origin/bolt/pyarrow-as-py-optimization-14437032280125748650 -- src/bioetl/domain/serialization.py src/bioetl/infrastructure/export/csv_exporter_table_ops.py
```

Если diff одинаковый или совместимый, бери только эти два файла из одной ветки, предпочтительно из более узкой `origin/bolt-optimize-as-py-8836708768404040860`:

```bash
git checkout origin/bolt-optimize-as-py-8836708768404040860 -- src/bioetl/domain/serialization.py
git checkout origin/bolt-optimize-as-py-8836708768404040860 -- src/bioetl/infrastructure/export/csv_exporter_table_ops.py
git add src/bioetl/domain/serialization.py src/bioetl/infrastructure/export/csv_exporter_table_ops.py
git commit -m "perf(pyarrow): port as_py optimization changes"
```

Проверка:

```bash
cmd.exe /c "cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2-consolidate && .venv\Scripts\python.exe -m pytest -p no:xdist tests\architecture\test_regression_metrics.py tests\architecture\test_code_metrics.py -q"
```

## 4. Вытащить только полезный quality-кусок из review-reports

Из `origin/feat/review-reports-14838491997822328842` уникально интересен `src/bioetl/infrastructure/quality/budget_evaluator.py`. Не бери всю ветку.

Сначала посмотри diff:

```bash
git diff origin/main...origin/feat/review-reports-14838491997822328842 -- src/bioetl/infrastructure/quality/budget_evaluator.py
git diff origin/main...origin/feat/review-reports-14838491997822328842 -- .gitignore
```

Если изменение в `budget_evaluator.py` нужно, перенеси файл или конкретные hunks:

```bash
git checkout origin/feat/review-reports-14838491997822328842 -- src/bioetl/infrastructure/quality/budget_evaluator.py
git add src/bioetl/infrastructure/quality/budget_evaluator.py
git commit -m "fix(quality): port budget evaluator adjustments"
```

`.gitignore` переносить только если там реально новые полезные ignore-правила.

Проверка:

```bash
cmd.exe /c "cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2-consolidate && .venv\Scripts\python.exe -m pytest -p no:xdist tests\architecture\test_quality_debt_scorecard.py tests\architecture\test_quality_burndown_priorities.py -q"
```

## 5. Из docs-ветки брать только report

`origin/docs/arch-review-refactoring-plan-1254790078704454945` не стоит мержить целиком. Забери только артефакт:

```bash
git checkout origin/docs/arch-review-refactoring-plan-1254790078704454945 -- docs/reports/architecture-review-and-refactoring-plan.md
git add docs/reports/architecture-review-and-refactoring-plan.md
git commit -m "docs(reports): add architecture review and refactoring plan"
```

`mkdocs.yml` переносить только после ручного сравнения:

```bash
git diff origin/main...origin/docs/arch-review-refactoring-plan-1254790078704454945 -- mkdocs.yml
```

Если там только nav-entry для нового отчёта, перенеси её вручную, не файлом целиком.

## 6. Не мержить целиком две шумные ветки

Эти ветки лучше закрыть после выборочного извлечения нужного:

- `origin/fix/py-test-swarm-arch-tests-13704176743142189750`
- `origin/bolt/pyarrow-as-py-optimization-14437032280125748650`

Для них максимум сделать финальную проверку, что после шагов 2-4 там не осталось нужных уникальных кодовых файлов:

```bash
git diff --name-only HEAD...origin/fix/py-test-swarm-arch-tests-13704176743142189750
git diff --name-only HEAD...origin/bolt/pyarrow-as-py-optimization-14437032280125748650
```

Если остаются только `reports/**`, временные tracking-файлы или уже покрытый overlap, ветки можно считать закрываемыми.

## 7. Ветка review-orchestrator

`origin/feature/review-orchestrator-2340624145261315589` в этот батч не включать. Она вне строгого окна 48h и слишком тяжёлая по артефактам `reports/review/**`. Её лучше разбирать отдельно.

## 8. Финальная верификация

После всех шагов:

```bash
cmd.exe /c "cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2-consolidate && .venv\Scripts\python.exe -m pytest -p no:xdist tests\architecture\test_scripts_inventory_discovery.py tests\architecture\test_architecture_dependency_docs_drift.py tests\architecture\test_quality_debt_scorecard.py tests\architecture\test_quality_burndown_priorities.py tests\architecture\test_regression_metrics.py -q"
```

Параллельно:

```bash
cmd.exe /c "cd /d E:\g-drive\05_AI\github\BioactivityDataAcquisition2-consolidate && .venv\Scripts\python.exe scripts\docs\check_doc_links.py --configs"
```

И затем:

```bash
git log --oneline --decorate -n 10
git diff --stat origin/main..HEAD
```

## 9. Что закрывать после консолидации

Если интеграционная ветка зелёная, кандидаты на удаление:

- `origin/dependabot/github_actions/actions/checkout-6` после merge
- `origin/bolt-optimize-as-py-8836708768404040860` после selective port
- `origin/fix/py-test-swarm-arch-tests-13704176743142189750` после проверки, что отчёты не нужны
- `origin/bolt/pyarrow-as-py-optimization-14437032280125748650` после selective port
- `origin/docs/arch-review-refactoring-plan-1254790078704454945` после extraction
- `origin/feat/review-reports-14838491997822328842` после extraction

