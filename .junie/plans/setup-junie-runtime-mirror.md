---
sessionId: session-260730-085154-1e84
---

# Requirements

### Overview & Goals

Настроить `.junie/**` как полноценный tracked runtime surface JetBrains Junie в проекте BioETL по аналогии с уже существующим `.codex/**`. Junie и Codex становятся **равноправными canonical runtime trees** для своих агентов; изменения runtime-поведения синхронизируются в обе стороны через parity-контракт.

### Scope

**In Scope**

- Создание tracked дерева `.junie/`:
  - `.junie/guidelines.md` — JetBrains-native корневой контракт (аналог `AGENTS.md`), содержащий Canonical Precedence, Required AI Context, Response Language, Post-Change Validation, Guardrails.
  - `.junie/agents/{JUNIE-RUNTIME,README,ORCHESTRATION}.md` — runtime-карта, каталог, оркестрация (mirrors of `.codex/agents/**`).
  - `.junie/agents/py-{plan,audit,architecture-debt,test,test-swarm,config,debug,doc,review-orchestrator}-bot.md` — 9 профилей, зеркальных активному набору Codex.
  - `.junie/skills/**` — mirror всех active skills из `.codex/skills/**` c `SKILLS-CATALOG.md` и `agents/openai.yaml` метаданными (либо аналогом для Junie).
- Parity-контракт и проверочный скрипт `scripts/ai/junie/check_junie_mirror.sh` (`--check` / `--sync`) + JSON контракт `scripts/ai/junie/junie-mirror-contract.json`.
- Обновление precedence chain в `AGENTS.md` и `.codex/agents/CODEX-RUNTIME.md`: `.junie/agents/JUNIE-RUNTIME.md` добавляется как active runtime source наравне с `.codex/agents/CODEX-RUNTIME.md`.
- Реклассификация `.junie/` из local-only vendor state в tracked runtime во всех governance-реестрах.
- Post-Change Validation расширяется требованием запускать mirror-check при правках `.codex/**` **и** `.junie/**`.

**Out of Scope**

- Изменения `.env`, `.gemini/**`, `.claude/**`, `.devin/**` runtime trees.
- Реальные правки бизнес-логики агентов / скиллов (только зеркалирование существующего содержимого).
- Настройка Junie IDE вне репозитория (лицензии, ключи, machine-local конфиги).
- Развёртывание нового pipeline / изменение `src/bioetl/**`.

### User Stories

- **Как разработчик, использующий JetBrains Junie**, я хочу видеть в проекте `.junie/guidelines.md` и профили агентов, чтобы Junie автоматически применял те же нормативы (RULES, REQUIREMENTS, ADR, MEMORY workflow, tech-debt guardrail), что и Codex.
- **Как maintainer**, я хочу единый parity-контракт и mirror-check, чтобы правка `.codex/agents/py-*.md` или `.codex/skills/**` не расходилась с `.junie/**`.
- **Как ревьюер**, я хочу, чтобы `AGENTS.md` явно перечислял `.junie/**` как active runtime tree, а governance-реестры (`repo_structure_catalog.yaml`, `root_hygiene_review_registry.yaml`, `03-file-policy.md`, `cleanup-policy.md`, MEM-IDE-LOCAL) корректно отражали tracked-статус.

### Functional Requirements

1. `.junie/guidelines.md` существует, отслеживается git, и его Canonical Precedence секция перечисляет: `.codex/agents/CODEX-RUNTIME.md`, `.junie/agents/JUNIE-RUNTIME.md`, `docs/00-project/NORMATIVE_SOURCES.md`, `docs/00-project/RULES.md`, `REQUIREMENTS.md`, ADRs, docs mirrors.
2. Для каждого активного Codex-агента из `.codex/agents/README.md` таблицы (9 профилей) существует зеркальный `.junie/agents/<agent>.md`.
3. Для каждого active skill из `.codex/skills/SKILLS-CATALOG.md` существует `.junie/skills/<skill>/SKILL.md`. Shared `references/**` идентичны байт-в-байт (кроме runtime-specific frontmatter).
4. `scripts/ai/junie/check_junie_mirror.sh --check` возвращает non-zero при расхождении списка агентов/скиллов или содержимого shared references; `--sync` регенерирует зеркало без затирания Codex-стороны.
5. `AGENTS.md` §Canonical Precedence перечисляет `.junie/agents/JUNIE-RUNTIME.md` как active runtime source; §Guardrails и §Related Files обновлены.
6. `.gitignore` больше не игнорирует `.junie/guidelines.md`, `.junie/agents/**`, `.junie/skills/**` (локальный machine-only state вроде `.junie/history/`, `.junie/cache/` остаётся ignored через явные негативные правила).
7. `README.md` root-allowlist секция и `.github/root-allowlist.txt` (если применимо) отражают tracked-статус `.junie/**`.

### Non-Functional Requirements

- Никаких изменений в `.env`, `src/bioetl/**`, `configs/pipelines/**`.
- Технический долг не увеличивается (правило Guardrail из `AGENTS.md`).
- Локальность BioETL сохраняется (ADR-010): никаких сетевых зависимостей.
- Все изменения detectable git-diff'ом, mirror-check воспроизводим локально без Docker.


# Technical Design

### Current Implementation

- **Codex runtime tree** (`.codex/**`): `.codex/agents/CODEX-RUNTIME.md` (runtime-карта), `.codex/agents/README.md` (mirror index каталога), `.codex/agents/ORCHESTRATION.md`, 9 tracked профилей `py-*.md` + `.codex/skills/**` с `SKILLS-CATALOG.md`, `agents/openai.yaml` метаданными, `references/**` shared blocks, parity-check `scripts/ai/codex/check_skills_mirror.sh` и контракт `scripts/ai/codex/skills-mirror-contract.json` (parity с `.devin/skills/`).
- **Junie surface** сейчас: полностью отсутствует в трекинге. `.gitignore:262` игнорирует `.junie/`. Во всех governance-реестрах помечено как local-only:
  - `configs/quality/repo_structure_catalog.yaml:94` — `role: local_vendor_editor_state_untracked`.
  - `configs/quality/root_hygiene_review_registry.yaml:477–485` — cleanup-registry для `.junie`, `.qodo`, `.sonarlint`, `.windsurf`.
  - `docs/00-project/governance/03-file-policy.md:128–132` — Editor/vendor/tooling roots.
  - `docs/03-guides/cleanup-policy.md:70,122` — `.idea/junie.xml` в списке cleanup + локальный vendor bucket.
  - `docs/00-project/governance/root-local-clutter-cleanup.md:102` — `.junie/` в списке editor/agent local state.
  - `README.md:706–710` — Junie в списке tolerated tooling/cache surfaces.
  - `src/memory/catalog/memory_registry.yaml:244–251` — `MEM-IDE-LOCAL` группирует `.cursor;.gemini;.junie;.idea` как vendor cache.
- **AGENTS.md** §Canonical Precedence перечисляет `.codex/agents/CODEX-RUNTIME.md` как единственный active runtime source; `.gemini/**` — только опционально при tracked дереве; `.junie/**` не упомянут вовсе.

### Key Decisions

1. **Junie = equal peer of Codex.** `.junie/agents/JUNIE-RUNTIME.md` добавляется как active runtime source в precedence chain наравне с `.codex/agents/CODEX-RUNTIME.md`. Двусторонний parity-контракт (изменения в любую сторону обязаны синхронизироваться).
2. **JetBrains-native root file — `.junie/guidelines.md`.** Это стандартный контракт Junie (аналог `AGENTS.md`). Он повторяет структуру `AGENTS.md`, но с приоритетным упоминанием `.junie/**` как «своей» runtime tree.
3. **Полное зеркало 9 активных `py-*` профилей + всех active skills.** Deprecated `py-code-bot` не зеркалируется (уже tombstone). Docs-only `sp-*` профили в Junie не переносятся — их место в `docs/00-project/ai/agents/agents/**` неизменно.
4. **Shared references остаются в `.codex/skills/**/references/**` как источник, `.junie/skills/**/references/**` — байт-в-байт mirror.** Это минимизирует drift и облегчает `check_junie_mirror.sh` diff.
5. **`.gitignore` реклассификация через селективное un-ignore.** Оставляем `.junie/` в списке, но добавляем негативные правила `!.junie/guidelines.md`, `!.junie/agents/`, `!.junie/agents/**`, `!.junie/skills/`, `!.junie/skills/**`; machine-local (`/.junie/history/`, `/.junie/state/`, `/.junie/cache/`) продолжает игнорироваться явно.
6. **`AI_RUNTIME_MIRROR_OWNERSHIP.md`** получает новый раздел «Junie ownership» с описанием: кто владеет `.junie/**`, каким скриптом синхронизируется, какая политика на расхождения.

### Proposed Changes

**Новые файлы под `.junie/`**

- `.junie/guidelines.md` — корневой контракт Junie.
- `.junie/agents/JUNIE-RUNTIME.md` — runtime-карта (mirror `CODEX-RUNTIME.md` с поправкой на Junie precedence).
- `.junie/agents/README.md` — каталог 9 активных агентов + `Surface Note`, что это tracked runtime (не мирроr).
- `.junie/agents/ORCHESTRATION.md` — оркестрация (mirror содержимого Codex-версии).
- `.junie/agents/py-{plan,audit,architecture-debt,test,test-swarm,config,debug,doc,review-orchestrator}-bot.md` — 9 файлов.
- `.junie/skills/SKILLS-CATALOG.md` + `.junie/skills/<skill>/SKILL.md` + shared `references/**` + `agents/openai.yaml` (или Junie-эквивалент, если требуется — при отсутствии Junie-native формата используется тот же `openai.yaml` для совместимости с capability-discovery).
- `scripts/ai/junie/check_junie_mirror.sh` — bash-скрипт с флагами `--check` и `--sync`; проверяет: (a) parity списка агентов между `.codex/agents/py-*.md` и `.junie/agents/py-*.md`; (b) parity списка скиллов; (c) идентичность shared references (SHA-256).
- `scripts/ai/junie/junie-mirror-contract.json` — декларативный контракт: mapping файлов, allow-list runtime-specific метаданных, entry-point rules.

**Изменяемые файлы**

- `AGENTS.md` — §Canonical Precedence и §Guardrails: добавить `.junie/agents/JUNIE-RUNTIME.md` как active runtime source; описать двусторонний parity-контракт.
- `.codex/agents/CODEX-RUNTIME.md` — секция §Related Runtime Surfaces добавляет `.junie/agents/**` + упоминание parity-скрипта.
- `.gitignore` — секция около строки 262: селективное un-ignore tracked поддеревьев `.junie/**` + явные ignore для `.junie/history/`, `.junie/state/`, `.junie/cache/`.
- `configs/quality/repo_structure_catalog.yaml` — сменить `role` для `.junie` на `tracked_runtime_source` (по аналогии с ролью, использованной для `.codex`).
- `configs/quality/root_hygiene_review_registry.yaml` — обновить блок `.junie` (строки 477–485): убрать из cleanup-registry, добавить в tracked-runtime registry.
- `docs/00-project/governance/03-file-policy.md` — перенести `.junie/` из «Editor/vendor/tooling roots» в раздел tracked AI runtime trees.
- `docs/03-guides/cleanup-policy.md` — обновить §120–124 и §68–72 (последняя оставляет `.idea/junie.xml` в cleanup — это отдельный IDE-файл, не runtime tree).
- `docs/00-project/governance/root-local-clutter-cleanup.md` — убрать `.junie/` из строки 102.
- `README.md` — блок §706–710: перенести `.junie/` в список tracked runtime surfaces рядом с `.codex/`, `.gemini/`.
- `src/memory/catalog/memory_registry.yaml` — `MEM-IDE-LOCAL` (строки 244–251): изъять `.junie` из `path_or_backend`, добавить новую запись `MEM-JUNIE-RUNTIME` (subtype: `runtime-source`, `path_or_backend: .junie`).
- `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md` — новый раздел «Junie ownership» + mirror-sync contract.
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` — добавить шаг: после правок под `.codex/agents/**` или `.codex/skills/**` запускать `scripts/ai/junie/check_junie_mirror.sh --check`; и наоборот при правках `.junie/**`.
- `docs/00-project/NORMATIVE_SOURCES.md` — добавить упоминание `.junie/**` как equal-peer runtime source.

### Data Models / Contracts

`scripts/ai/junie/junie-mirror-contract.json` (черновик):

```json
{
  "source_runtime": ".codex",
  "mirror_runtime": ".junie",
  "parity_scope": {
    "agents": {
      "source_glob": ".codex/agents/py-*.md",
      "mirror_glob": ".junie/agents/py-*.md",
      "required_match": ["filename", "section_headers"],
      "runtime_specific_metadata": ["model", "runtime_hint"]
    },
    "skills": {
      "source_glob": ".codex/skills/*/SKILL.md",
      "mirror_glob": ".junie/skills/*/SKILL.md",
      "required_match": ["skill_name", "description", "references_hash"]
    },
    "shared_references": {
      "source_glob": ".codex/skills/*/references/**",
      "mirror_glob": ".junie/skills/*/references/**",
      "required_match": ["sha256"]
    }
  },
  "exclusions": {
    "skills": ["py-code-bot"],
    "runtime_only_files": [".codex/agents/CODEX-RUNTIME.md", ".junie/agents/JUNIE-RUNTIME.md"]
  }
}
```

`scripts/ai/junie/check_junie_mirror.sh` контракт: exit 0 при parity, exit 1 при расхождениях с подробным diff-выводом; `--sync` копирует missing/outdated files из `.codex/**` в `.junie/**` (никогда не в обратную сторону в этом флаге).

### File Structure

```
.junie/
├── guidelines.md                          [NEW]
├── agents/
│   ├── JUNIE-RUNTIME.md                   [NEW]
│   ├── README.md                          [NEW]
│   ├── ORCHESTRATION.md                   [NEW]
│   ├── py-plan-bot.md                     [NEW, mirror]
│   ├── py-audit-bot.md                    [NEW, mirror]
│   ├── py-architecture-debt-bot.md        [NEW, mirror]
│   ├── py-test-bot.md                     [NEW, mirror]
│   ├── py-test-swarm.md                   [NEW, mirror]
│   ├── py-config-bot.md                   [NEW, mirror]
│   ├── py-debug-bot.md                    [NEW, mirror]
│   ├── py-doc-bot.md                      [NEW, mirror]
│   └── py-review-orchestrator.md          [NEW, mirror]
└── skills/
    ├── SKILLS-CATALOG.md                  [NEW]
    ├── <each active skill>/               [NEW, mirror of .codex/skills/<skill>/]
    │   ├── SKILL.md
    │   ├── agents/openai.yaml
    │   └── references/**
    └── ...

scripts/ai/junie/
├── check_junie_mirror.sh                  [NEW]
└── junie-mirror-contract.json             [NEW]

AGENTS.md                                  [MODIFIED]
.codex/agents/CODEX-RUNTIME.md             [MODIFIED]
.gitignore                                 [MODIFIED]
README.md                                  [MODIFIED]
configs/quality/repo_structure_catalog.yaml         [MODIFIED]
configs/quality/root_hygiene_review_registry.yaml   [MODIFIED]
docs/00-project/NORMATIVE_SOURCES.md                [MODIFIED]
docs/00-project/governance/03-file-policy.md        [MODIFIED]
docs/00-project/governance/root-local-clutter-cleanup.md [MODIFIED]
docs/03-guides/cleanup-policy.md                    [MODIFIED]
docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md [MODIFIED]
docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md      [MODIFIED]
src/memory/catalog/memory_registry.yaml             [MODIFIED]
```

### Architecture Diagram

```mermaid
graph TD
    AGENTS["AGENTS.md<br/>(root precedence)"] --> CODEX[".codex/agents/CODEX-RUNTIME.md"]
    AGENTS --> JUNIE[".junie/agents/JUNIE-RUNTIME.md"]
    AGENTS --> GUIDE[".junie/guidelines.md"]
    GUIDE --> JUNIE
    CODEX --> CODEX_PROFILES[".codex/agents/py-*.md<br/>(9 profiles)"]
    JUNIE --> JUNIE_PROFILES[".junie/agents/py-*.md<br/>(9 profiles, mirror)"]
    CODEX --> CODEX_SKILLS[".codex/skills/**"]
    JUNIE --> JUNIE_SKILLS[".junie/skills/**"]
    CODEX_PROFILES -. parity .-> JUNIE_PROFILES
    CODEX_SKILLS -. parity .-> JUNIE_SKILLS
    JUNIE_PROFILES -. check_junie_mirror.sh --check/--sync .-> CONTRACT["scripts/ai/junie/<br/>junie-mirror-contract.json"]
    JUNIE_SKILLS -. check_junie_mirror.sh .-> CONTRACT
    CODEX --> NORM["docs/00-project/NORMATIVE_SOURCES.md<br/>RULES.md, REQUIREMENTS.md, ADRs"]
    JUNIE --> NORM
```

### Risks

- **Drift между `.codex/**` и `.junie/**`.** Митигация: `check_junie_mirror.sh --check` в POST_CHANGE_VALIDATION и (опционально) в pre-commit; SHA-256 sums shared references.
- **Дублирование скиллов раздувает репозиторий.** Митигация: shared references копируются один-в-один, никакой доп. вариативности; допускается будущая эволюция в symlinks (не в scope).
- **Конфликт с существующей `.gitignore` политикой `.junie/`.** Митигация: селективные негативные правила + обновление governance-реестров одной атомарной серией коммитов.
- **Machine-local Junie state (history, cache) может случайно попасть в git.** Митигация: явные `/.junie/history/`, `/.junie/state/`, `/.junie/cache/` игноры + документация в `.junie/guidelines.md`.
- **`AI_RUNTIME_MIRROR_OWNERSHIP.md` уже фиксирует, что Junie — не canonical.** Требуется явная правка политики + запись в CHANGELOG.


# Testing

### Validation Approach

Поскольку задача — governance/runtime-конфиг, а не бизнес-логика, валидация состоит из статических проверок структуры файлов, содержимого и совместимости с существующими guardrails.

### Key Scenarios

1. **Parity-check зелёный после первичного развёртывания.**
   - `bash scripts/ai/junie/check_junie_mirror.sh --check` → exit 0.
   - Список `.junie/agents/py-*.md` совпадает с `.codex/agents/py-*.md` минус `py-code-bot`.
   - Список `.junie/skills/*/SKILL.md` совпадает с `.codex/skills/*/SKILL.md` (за вычетом deprecated).
2. **`.gitignore` разрешает tracked поддеревья.**
   - `git check-ignore -v .junie/guidelines.md` → not ignored.
   - `git check-ignore -v .junie/agents/py-plan-bot.md` → not ignored.
   - `git check-ignore -v .junie/history/session.log` → ignored (machine-local сохраняется).
3. **Governance-реестры согласованы.**
   - `configs/quality/repo_structure_catalog.yaml` для `.junie` содержит role `tracked_runtime_source` (или эквивалент, используемый для `.codex`).
   - `configs/quality/root_hygiene_review_registry.yaml` не содержит `.junie` в cleanup-candidates.
   - Docs (`03-file-policy.md`, `cleanup-policy.md`, `root-local-clutter-cleanup.md`, `README.md`) не упоминают `.junie/` как local-only.
4. **Precedence chain синхронизирован.**
   - `AGENTS.md` §Canonical Precedence содержит `.junie/agents/JUNIE-RUNTIME.md`.
   - `docs/00-project/NORMATIVE_SOURCES.md` перечисляет `.junie/**` как runtime source.
5. **Существующие quality-gates не сломаны.**
   - Если существует architecture hash guard / `_refresh_module_coverage_inventory.py` — они не должны срабатывать на изменения `.junie/**` (это не `src/bioetl/**`); подтвердить через dry-run.

### Edge Cases

- **Windows/POSIX line endings** в mirror-файлах: `check_junie_mirror.sh` должен нормализовывать перед сравнением SHA (или использовать `git ls-files --eol`).
- **`.junie/skills/*/agents/openai.yaml`** — если Junie не понимает формат, оставить как декларативный metadata-сайдкар (используется capability-discovery); документировать в `SKILLS-CATALOG.md`.
- **Пустое `.junie/` в чужом checkout** — `check_junie_mirror.sh --sync` должен корректно создавать структуру с нуля.
- **Deprecated `py-code-bot`** — явный `exclusions.skills` в contract JSON; тест: добавить его временно и убедиться, что `--check` не жалуется.
- **CI без bash (Windows-runner)** — предусмотреть, что скрипт запускается через `bash` (git-bash достаточен); при необходимости добавить PowerShell-обёртку.

### Test Changes

- Нет изменений в `tests/**` bioetl-код (задача non-code).
- Опционально: добавить `tests/governance/test_junie_mirror.py` (pytest), запускающий `check_junie_mirror.sh --check` через subprocess и падающий при exit != 0. Решение по добавлению — на этапе реализации.


# Delivery Steps

### * Step 1: Stage 1: Реклассификация `.junie/` в policy и governance-реестрах
`.junie/**` официально признан tracked runtime surface во всех policy-документах и registry, `.gitignore` селективно разрешает tracked поддеревья.

- Обновить `.gitignore` (район строки 262): оставить `.junie/` в списке, добавить негативные исключения `!.junie/guidelines.md`, `!.junie/agents/`, `!.junie/agents/**`, `!.junie/skills/`, `!.junie/skills/**`, и явные ignore для machine-local `/.junie/history/`, `/.junie/state/`, `/.junie/cache/`.
- В `configs/quality/repo_structure_catalog.yaml` сменить `role` для `.junie` (строка 94) с `local_vendor_editor_state_untracked` на роль, эквивалентную tracked runtime source `.codex`.
- В `configs/quality/root_hygiene_review_registry.yaml` (блок строк 477–485) убрать `.junie` из cleanup-candidates, обновить `verification` шаги.
- Обновить `docs/00-project/governance/03-file-policy.md` (§128–132), `docs/03-guides/cleanup-policy.md` (§120–124), `docs/00-project/governance/root-local-clutter-cleanup.md` (§102), `README.md` (§706–710) — перенести `.junie/` из local-only в tracked runtime.
- В `src/memory/catalog/memory_registry.yaml` (`MEM-IDE-LOCAL`, строки 244–251) удалить `.junie` из `path_or_backend`, добавить новую запись `MEM-JUNIE-RUNTIME` с subtype `runtime-source`.
- Верифицировать: `git check-ignore -v .junie/guidelines.md` → not ignored; `git check-ignore -v .junie/history/x` → ignored.

###   Step 2: Stage 2: Создание корневого контракта `.junie/guidelines.md` и runtime-карты `.junie/agents/JUNIE-RUNTIME.md`
JetBrains Junie получает свой корневой контракт и runtime map, эквивалентные `AGENTS.md` + `.codex/agents/CODEX-RUNTIME.md`.

- Создать `.junie/guidelines.md` со всеми секциями `AGENTS.md`: Canonical Precedence, Required AI Context, Response Language (RU по умолчанию), Post-Change Validation, Guardrails (RH5, local-only default, tech-debt guardrail, env-file guardrail), Dashboard Skill Routing, Related Files. В Canonical Precedence перечислить оба runtime tree как equal peers: `.codex/agents/CODEX-RUNTIME.md` и `.junie/agents/JUNIE-RUNTIME.md`.
- Создать `.junie/agents/JUNIE-RUNTIME.md` (структурно как `.codex/agents/CODEX-RUNTIME.md`): Canonical Sources, Purpose, Response Language, Technical Debt Guardrail, Recommended Mapping (для Junie ролей: default/worker или Junie-native), Related Runtime Surfaces (ссылки на `.codex/agents/**` + `.junie/**`), Env File Guardrail.
- Создать `.junie/agents/README.md` — каталог 9 активных агентов + Surface Note, помечающий `.junie/**` как tracked runtime (не мирроr) с двусторонним parity к `.codex/**`.
- Создать `.junie/agents/ORCHESTRATION.md` как зеркало Codex-версии.

###   Step 3: Stage 3: Зеркалирование 9 активных `py-*` профилей агентов в `.junie/agents/`
Каждый активный Codex `py-*` профиль имеет полный tracked mirror в `.junie/agents/`.

- Создать 9 файлов, зеркальных `.codex/agents/py-*.md`: `py-plan-bot.md`, `py-audit-bot.md`, `py-architecture-debt-bot.md`, `py-test-bot.md`, `py-test-swarm.md`, `py-config-bot.md`, `py-debug-bot.md`, `py-doc-bot.md`, `py-review-orchestrator.md`.
- Контент идентичен Codex-версии; runtime-specific метаданные (model hint, runtime pool) допускается заменять на Junie-эквивалент — фиксируется в `junie-mirror-contract.json` как allow-list.
- Deprecated `py-code-bot` в mirror **не включать** (уже tombstone в Codex).
- Docs-only `sp-*` профили из `docs/00-project/ai/agents/agents/**` не мирятся.

###   Step 4: Stage 4: Зеркалирование `.codex/skills/**` в `.junie/skills/**` + `SKILLS-CATALOG.md`
Все active skills из Codex доступны Junie через полный tracked mirror с идентичными shared references.

- Создать `.junie/skills/<skill>/SKILL.md` для каждого active skill из `.codex/skills/SKILLS-CATALOG.md` (orchestration, profile skills кроме `py-code-bot`, architecture/quality, observability, documentation, research/planning, build/design).
- Скопировать байт-в-байт `agents/openai.yaml` и `references/**` из соответствующей `.codex/skills/<skill>/` папки.
- Создать `.junie/skills/SKILLS-CATALOG.md` — mirror `.codex/skills/SKILLS-CATALOG.md` с уточнением, что shared references идентичны Codex-версии и синхронизируются через `check_junie_mirror.sh`.

###   Step 5: Stage 5: Parity-контракт `junie-mirror-contract.json` и скрипт `check_junie_mirror.sh`
Существует воспроизводимый механизм проверки и синхронизации parity между `.codex/**` и `.junie/**`.

- Создать `scripts/ai/junie/junie-mirror-contract.json` с блоками `agents`, `skills`, `shared_references`, `exclusions` (см. Data Models / Contracts в Technical Design).
- Реализовать `scripts/ai/junie/check_junie_mirror.sh` по образцу `scripts/ai/codex/check_skills_mirror.sh`: флаг `--check` (exit 1 при расхождениях с diff-выводом), флаг `--sync` (копирование missing/outdated из `.codex/**` в `.junie/**`, никогда в обратную сторону).
- Проверки: parity списка агентов (filename glob), parity списка скиллов, SHA-256 sums shared references, наличие runtime-only файлов (`JUNIE-RUNTIME.md`, `CODEX-RUNTIME.md`) на своих местах.
- Локальный smoke-test: запустить `bash scripts/ai/junie/check_junie_mirror.sh --check` → exit 0 после Stage 2–4.
- Опционально: добавить `tests/governance/test_junie_mirror.py` (pytest subprocess wrapper).

### ✓ Step 6: Stage 6: Обновление precedence chain и Post-Change Validation в canonical docs
`AGENTS.md`, `NORMATIVE_SOURCES.md`, `AI_RUNTIME_MIRROR_OWNERSHIP.md`, `POST_CHANGE_VALIDATION.md` и `.codex/agents/CODEX-RUNTIME.md` официально признают `.junie/**` equal-peer runtime и обязывают запускать parity-check.

- В `AGENTS.md` §Canonical Precedence добавить `.junie/agents/JUNIE-RUNTIME.md` как active runtime source (пункт 1 расширяется двумя equal peers); §Guardrails обновить формулировку про `.junie/**` (снять «treated as unavailable») и добавить обязательство запускать `scripts/ai/junie/check_junie_mirror.sh --check` при правках любого runtime tree; §Related Files дополнить.
- В `.codex/agents/CODEX-RUNTIME.md` §Related Runtime Surfaces добавить `.junie/agents/**` и упоминание parity-скрипта.
- В `docs/00-project/NORMATIVE_SOURCES.md` включить `.junie/**` в перечень runtime sources.
- В `docs/00-project/ai/agents/policy/AI_RUNTIME_MIRROR_OWNERSHIP.md` добавить раздел «Junie ownership»: владелец, mirror-sync контракт, политика разрешения расхождений.
- В `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` добавить обязательный шаг: после правок под `.codex/agents/**`, `.codex/skills/**`, `.junie/agents/**` или `.junie/skills/**` запускать `bash scripts/ai/junie/check_junie_mirror.sh --check` и репортить статус.
- Финальная валидация: перезапустить `check_junie_mirror.sh --check` → exit 0; вручную пройтись по чек-листу Testing / Key Scenarios.