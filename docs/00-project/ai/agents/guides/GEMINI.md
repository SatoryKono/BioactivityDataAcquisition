# Gemini is not a BioETL runtime

*Статус: internal-published (Internal / Extended)*

Gemini CLI is not a supported runtime in this repository. There is no root
`GEMINI.md` and no tracked `.gemini/agents/**` or `.gemini/skills/**` tree.

Read first, in this order:

1. `AGENTS.md`
1. `.codex/agents/CODEX-RUNTIME.md` and `.junie/agents/JUNIE-RUNTIME.md` (equal peers; plus `.junie/guidelines.md`)
1. `.devin/agents/DEVIN-RUNTIME.md` for Devin sessions
1. `docs/00-project/NORMATIVE_SOURCES.md`

Do not add Gemini above those runtime maps. Local-only deployment stays
[ADR-010](../../../../02-architecture/decisions/ADR-010-local-only-deployment.md).
