# План очистки веток репозитория BioactivityDataAcquisition

**Дата анализа:** 2026-07-13  
**Критерий:** ветки, созданные до 2026-06-30 включительно  
**Всего веток:** 348  
**Веток до 2026-06-30:** 291  

## Сводка

| Категория | Количество | Описание |
|-----------|------------|----------|
| Безопасно для удаления | 11 | Слиты в main, нет уникальных коммитов |
| Требуют проверки | 278 | Не слиты или требуют ручной проверки |
| Защищённые | 2 | main, master (не удалять) |
| Слишком новые | 0 | Веток после 2026-06-30 нет |

---

## Приоритет 1: Безопасное удаление (11 веток)

Эти ветки уже слиты в `main` и могут быть безопасно удалены.

### Локальные ветки (11)

| Ветка | Автор | Дата последнего коммита | SHA |
|-------|-------|------------------------|-----|
| `fix/issue-3105-sonar-baseline-step1` | SatoryKono | 2026-04-24 | 402d616722bb6c3b0cfc87c8a8f06821171ad088 |
| `main_20250426` | SatoryKono | 2026-04-25 | c97c4bcf9cb19478d54772f29f90b866ffc7d7dd |
| `main_20260426-1` | SatoryKono | 2026-04-26 | 35fdc976f6c3b2cfc0ca3b342b95eb7f20e8306c |
| `main_20260503` | SatoryKono | 2026-05-03 | 31b7fe908ed9f655f93cdb08532a9a73d4babc29 |
| `main_20260505` | SatoryKono | 2026-05-04 | 47846528e2a6202a84f725a54d9ace52fd7c9ddc |
| `main_20260514` | SatoryKono | 2026-05-14 | 5d34468b9dc6a2a6965737bb223f5776ce42b000 |
| `main_20260615` | SatoryKono | 2026-05-15 | f23e92c9b97d57ff7df2c9d0f2780b0018f59060 |
| `main_20260514-2` | SatoryKono | 2026-05-15 | 8e551ab1c22032b9997e6ce88a77ea24241fa5c4 |
| `fix/repro-4526-4530` | SatoryKono | 2026-05-22 | 18f4c1a75404419d217f9feed0cefeb571f04a0e |
| `codex/close-5395-5401` | SatoryKono | 2026-06-18 | 7ff3b97103f582fa64186c9b035a16a38fbfcdcd |
| `tmp-20260626` | SatoryKono | 2026-06-25 | b2e3f1baa08e0e55368ef077684ade9a98190a7d |

**Рекомендация:** Удалить локально командой:
```bash
git branch -d fix/issue-3105-sonar-baseline-step1
git branch -d main_20250426
git branch -d main_20260426-1
git branch -d main_20260503
git branch -d main_20260505
git branch -d main_20260514
git branch -d main_20260615
git branch -d main_20260514-2
git branch -d fix/repro-4526-4530
git branch -d codex/close-5395-5401
git branch -d tmp-20260626
```

---

## Приоритет 2: Требуют проверки (278 веток)

Эти ветки не слиты в `main` или требуют ручной проверки перед удалением.

### 2.1. Локальные ветки (30)

#### Ветки задач (issue/*) - 27 веток

Большинство этих веток относятся к апрелю 2026 и связаны с observability, checkpointing, и runtime wiring. Рекомендуется проверить статус соответствующих issues.

| Ветка | Дата | Описание |
|-------|------|----------|
| `issue/2686-checkpoint-fingerprint-sync` | 2026-04-09 | Checkpoint fingerprint sync |
| `issue/2687-registry-hash-canonical` | 2026-04-09 | Registry hash canonical |
| `issue/2688-smiles-vo` | 2026-04-09 | SMILES value object |
| `issue/2689-field-matrix-contract` | 2026-04-09 | Field matrix contract |
| `issue/2690-workflow-config` | 2026-04-09 | Workflow config |
| `issue/2712-audit-runtime-wiring-clean` | 2026-04-10 | Audit runtime wiring clean |
| `issue/2723-deterministic-persisted-contract` | 2026-04-10 | Deterministic persisted contract |
| `issue/2733-bounded-observability-labels` | 2026-04-10 | Bounded observability labels |
| `issue/2733-bounded-observability-labels-v3` | 2026-04-10 | Bounded observability labels v3 |
| `issue/2735-metrics-port-split` | 2026-04-10 | Metrics port split |
| `issue/2736-freshness-from-anchors` | 2026-04-10 | Freshness from anchors |
| `issue/2737-observability-diagnostics` | 2026-04-10 | Observability diagnostics |
| `issue/2741-composite-join-merge-core` | 2026-04-10 | Composite join merge core |
| `issue/2754-deterministic-dq-context` | 2026-04-10 | Deterministic DQ context |
| `issue/2762-domain-event-observability-map` | 2026-04-10 | Domain event observability map |
| `issue/2769-observability-api-consolidation` | 2026-04-10 | Observability API consolidation |
| `issue/2770-checkpoint-observability` | 2026-04-10 | Checkpoint observability |
| `issue/2771-audit-checkpoint-diagnostics` | 2026-04-10 | Audit checkpoint diagnostics |
| `issue/2772-runtime-observability-contract` | 2026-04-10 | Runtime observability contract |
| `issue/2778-2780-phase1` | 2026-04-10 | Phase 1 of issues 2778-2780 |
| `issue/2786-domain-schema-metadata` | 2026-04-10 | Domain schema metadata |
| `issue/2788-observability-cli-workflows` | 2026-04-10 | Observability CLI workflows |
| `issue/obs-p0-audited-main` | 2026-04-10 | P0 audited main |
| `issue/obs-p0-observability-surface` | 2026-04-10 | P0 observability surface |

**Рекомендация:** Проверить статус issues в GitHub. Если issues закрыты и изменения слиты, ветки можно удалить.

#### Другие локальные ветки (3)

| Ветка | Дата | Описание |
|-------|------|----------|
| `chore/consolidate-recent-branches` | 2026-03-20 | Bot branch for consolidation |
| `integration/repro-2754-2761` | 2026-04-10 | Integration repro |
| `backup/local-main-before-4083-4085` | 2026-05-14 | Backup branch |
| `main_20260404` | 2026-04-04 | Date-based snapshot |
| `main_20260505-1` | 2026-05-05 | Date-based snapshot |

**Рекомендация:** 
- `backup/local-main-before-4083-4085` - проверить, нужна ли резервная копия
- `main_20260404`, `main_20260505-1` - можно удалить, если snapshots больше не нужны
- Bot ветки - можно удалить, если изменения не нужны

### 2.2. Удалённые ветки origin/* (248)

#### Bot-ветки (google-labs-jules[bot], dependabot[bot], copilot, devin, claude) - ~200 веток

Большинство bot-веток содержат экспериментальные изменения, оптимизации, или зависимости. Многие из них не слиты.

**Рекомендация:** 
1. Проверить наличие открытых PR для этих веток
2. Если PR закрыты/слиты и изменения не нужны - удалить
3. Для dependabot веток - проверить, обновлены ли зависимости в main

#### Codex/Claude ветки - ~30 веток

Экспериментальные ветки от AI-агентов.

**Рекомендация:** Проверить, есть ли полезные изменения. Если нет - удалить.

#### Временные и тестовые ветки - ~10 веток

`tmp`, `tmp01`, `tmp2`, `tmp-audit-noop-cleanup`, `test-*`, и т.д.

**Рекомендация:** Можно удалить, если тесты завершены.

#### Date-based ветки (main_*, master_*) - ~20 веток

Snapshots main/master на определённые даты.

**Рекомендация:** Удалить, если snapshots больше не нужны для отката.

#### Feature/fix/chore/perf ветки - ~30 веток

Ветки для конкретных задач.

**Рекомендация:** Проверить статус соответствующих issues/PR. Если закрыты/слиты - удалить.

---

## Приоритет 3: Защищённые ветки (2 ветки)

| Ветка | Статус |
|-------|--------|
| `main` | Основная ветка, не удалять |
| `master` | Legacy ветка, возможно нужна для совместимости |

**Рекомендация:** НЕ УДАЛЯТЬ

---

## Безопасная последовательность действий

### Шаг 1: Удаление безопасных локальных веток
```bash
# Удалить 11 слитых локальных веток
git branch -d fix/issue-3105-sonar-baseline-step1
git branch -d main_20250426
git branch -d main_20260426-1
git branch -d main_20260503
git branch -d main_20260505
git branch -d main_20260514
git branch -d main_20260615
git branch -d main_20260514-2
git branch -d fix/repro-4526-4530
git branch -d codex/close-5395-5401
git branch -d tmp-20260626
```

### Шаг 2: Проверка локальных issue-веток
Для каждой локальной issue-ветки:
1. Проверить статус issue в GitHub
2. Если issue закрыт и изменения слиты - удалить ветку
3. Если issue открыт или изменения не слиты - сохранить

### Шаг 3: Проверка backup и snapshot веток
1. `backup/local-main-before-4083-4085` - решить, нужна ли резервная копия
2. `main_20260404`, `main_20260505-1` - удалить, если snapshots не нужны

### Шаг 4: Проверка удалённых веток (origin/*)
**Важно:** Удаление удалённых веток требует осторожности.

1. Проверить наличие открытых PR:
   ```bash
   # Для конкретной ветки
   gh pr list --head origin/branch-name
   ```

2. Для bot-веток:
   - Проверить, слиты ли изменения
   - Если да и PR закрыт - удалить
   - Если нет - оценить необходимость изменений

3. Для dependabot веток:
   - Проверить, обновлены ли зависимости в main
   - Если да - удалить ветку

4. Удаление удалённых веток:
   ```bash
   # Локальное удаление ссылки на удалённую ветку
   git branch -d -r origin/branch-name
   
   # Удаление с удалённого сервера (требует прав)
   git push origin --delete branch-name
   ```

### Шаг 5: Очистка orphaned references
```bash
# Очистка локальных ссылок на удалённые ветки
git remote prune origin
```

---

## Рекомендации по автоматизации

### Скрипт для удаления безопасных локальных веток
```bash
#!/bin/bash
# delete_safe_branches.sh

SAFE_BRANCHES=(
    "fix/issue-3105-sonar-baseline-step1"
    "main_20250426"
    "main_20260426-1"
    "main_20260503"
    "main_20260505"
    "main_20260514"
    "main_20260615"
    "main_20260514-2"
    "fix/repro-4526-4530"
    "codex/close-5395-5401"
    "tmp-20260626"
)

for branch in "${SAFE_BRANCHES[@]}"; do
    git branch -d "$branch"
done
```

### Скрипт для проверки PR перед удалением origin веток
```bash
#!/bin/bash
# check_prs.sh

for branch in $(git branch -r | grep origin/ | grep -v origin/main | grep -v origin/master); do
    branch_name=${branch#origin/}
    echo "Checking PR for $branch_name"
    gh pr list --head "$branch_name" --state all
done
```

---

## Статистика по типам веток

| Тип ветки | Количество | Приоритет очистки |
|-----------|------------|-------------------|
| Локальные слитые | 11 | Высокий |
| Локальные issue/* | 27 | Средний |
| Локальные backup/snapshot | 3 | Средний |
| Origin bot-ветки | ~200 | Низкий |
| Origin feature/fix/* | ~30 | Средний |
| Origin date-based | ~20 | Низкий |
| Origin temporary | ~10 | Высокий |

---

## Примечания

1. **Дата создания:** Использована дата последнего коммита как приближение даты создания ветки
2. **Статус слияния:** Проверено относительно ветки `main`
3. **PR статус:** Не проверен (требует доступа к GitHub API)
4. **Уникальные коммиты:** Не проверено для всех веток из-за большого объёма

---

## Дальнейшие действия

1. **Немедленно:** Удалить 11 безопасных локальных веток
2. **Краткосрочно:** Проверить статус issues для локальных issue-веток
3. **Среднесрочно:** Проверить PR статус для origin веток
4. **Долгосрочно:** Рассмотреть автоматическую очистку bot-веток после закрытия PR

---

**Отчёт сгенерирован:** 2026-07-13  
**Детальный JSON отчёт:** `branch_cleanup_report.json`
