# План обновления документации проекта BioETL

**Дата:** 2026-10-15
**Версия:** 2.0
**Статус:** active
**Заменяет:** v1.0 от 2026-08-05 (закрыт, см. §1)

## Executive Summary

Аудит 2026-10-15 показывает, что механическая целостность документации здорова:
`scripts.docs check-drift` — PASS (0 issues), `check-links` — OK, навигация
mkdocs цела, cleanup-inventory генерируется без unrouted-файлов, DeepWiki
актуален (регенерация 2026-10-04, покрывает ADR-062). Основной объём работ —
не поломки, а накопленный lifecycle-долг: миграция старых рабочих отчётов,
реконсиляция issue-зеркал с GitHub и содержательная ре-верификация самых
старых `Last verified` штампов.

## 1. Закрытие плана v1.0 (2026-08-05)

| Пункт v1.0 | Итог | Доказательство |
| --- | --- | --- |
| 1.1 Dataflow guide | DONE | `docs/03-guides/pipeline-dataflow-documentation.md` существует; ссылка добавлена в `docs/00-project/00-map.md` (Quick Links) |
| 1.2 Pipeline configuration + dataflow | DONE | `docs/03-guides/pipeline-configuration.md` §953+ описывает генерацию dataflow, passports, CI drift detection |
| 2.1 Layer docs port patterns | DONE | `CompositeCheckpointService` задокументирован в `docs/02-architecture/02-application-layer.md` |
| 2.2 Fail-fast semantics | OPEN → перенесено в v2 фазу 3 | `docs/02-architecture/domain-composite.md` не содержит fail-fast описания EnrichmentCoordinatorService |
| 3.1 Locking terminology | DONE | `running-pipelines.md`, `runbooks/scaling.md` используют Local-Only / MemoryLock (ADR-010) |
| 3.2 CLI observability defaults | DONE | `docs/04-reference/cli.md` документирует `--ensure-observability-backend` (default off) |
| 4.1 Passport guide + ADR-054 | DONE | `pipeline-passport-guide.md` — «deterministic documentation projections» |
| 4.2 Normalization cheatsheet | UNVERIFIED → v2 фаза 3 | canonical fields в `cheatsheets/pipeline-config.md` не подтверждены |
| Процессные рекомендации (PR template, CI checks, KPI) | частично: `report_docs_kpi`, `check-drift`, cleanup-inventory внедрены; PR template и freshness-gate — нет | → v2 фаза 6 |

## 2. Текущее верифицированное состояние (2026-10-15)

Механические гейты:

| Проверка | Результат |
| --- | --- |
| `python -m scripts.docs check-drift` | PASS, 0 issues (порты/классы/модули в docs совпадают с кодом) |
| `check-links` | OK — битых относительных ссылок нет, nav цел |
| `generate-cleanup-inventory` | 3811 файл, 0 unrouted, 73 generated routes |
| DeepWiki | актуален: регенерация 2026-10-04, покрывает ADR-062 |

Реальные пробелы (данные `documentation-cleanup-inventory.json`):

| Пласт | Объём | Маркер действия |
| --- | --- | --- |
| Stale `working_report` в `reports/` | 1028 файлов | `archive-after-migration` |
| `.github/ISSUES` drafts/packs/mirrors | 346 | `archive-after-github-state-check` (338) + `reconcile-with-github-state` (8) |
| Published docs `Last verified` < 2026-08 | ~170 (из них ~98 — 2026-03) | содержательная ре-верификация |
| Retention-sensitive evidence | 165 | retention-политика `03-file-policy` |
| Duplicate groups | 7 пар | по `duplicate_resolution` |

Известный семантический дрейф (check-drift его не ловит — имена целы):
`docs/02-architecture/data-layers.md` (Last verified 2026-07-28) описывает
модель Silver до изменений #12122 (удаление Silver DELETE, injected clocks,
strict preflight) — требуется содержательное обновление, а не рестампинг.

## 3. План обновления v2.0

### Фаза 1 — Issue-mirror реконсиляция (~1 день, механично)

- Вытянуть live-состояние через `gh issue list --state all --json number,state,closedAt` и сопоставить с `github_issue_number` в cleanup-inventory.
- Файлы с закрытыми issue и маркером `archive-after-github-state-check` → перенос в `docs/99-archive/` по `03-file-policy`.
- 8 файлов `reconcile-with-github-state` — ручная проверка расхождений.
- После переноса: `python -m scripts.docs generate-cleanup-inventory --update`, затем `--check`.

### Фаза 2 — Reports-миграция (1–2 дня, механично)

- 1028 `working_report` + остальные `archive-after-migration` → переместить по retention-лейну `03-file-policy` (архивация, не удаление).
- 165 `retention-sensitive` evidence — отдельным списком, по политике хранения.
- Регенерация cleanup-inventory и link-проверка после миграции.

### Фаза 3 — Ре-верификация published docs (основная работа, ~1–2 недели)

Волнами по возрасту `Last verified`, содержательно (не штамп):

1. **2026-03 (~98 файлов):** `docs/00-project/glossary.md`, `03-file-policy.md`, `02-architecture/07-compatibility-facade-inventory.md`, diagram descriptions (`descriptions/architecture/*`).
2. **2026-07/08 (~72 файла):** `data-layers.md`, `docs-verification.md`, `NORMATIVE_SOURCES.md`, ADR-053-era, diagram READMEs.
3. Закрыть перенесённые из v1: fail-fast semantics в `domain-composite.md` (2.2), canonical fields в `cheatsheets/pipeline-config.md` (4.2).

Каждый файл: сверка семантики с кодом (особенно storage/control-plane/composite
после недавних PR), фикс контента или bump `Last verified` (+Version) если
чисто. Приоритет: `02-architecture` > `03-guides` > `05-operations`.

### Фаза 4 — Дубликаты и навигация (0.5 дня)

- 7 пар `duplicate_group` — применить `duplicate_resolution`/`canonical_successor` из cleanup-inventory.
- `check-links --legacy-paths` на ссылки в архивные пути после фаз 1–2.

### Фаза 5 — Генерируемые поверхности (0.5 дня)

- `generate-cleanup-inventory --update`, `report_docs_kpi`, adr-registry, pipeline dataflows — перегенерировать и прогнать `--check`.

### Фаза 6 — Процесс (0.5 дня)

- Проверить wiring `check-drift --freshness` в CI; при отсутствии — тикет на freshness age-gate (warn при `Last verified` > 90 дней).
- PR template: checklist-пункт «docs touched? → обнови Last verified / inventory».
- DeepWiki: действий не требуется (авто-реиндексация, свежая). Issue #8035 (regen request) — проверить статус и закрыть, если покрыто.

## 4. Границы

- `docs/99-archive/**`, `docs/reports/generated/**`, retention-sensitive evidence — без отдельного решения не трогаем.
- Рестампинг `Last verified` без сверки содержимого запрещён — это скрывает семантический дрейф.

## Критерии успеха

- [ ] `archive-after-github-state-check` и `archive-after-migration` в инвентаре → 0
- [ ] `Last verified` старше 90 дней → 0 в published surface (`docs/0[0-5]`)
- [ ] `data-layers.md` синхронизирован с post-#12122 storage semantics
- [ ] `check-drift`, `check-links`, cleanup-inventory `--check` — зелёные после каждой фазы
- [ ] Все 7 duplicate groups разрешены

## Риски и митигация

| Риск | Влияние | Митигация |
| --- | --- | --- |
| Семантический дрейф вне зоны check-drift | Среднее | Фаза 3 — содержательная ре-верификация, не рестампинг |
| Объём reports-миграции | Низкое | Механично, по lifecycle-полю инвентаря; батчи по разделам |
| Устаревание во время работы | Среднее | Фаза 6 — freshness-gate в CI, чтобы долг не возвращался |

## Следующие шаги

1. Фаза 1–2 — механическая гигиена (issue-mirrors, reports) — снимает ~60% инвентарного шума.
2. Фаза 3 — содержательная волна ре-верификации.
3. Фазы 4–6 — замыкание + защита от регресса.

---

**Создано:** 2026-10-15 (v2.0)
**Автор:** Devin AI Assistant
**История:** v1.0 (2026-08-05) — закрыт в §1
**Связанные артефакты:**

- `docs/reports/generated/documentation-cleanup-inventory.{json,md}` — источник lifecycle-данных
- `docs/00-project/governance/03-file-policy.md` — retention/archive правила
- `docs/03-guides/docs-verification.md` — published docs boundaries
- GitHub Issue #8035 (DeepWiki regeneration request) — проверить и закрыть
