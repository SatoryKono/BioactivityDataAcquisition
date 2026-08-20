# BRIEF — BioETL Research Ledger

**Created:** 2026-08-20
**Status:** draft — awaiting user confirmation
**Source:** inferred from `README.md`, `docs/00-project/RULES.md` v6.1.10, `docs/01-requirements/REQUIREMENTS.md` v1.12.5
**Workspace:** `./ledger/`

> Этот бриф сгенерирован автоматически, т.к. вызов `/research-workflow` не содержал текста брифа и интерактивный промпт истёк. Отредактируй файл перед стартом фазы Evidence, если формулировки неточны.

---

## 1. Core Idea (что строим, 1–2 предложения)

**BioETL** — локальный (local-first) data-engineering фреймворк для приобретения, нормализации и процессинга биоактивностных данных из публичных репозиториев (ChEMBL, PubChem, UniProt, PubMed/CrossRef/OpenAlex/Semantic Scholar) в единый аналитический **Delta Lake** warehouse по архитектуре **Medallion (Bronze → Silver → Gold)** с детерминированными записями, quarantine для отбракованных строк, control-plane (run manifest + append-only ledger) и наблюдаемостью (metrics/tracing/logging).

Второстепенные поверхности: декларативные pipeline/workflow YAML-конфиги, CLI `bioetl`, операторский HTTP и опциональный Grafana-стек (ADR-010).

## 2. Target Users (кто использует)

| Сегмент | Примеры | Ключевая JTBD |
|---------|---------|---------------|
| **Bioinformatics researchers** | исследователи, cheminformatics | получить консистентные, дедуплицированные биоактивности для ML/QSAR |
| **Data engineers / platform** | контрибьюторы BioETL | расширять провайдеры/сущности без нарушения портов и DQ-контрактов |
| **Operators / SRE (опционально)** | on-call для локального деплоя | диагностировать прогоны через manifest/ledger, метрики, дашборды L0/L1 |

Не-целевые: конечные пользователи SaaS, команды, требующие managed cloud / Redis / оркестратор по умолчанию.

## 3. Key Goals (как выглядит успех)

1. **Единый warehouse:** 22+ стандартных provider/entity пайплайнов (ChEMBL 14 сущностей + PubChem/UniProt/PubMed/CrossRef/OpenAlex/Semantic Scholar/ID Mapping) + composite-пайплайны с детерминированным merge — все через `configs/entities/{provider}/{entity}.yaml`.
2. **Качество и воспроизводимость:** Medallion-инварианты, Pandera-валидация перед каждой записью Silver/Gold, DQ-контракты с quarantine, детерминированные ретраи/бэкфилл (ADR-014) и replay-анализ.
3. **Local-only по умолчанию:** без Docker/Redis/внешней оркестрации; in-memory locking, локальные файлы; мониторинг опционален (`docker-compose.monitoring.yml` только по запросу).
4. **Наблюдаемость и управление:** bounded метрики, структурированные логи, трейсинг, run manifest/ledger, health-проверки провайдеров, операторские дашборды с контрактом `DASHBOARD_REQUIREMENTS.md`.
5. **Строгая управляемость изменениями:** версионированные контракты, синхронизация generated-артефактов, architecture guards (`tests/architecture/`), 171 требование в `REQUIREMENTS.md` с трассируемостью.

Метрики успеха (из существующего контракта): покрытие ≥85%, architecture guards зелёные, DQ quarantine форензика через `bioetl quarantine inspect`, время восстановления (RPO/RTO) по runbook.

## 4. Constraints (что явно вне скоупа)

- **Local-only default (ADR-010):** не вводить Docker/Redis/внешнюю оркестрацию как обязательные зависимости без явного запроса пользователя.
- **Hexagonal + DDD границы (ADR-005, ADR-048):** domain остаётся pure, зависимости направлены внутрь, DI только через `src/bioetl/composition/`.
- **Delta Lake only для Silver/Gold:** сырую Parquet-овскую запись без Delta запрещено (RULES §2.1).
- **Детерминизм записей:** любой прогон с теми же входами даёт байт-идентичный выход; поствалидационные трансформации требуют ревалидации.
- **Root scratch ban (RH5/RH6):** tracked root ≡ `.github/root-allowlist.txt` (37 файлов), ad-hoc `_tmp_*.py`/`test_*.py`/nul в корне запрещены.
- **Tech-debt бюджеты только вниз:** увеличивать бюджеты техдолга запрещено.
- **Env guardrail:** `.env` — secret-bearing, machine-local; создание/изменение только с явного разрешения пользователя.

## 5. Context (доменная специфика)

- **Провайдеры и лимиты:** ChEMBL 3 r/s, PubChem 5 r/s, UniProt 10/100 r/s (с ключом), PubMed 3/10 r/s, CrossRef polite pool, OpenAlex 10 r/s, Semantic Scholar 0.1/1 r/s.
- **Нормативный стек:** `AGENTS.md` (canonical precedence) → `.codex/.junie` runtime peers → `docs/00-project/NORMATIVE_SOURCES.md` → `RULES.md` → `REQUIREMENTS.md` → accepted ADRs → docs mirrors.
- **Ключевые ADRs:** ADR-002/014/018 (Medallion/детерминизм), ADR-026 (composites), ADR-027/045 (DQ), ADR-032 (unified HTTP), ADR-044/046/047 (control plane/replay), ADR-039 (unified entity config), ADR-017/019 (observability), ADR-042 (testing).
- **Операционные артефакты:** `src/bioetl/domain/control_plane/run_manifest.py`, `run_ledger.py`, `configs/workflows/`, `grafana/dashboards/`, `reports/quality/*`.
- **Текущий релиз:** 6.1.0 (unreleased), Python 3.12+, Ruff + mypy, Delta Lake + Pandera.

## 6. Open Questions (уточнить у владельца)

1. Какой именно фокус исследования нужен в ledger — продуктовая стратегия BioETL в целом или конкретная инициатива (новый провайдер/сущность, composite, observability, performance)?
2. Приоритизация пилларов для фазы Evidence — какие из 8 (market, users, tech, competitors, design, legal, ops, economics) критичны в первую очередь?
3. Нужен ли multi-stream режим (параллельные независимые потоки доказательств) или достаточно single-stream?
4. Кастомный путь ledger (по умолчанию `./ledger/`) и требования к брендингу/GTM — включать ли `09-brand`/`10-gtm-ops` в скоуп?

## 7. Next Step

- Отредактируй этот файл под реальный бриф (если инференс неточен).
- Затем: `research-workflow --phase evidence --pillar <pillar>` (или multi-stream).
- Пиларовские скоупы — в `ledger/01-pillars/PILLARS.md`.
