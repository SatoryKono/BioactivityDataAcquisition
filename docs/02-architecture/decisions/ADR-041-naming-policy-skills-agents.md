______________________________________________________________________

Version: 1.0.0
Status: Accepted
Class: published
Owner: BioETL Team
Reviewers:

- BioETL Team
  Last verified: '2026-03-30'

______________________________________________________________________

# ADR-041: Naming Policy for Skills, Agents, and Commands

## **Date:** 2026-03-04 **Status:** Accepted **Decision makers:** @BioETL-Team **Related:** ADR-040 (Mermaid), RULES.md §NAME

## Context

Критический аудит historical runtime skills, agents, and command surfaces выявил
**системные расхождения** в наименованиях, форматах файлов и языковой политике.
Отсутствие формализованной naming policy затрудняет обнаружение skills/agents
автоматическими сканерами (capability-discovery), создаёт путаницу в маппинге
команда → skill → agent и повышает когнитивную нагрузку при онбординге.

______________________________________________________________________

## Decision

### 1. Naming Convention

#### 1.1 Agents (`subagent_type`)

**Pattern:** `py-{role}-{type}`

| Segment  | Rule                                    | Values                                                                               |
| -------- | --------------------------------------- | ------------------------------------------------------------------------------------ |
| `py-`    | Обязательный префикс (Python ecosystem) | всегда `py-`                                                                         |
| `{role}` | Функциональная роль, kebab-case         | `audit`, `plan`, `test`, `debug`, `doc`, `config`, `review`                          |
| `{type}` | Архитектурный тип                       | `bot` (single agent), `swarm` (hierarchical L1→L2→L3), `orchestrator` (sector-based) |

**Filename:** `.codex/agents/{subagent_type}.md` (1:1 mapping for the current Codex workflow)

**Frontmatter (REQUIRED):**

```yaml
---
name: py-{role}-{type}        # MUST match filename
description: "..."             # English, 1 sentence
model: opus | sonnet | haiku   # Abstract alias, NOT versioned ID
---
```

#### 1.2 Skills (`.codex/skills/`)

**Pattern:** `{verb}-{noun}` или `{noun}-{noun}` в kebab-case

**Single canonical format:** `{skill-name}/SKILL.md`

| Rule                | Detail                                 |
| ------------------- | -------------------------------------- |
| Directory name      | kebab-case, descriptive English        |
| File inside         | `SKILL.md` (uppercase)                 |
| Frontmatter `name:` | **MUST** equal directory name          |
| Forbidden formats   | `.openai.yaml`, `.skill.md` flat files |

**Frontmatter (REQUIRED):**

```yaml
---
name: {skill-name}            # MUST match directory name
description: "..."             # English, max 200 chars
context: fork | none
agent: general-purpose | specific-type
---
```

#### 1.3 Commands (runtime command registry)

**Pattern:** `{action}` или `{action}-{object}` в kebab-case

**Identifier:** `{command-name}` in the active runtime command registry

**Frontmatter (REQUIRED):**

```yaml
---
description: "..."            # Russian for BioETL-specific, English for generic
---
```

#### 1.4 Name-to-Name Mapping Contract

| Entity             | Name Resolution                                       |
| ------------------ | ----------------------------------------------------- |
| Slash command `/X` | Runtime command entry `X`                             |
| Skill `X`          | Dir `.codex/skills/X/SKILL.md`, frontmatter `name: X` |
| Agent `Y`          | File `.codex/agents/Y.md`, frontmatter `name: Y`      |

**Critical invariant:** Если command делегирует agent'у, маппинг документируется
в теле command файла через `subagent_type: py-{role}-{type}`.

______________________________________________________________________

### 2. Language Policy

| Layer                               | Language                                       | Rationale                        |
| ----------------------------------- | ---------------------------------------------- | -------------------------------- |
| `name`, `description` (frontmatter) | English                                        | Machine-readable, universal      |
| Agent/Skill body (prompt text)      | Russian (BioETL-specific) or English (generic) | Team language for domain context |
| Slash command `description`         | Russian                                        | User-facing, team language       |
| `agent-orchestration-rules.md`      | Russian + English terms                        | Matches team workflow            |

______________________________________________________________________

### 3. Taxonomy: Agent Architectural Types

| Type suffix     | Pattern                               | Example                                        |
| --------------- | ------------------------------------- | ---------------------------------------------- |
| `-bot`          | Single autonomous agent, focused task | `py-test-bot`, `py-debug-bot`                  |
| `-swarm`        | Hierarchical L1→L2(→L3), auto-scaling | `py-test-swarm`, `documentation-cascade-audit` |
| `-orchestrator` | Sector-based decomposition (S1-S8)    | `py-review-orchestrator`                       |

______________________________________________________________________

## Audit Findings (Current State)

### Critical Issues (MUST fix)

| ID     | Issue                                                                                                   | Severity | Location                                      |
| ------ | ------------------------------------------------------------------------------------------------------- | -------- | --------------------------------------------- |
| NP-001 | `py-test-swarm.md` missing YAML frontmatter                                                             | CRITICAL | `agents/py-test-swarm.md`                     |
| NP-002 | `py-review-orchestrator.md` uses hardcoded model `claude-3-5-sonnet-20241022` instead of abstract alias | HIGH     | `agents/py-review-orchestrator.md`            |
| NP-003 | `deep-research/SKILL.md` name mismatch: dir=`deep-research`, frontmatter=`conducting-deep-research`     | HIGH     | `skills/deep-research/SKILL.md`               |
| NP-004 | `nci-analysis/SKILL.md` name mismatch: dir=`nci-analysis`, frontmatter=`nci-manipulation-analysis`      | HIGH     | `skills/nci-analysis/SKILL.md`                |
| NP-005 | `create-pr/SKILL.md` missing `name:` in frontmatter                                                     | HIGH     | `skills/create-pr/SKILL.md`                   |
| NP-006 | `architecture-guardian.openai.yaml` — non-standard format                                               | MEDIUM   | `skills/architecture-guardian.openai.yaml`    |
| NP-007 | `documentation-audit.openai.yaml` — non-standard format                                                 | MEDIUM   | `skills/documentation-audit.openai.yaml`      |
| NP-008 | `documentation-cascade-audit.skill.md` — non-standard flat format                                       | MEDIUM   | `skills/documentation-cascade-audit.skill.md` |

### Warnings (SHOULD fix)

| ID     | Issue                                                                                                    | Severity |
| ------ | -------------------------------------------------------------------------------------------------------- | -------- |
| NP-009 | `capability-discovery` scanner used a legacy skills-only glob and missed `.yaml` and `.skill.md` formats | LOW      |
| NP-010 | 3 redundant definition layers for `documentation-cascade-audit` (skill + command + agent)                | LOW      |
| NP-011 | Generic skills (ledger, NCI, deep-research) mixed with BioETL-specific in same directory                 | LOW      |

______________________________________________________________________

## Unification Plan

### Phase 1: Fix Critical (estimated: 30 min)

| Step | Action                                                               | Files                              |
| ---- | -------------------------------------------------------------------- | ---------------------------------- |
| 1.1  | Add frontmatter to `py-test-swarm.md`                                | `agents/py-test-swarm.md`          |
| 1.2  | Replace hardcoded model in `py-review-orchestrator.md` with `sonnet` | `agents/py-review-orchestrator.md` |

### Phase 2: Normalize Skill Names (estimated: 20 min)

| Step | Action                                                                                    | Files                           |
| ---- | ----------------------------------------------------------------------------------------- | ------------------------------- |
| 2.1  | `deep-research/SKILL.md`: change `name: conducting-deep-research` → `name: deep-research` | `skills/deep-research/SKILL.md` |
| 2.2  | `nci-analysis/SKILL.md`: change `name: nci-manipulation-analysis` → `name: nci-analysis`  | `skills/nci-analysis/SKILL.md`  |
| 2.3  | `create-pr/SKILL.md`: add `name: create-pr` to frontmatter                                | `skills/create-pr/SKILL.md`     |

### Phase 3: Migrate Non-Standard Formats (estimated: 45 min)

| Step | Action                                                                                  | Files                                   |
| ---- | --------------------------------------------------------------------------------------- | --------------------------------------- |
| 3.1  | Convert `architecture-guardian.openai.yaml` → `architecture-guardian/SKILL.md`          | create dir + SKILL.md, delete .yaml     |
| 3.2  | Convert `documentation-audit.openai.yaml` → `documentation-audit/SKILL.md`              | create dir + SKILL.md, delete .yaml     |
| 3.3  | Convert `documentation-cascade-audit.skill.md` → `documentation-cascade-audit/SKILL.md` | create dir + SKILL.md, delete flat file |

### Phase 4: Update Scanner (estimated: 15 min)

| Step | Action                                                               | Files                                  |
| ---- | -------------------------------------------------------------------- | -------------------------------------- |
| 4.1  | After Phase 3, verify `capability-discovery` scanner sees all skills | `skills/capability-discovery/SKILL.md` |

### Phase 5: Documentation (estimated: 15 min)

| Step | Action                                                             | Files                                |
| ---- | ------------------------------------------------------------------ | ------------------------------------ |
| 5.1  | Update `agent-orchestration-rules.md` with naming policy reference | `rules/agent-orchestration-rules.md` |
| 5.2  | Add this ADR to index                                              | `docs/02-architecture/decisions/`    |

______________________________________________________________________

## Consequences

### Positive

- Единый формат обнаружения skills автоматическим сканером
- 1:1 mapping между именами файлов, frontmatter `name:` и runtime identifiers
- Формализованная таксономия `-bot` / `-swarm` / `-orchestrator`
- Ликвидация дрифта между directory name и internal name

### Negative

- Миграция 3 skill файлов из legacy форматов
- Потенциально сломает внешние ссылки на `conducting-deep-research` и `nci-manipulation-analysis`

### Risks

- Если `capability-discovery` кэширует имена — нужен перезапуск после миграции
- OpenAI YAML format может использоваться другими инструментами — проверить перед удалением

______________________________________________________________________

## Compliance

This ADR establishes rules **NAME-007** through **NAME-009** to be added to `ai-selfreview-rules.md`:

| Rule     | Severity | Description                                                                        |
| -------- | -------- | ---------------------------------------------------------------------------------- |
| NAME-007 | HIGH     | Skill frontmatter `name:` MUST equal directory name                                |
| NAME-008 | HIGH     | Agent frontmatter `name:` MUST equal filename (sans `.md`)                         |
| NAME-009 | MEDIUM   | Agent `model:` MUST use abstract alias (`opus`/`sonnet`/`haiku`), not versioned ID |

## Rollout

- Rollout steps MUST be sequenced before broad adoption.
- Documentation, configuration, and test surfaces SHOULD be updated in the same change set when the decision is implemented.
- Breaking or migration-sensitive adoption SHOULD include an explicit transition window.

## Rollback

- Rollback MUST identify the last known-good behavior or artifact set.
- If the decision changes contracts, configuration, or storage semantics, rollback SHOULD include data and compatibility checks.
- Rollback triggers SHOULD be observable through tests, runtime signals, or regression symptoms.

## Verification

- Verify architecture, configuration, and documentation changes against the current codebase.
- Run the relevant tests, validators, or parity checks before considering the ADR fully adopted.
- Confirm downstream docs and contracts reflect the same decision boundaries.

## Acceptance Criteria

- [ ] The decision is documented with current status, date, and owner metadata.
- [ ] The implementation path or adoption boundary is testable and linked from the ADR.
- [ ] Supersession or migration impact is documented when the decision changes an earlier posture.
- [ ] Related docs, contracts, and operational guidance are aligned with this ADR.

## References

- `<link-or-path>`
