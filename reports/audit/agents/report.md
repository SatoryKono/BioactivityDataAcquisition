# agents-runtime

- prompt: `prompt.audit.agents-runtime`
- surface_score: **2**
- proven: 6; P0/P1: 0
- run_id: `20260924T183653Z-9d9d303fa3f6-e28b4aa3`

Канон `.codex`, `.junie`, `.devin` на месте; tracked `.gemini/agents` и `.claude` отсутствуют. `check_junie_mirror.py --check` и `governance.py --check --only skill-mirrors`: exit 0. CODEX/JUNIE/DEVIN-RUNTIME совпадают с context tiers `AGENTS.md`. Оценка 2: peer-SSOT согласован и parity зелёная, дрейф локальный. Setup-prompt Devin требует RULES/ADR на любую задачу и в critical bootstrap пропускает DEVIN-RUNTIME; план Junie предписывает 9 профилей, включая запрещённые контрактом; `GEMINI.md` при конфликте ставит `AGENTS.md` выше runtime maps. Read-only профили Devin разрешают Exec(python). Разрушительный путь не доказан: OpenCode Phase 1 write:false, --sync не пишет в `.codex`.

## Findings

- **AGT-001** P2 PROVEN `.devin/prompts/devin-setup-prompt.md:8-18` — Critical bootstrap Devin требует читать RULES.md и ADR перед любой задачей и не включает DEVIN-RUNTIME, тогда как AGENTS.md и DEVIN-RUNTIME освобождают hash-only от RULES/ADR и ставят runtime map первым.
- **AGT-002** P2 PROVEN `.junie/plans/setup-junie-runtime-mirror.md:18` — Tracked план Junie всё ещё требует создать 9 py-* профилей, включая py-architecture-debt-bot, py-test-swarm и py-review-orchestrator.
- **AGT-003** P2 PROVEN `GEMINI.md:31-32` — GEMINI.md при конфликте инструкций ставит AGENTS.md выше runtime maps, тогда как AGENTS.md для конфликтов поведения ставит runtime maps первыми.
- **AGT-004** P2 PROVEN `.devin/agents/py-audit-bot/AGENT.md:19` — Профили Devin, помеченные read-only, разрешают неограниченный Exec(python), тогда как Codex sandbox и таблица Junie фиксируют read-only.
- **AGT-005** P3 PROVEN `.junie/guidelines.md:6-7` — Вступление guidelines требует синхронизировать поведение в обе стороны, а контракт и --sync пишут только .codex → .junie.
- **AGT-006** P3 PROVEN `docs/00-project/ai/prompts/library/audit/sequential-run.md:64` — Операторский prompt задаёт precedence AGENTS.md → NORMATIVE_SOURCES и пропускает runtime peers, которые AGENTS.md ставит первыми.

## Remediations

- Выровнять critical bootstrap .devin/prompts/devin-setup-prompt.md с context tiers DEVIN-RUNTIME.md и исключением hash-only в AGENTS.md:41-44.
- Снять из .junie/plans/setup-junie-runtime-mirror.md требование создавать запрещённые профили и проверять forbidden_identifiers в .junie/plans/**.
- Исправить порядок конфликтов в GEMINI.md:31-32 по AGENTS.md:10-18.
- Сузить Exec read-only профилей Devin или задокументировать, что deny:write покрывает дочерние процессы.
- Заменить «both directions» в .junie/guidelines.md:6-7 на направление codex_to_junie из контракта.
