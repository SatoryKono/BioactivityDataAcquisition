# CODEX-RUNTIME.md — Navigation Pointer (Junie Tree)

> **Not a runtime SSOT.** This path is a navigation stub only.
>
> Per `scripts/ai/junie/junie-mirror-contract.json` →
> `runtime_only_files.codex_only`, the Codex peer runtime map is
> **Codex-only** and is **not** mirrored into `.junie/**`.

## Canonical sources

| Surface | Path | Role |
| --- | --- | --- |
| Codex peer runtime map | `.codex/agents/CODEX-RUNTIME.md` | Canonical Codex runtime map (Memory Provenance, task routing, risk validation) |
| Junie peer runtime map | `.junie/agents/JUNIE-RUNTIME.md` | Canonical Junie runtime map for this tree |
| Equal-peer entry | `AGENTS.md` | Repository-wide AI runtime precedence |

## Why this stub exists

Historically a truncated copy of the Codex runtime map lived here and drifted
silently (outside shared mirror parity scope). That copy is replaced by this
pointer so agents do not treat a divergent Junie file as Codex SSOT.

## Operator guidance

- For Codex identity and provenance env vars, read `.codex/agents/CODEX-RUNTIME.md`.
- For Junie runtime behavior, read `.junie/agents/JUNIE-RUNTIME.md`.
- Do not reintroduce a full content fork of CODEX-RUNTIME under `.junie/agents/`.
