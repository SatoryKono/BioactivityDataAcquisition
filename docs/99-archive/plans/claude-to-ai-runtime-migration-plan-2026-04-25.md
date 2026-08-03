# План консолидации `ai/claude/*` с удалением `ai/claude/`

Дата: 2026-04-25  
Freshness note: refreshed against the live workspace on 2026-04-29  
Статус: Draft  
Владелец: Engineering / AI Runtime Governance

## Цель

Снять оставшуюся runtime-зависимость от `ai/claude/`, перенести все реально
нужные surfaces в канонические runtime roots и затем удалить `ai/claude/`
целиком.

Ключевое решение по текущему снимку:

- `ai/claude/` больше не выглядит как source-of-truth tree;
- в нем нет исполняемых скриптов, которые должны переехать в `scripts/`;
- основная масса содержимого — thin mirror / compatibility docs, уже
  ссылающиеся на `.codex/*`, `.gemini/*` и `docs/00-project/RULES.md`;
- поэтому целевая стратегия — не "перенести все как есть", а
  `repoint -> internalize -> delete`.

## Live Inventory

Подтвержденный состав `ai/claude/`:

- `ai/claude/agents/README.md`
- `ai/claude/agents/ORCHESTRATION.md`
- `ai/claude/agents/py-review-orchestrator.md`
- `ai/claude/agents/py-test-swarm.md`
- `ai/claude/agents/py-architecture-debt-bot.md`
- `ai/claude/rules/bioetl-rules.md`
- `ai/claude/rules/agent-orchestration-rules.md`
- `ai/claude/skills/py-architecture-debt-bot/SKILL.md`

Классификация:

- `agents/*`: Claude-mirror runtime profiles; canonical runtime уже живет в
  `.codex/skills/*` и `.codex/agents/*`
- `rules/*`: mirror docs на canonical sources
  (`docs/00-project/RULES.md`, `.codex/agents/ORCHESTRATION.md`,
  `.codex/agents/CODEX-RUNTIME.md`)
- `skills/py-architecture-debt-bot/SKILL.md`: compatibility skill shim;
  canonical skill уже есть в `.codex/skills/py-architecture-debt-bot/SKILL.md`

Вывод: в текущем составе нет ни одного файла, который оправданно должен жить в
`scripts/`.

## Live Callers And Drift

Подтвержденные live references на `ai/claude`:

- `README.md`
- `.codex/skills/py-review-orchestrator/SKILL.md`
- `.codex/skills/py-test-swarm/SKILL.md`
- `.codex/skills/py-architecture-debt-bot/SKILL.md`
- `.codex/skills/capability-discovery/SKILL.md`
- `.codex/skills/verify-architecture/SKILL.md`
- `.codex/skills/vcr-record/SKILL.md`
- `.codex/skills/new-pipeline/SKILL.md`
- `docs/00-project/ai/skills/README.md`

Отдельно подтвержден важный drift:

- `.codex/skills/verify-architecture/SKILL.md` ссылается на
  `ai/claude/skills/verify-architecture.md`, которого нет
- `.codex/skills/vcr-record/SKILL.md` ссылается на
  `ai/claude/skills/vcr-record.md`, которого нет
- `.codex/skills/new-pipeline/SKILL.md` ссылается на
  `ai/claude/skills/new-pipeline.md`, которого нет

Это означает, что часть migration wave уже не про "перенести файлы", а про
исправление stale source-of-truth links.

## Target State

После завершения волны:

- `ai/claude/` отсутствует
- Codex runtime использует только `.codex/skills/*` и `.codex/agents/*`
- Gemini mirrors используют только `.gemini/agents/*`
- runtime-neutral AI metadata, если такое действительно понадобится после
  реализации, живет под `.ai/`
- в `scripts/` ничего из `ai/claude/` не переносится, если в ходе реализации не
  вскроется новый executable artifact
- активные docs и skills не содержат live runtime references на `ai/claude/`

## Migration Mapping

### Delete After Repointing

- `ai/claude/agents/README.md`
  - replacement: `.codex/agents/README.md`, `.gemini/agents/README.md`
- `ai/claude/agents/ORCHESTRATION.md`
  - replacement: `.codex/agents/ORCHESTRATION.md`
- `ai/claude/rules/bioetl-rules.md`
  - replacement: `docs/00-project/RULES.md`
- `ai/claude/rules/agent-orchestration-rules.md`
  - replacement: `.codex/agents/ORCHESTRATION.md`,
    `.codex/agents/CODEX-RUNTIME.md`

### Internalize Into Existing Codex Surfaces

- `ai/claude/agents/py-review-orchestrator.md`
  - absorb any still-unique role text into
    `.codex/skills/py-review-orchestrator/SKILL.md`
- `ai/claude/agents/py-test-swarm.md`
  - absorb any still-unique role text into
    `.codex/skills/py-test-swarm/SKILL.md`
- `ai/claude/agents/py-architecture-debt-bot.md`
  - absorb any still-unique role text into
    `.codex/skills/py-architecture-debt-bot/SKILL.md`
- `ai/claude/skills/py-architecture-debt-bot/SKILL.md`
  - merge any residual detail into
    `.codex/skills/py-architecture-debt-bot/SKILL.md`

### Optional `.ai/` Extraction Only If Needed

Если в ходе body-level diff окажется, что часть текста нужна сразу двум и более
runtime surfaces и не принадлежит `docs/00-project/*`, допускается вынесение в
`.ai/` как shared AI-runtime metadata.

Предпочтительный паттерн:

- `.ai/agents/<name>.md` для runtime-neutral orchestration notes
- `.ai/policy/<name>.md` для shared AI policy notes

Но по текущему аудиту обязательных кандидатов на такой перенос нет.

## PR Wave Plan

### PR1. Caller Repoint And Skill Self-Containment

Цель: убрать live references на `ai/claude` из Codex skill layer и active docs.

Файлы:

- `.codex/skills/py-review-orchestrator/SKILL.md`
- `.codex/skills/py-test-swarm/SKILL.md`
- `.codex/skills/py-architecture-debt-bot/SKILL.md`
- `.codex/skills/capability-discovery/SKILL.md`
- `.codex/skills/verify-architecture/SKILL.md`
- `.codex/skills/vcr-record/SKILL.md`
- `.codex/skills/new-pipeline/SKILL.md`
- `README.md`
- `docs/00-project/ai/skills/README.md`

Что сделать:

1. Заменить ссылки на `ai/claude/agents/*` на `.codex/skills/*` или
   `.codex/agents/*`, в зависимости от фактического canonical owner.
1. Для `verify-architecture`, `vcr-record`, `new-pipeline` убрать ссылки на
   несуществующие `ai/claude/skills/*.md`.
1. Сделать `.codex/skills/*/SKILL.md` self-contained либо привязанными только к
   реально существующим references under `.codex/skills/*/references/`.
1. Обновить capability discovery, чтобы:
   - primary agent scan шел через `.codex/agents/` и `.gemini/agents/`
   - legacy scan `ai/claude/*` был снят полностью или оставлен только как
     temporary migration fallback на один PR, не дольше

Acceptance criteria:

- `rg -n "ai/claude" .codex docs README.md` не показывает live runtime links,
  кроме самого migration plan и historical notes
- `.codex/skills/verify-architecture/SKILL.md`,
  `.codex/skills/vcr-record/SKILL.md`,
  `.codex/skills/new-pipeline/SKILL.md` больше не ссылаются на missing files

### PR2. Claude Surface Collapse

Цель: удалить `ai/claude/` после того, как callers уже переведены.

Файлы:

- `ai/claude/agents/*`
- `ai/claude/rules/*`
- `ai/claude/skills/py-architecture-debt-bot/SKILL.md`
- docs/governance files, где `ai/claude/` еще указан как approved runtime root

Что сделать:

1. Удалить `ai/claude/agents/*`
1. Удалить `ai/claude/rules/*`
1. Удалить `ai/claude/skills/py-architecture-debt-bot/SKILL.md`
1. Удалить пустые директории `ai/claude/agents`, `ai/claude/rules`,
   `ai/claude/skills/py-architecture-debt-bot`, затем `ai/claude/skills`,
   затем `ai/claude`
1. Обновить governance and root-structure docs:
   - `README.md`
   - `configs/quality/repo_structure_catalog.yaml` only if it explicitly tracks
     `ai/claude` as a retained surface
   - root hygiene / structure tests if they still special-case `ai/claude`

Acceptance criteria:

- `rg -n "ai/claude/" .` returns only historical plan/archive context
- `test -d ai/claude && echo present || echo removed` returns `removed`
- no active skill or runtime doc requires `ai/claude/*`

## Tests And Verification

Минимальная проверка для PR1:

```bash
rg -n "ai/claude|\\.codex/agents|\\.codex/skills|\\.gemini/agents" .codex docs README.md
uv run pytest tests/architecture -q
```

Целевая проверка для PR2:

```bash
rg -n "ai/claude/" . --glob '!docs/plans/**' --glob '!docs/99-archive/**'
uv run pytest tests/architecture -q
uv run pytest tests/unit/scripts/repo -q
```

Если есть отдельные architecture tests, фиксирующие runtime surfaces, их нужно
добавить в mandatory slice этой волны.

## Risks

### Medium

- `.codex/skills/capability-discovery/SKILL.md` сейчас явно сканирует
  `ai/claude/agents`, `ai/claude/skills`, `ai/claude/commands`,
  `ai/claude/CLAUDE.md`; без обновления он будет давать ложную карту
  capabilities

### Medium

- В active docs еще есть language про `ai/claude/` как runtime root; это создаст
  governance drift, если удалить директорию без doc sync

### Low

- Удаление самих mirror markdown files низкорисково, потому что они не являются
  executable surfaces и уже ссылаются на другие canonical sources

## What Not To Do

- не переносить markdown mirrors в `scripts/`
- не создавать новый `.ai/` subtree только ради механического mirror move
- не оставлять `.codex/skills/*` зависимыми от удаляемых `ai/claude/*`
- не удалять `ai/claude/` в том же PR, где callers еще не переведены

## Definition Of Done

- `ai/claude/` удален
- все Codex skills self-contained или ссылаются только на live canonical files
- active docs больше не описывают `ai/claude/` как runtime surface
- runtime capability discovery больше не сканирует `ai/claude/*`
- remaining mentions of `ai/claude` живут только в historical plan context
