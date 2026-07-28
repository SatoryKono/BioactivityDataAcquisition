# Shared MCP multi-client — GitHub issue pack

*Status: Working planning artifact (non-normative)*
*Created: 2026-07-24*
*Primary plan: [mcp-shared-http-multi-client-plan-2026-07-24.md](./mcp-shared-http-multi-client-plan-2026-07-24.md)*

## Suggested dependency order

1. Umbrella (tracking)
2. OPS playbook (can ship in parallel with P0)
3. Phase 0 discovery/docs
4. Phase 1A runtime skeleton + protect allowlists
5. Phase 1B generator transport-mode
6. Phase 1C first shared server MVP
7. Phase 2 expand + ergonomics

Labels (existing): `mcp`, `ai-runtime`, `infrastructure`, `runtime`, `documentation`, `governance`, `developer-experience`, `priority:P1` / `priority:P2` / `P1`, `technical-debt` only if debt is reduced.

Guardrails for every issue:

- Do not edit `.env` / `.env.*` without explicit user approval
- Do not increase tech-debt budgets
- Do not reintroduce long-lived stdio MCP Compose (#6293)
- Tracked `.mcp.json` stays portable full stdio SSOT unless separate ADR
- Localhost-only for shared endpoints

---

## Issue 0 — Umbrella

### Title

`[MCP][P1] Shared HTTP plane for multi-client AI sessions (stop stdio thrash)`

### Summary

Umbrella for moving high-thrash BioETL MCP servers from per-client stdio to a localhost Streamable HTTP shared plane so multiple Grok/Cursor sessions do not multiply npx/docker children.

### Acceptance

- [ ] Child issues linked and sequenced
- [ ] Plan `docs/plans/mcp-shared-http-multi-client-plan-2026-07-24.md` referenced
- [ ] Live thrash evidence captured in issue body

---

## Issue OPS — Operator thrash (immediate)

### Title

`[MCP][P1] Operator playbook: single heavy client + Desktop Toolkit off + orphan cleanup`

### Summary

Document and optional script for host recovery while code path is still stdio-only. Explains why profile `stable` alone does not kill live duplicates.

### Scope

- Playbook in plan / DOCKER_QUICKSTART / lesson cross-link
- Optional: `scripts/ops/runtime/docker/reset-mcp-host-sessions.ps1` (kill extra grok? **dangerous** — default WhatIf; require explicit flags)
- Checklist: one grok, restart client, disable Toolkit jetbrains/sandbox, `cleanup-mcp-orphans -KillHostGateways`

### Non-goals

- Shared HTTP implementation
- Killing bioetl/neo4j

### Acceptance

- [ ] Documented steps operators can run today
- [ ] Clear warning that live clients respawn MCP after kill
- [ ] No silent kill of BioETL compose

---

## Issue P0 — Discovery

### Title

`[MCP][P1] Phase 0: transport matrix + MCP_SHARED_RUNTIME.md design SSOT`

### Summary

Classify all 21 servers and AI clients; write design SSOT; pick ≤4 Phase-1 candidates with host thrash prioritized.

### Scope

- `MCP_SHARED_RUNTIME.md`
- Pointer in `MCP_LOCAL_RUNTIME_CONFIG.md`
- Matrix tables (transport class T1–T4, client HTTP support)
- Priority list including host npx thrash leaders

### Acceptance

- [ ] Matrix complete for 21 servers
- [ ] Client support table for Cursor + Grok/Codex
- [ ] Explicit Phase-1 shortlist
- [ ] Security bind 127.0.0.1 documented

---

## Issue P1A — Runtime skeleton

### Title

`[MCP][P1] Shared MCP runtime skeleton (start/stop/health) + protect bioetl-mcp-* in cleanup`

### Summary

Add `scripts/ops/runtime/mcp/*` lifecycle scripts and ensure orphan cleanup / ensure-stable never destroy shared named services.

### Scope

- start/stop/health + README
- status artifact `logs/mcp-shared/status.json` (or under logs/)
- Allowlist updates: `cleanup-mcp-orphans.ps1`, `ensure-stable.ps1` Stop-ForeignContainers
- Optional empty compose project placeholder **without** starting stdio keepalive containers

### Acceptance

- [ ] Scripts exist and are documented
- [ ] cleanup/ensure-stable tests or manual proof do not remove `bioetl-mcp-*` / label `bioetl.mcp.shared=true`
- [ ] No #6293-style stdio Compose keepalive

---

## Issue P1B — Generator

### Title

`[MCP][P1] setup_mcp --transport-mode shared + localhost URL allowlist`

### Summary

Extend generator to emit `type: http` localhost URLs for shared-enabled servers on local projections only; keep portable SSOT stdio.

### Scope

- `--transport-mode stdio|shared|hybrid` (default stdio)
- `APPROVED_LOCAL_MCP_BASE_URL_PREFIXES`
- Profile or membership flag for shared-capable servers
- Unit tests

### Acceptance

- [ ] Default generation unchanged (stdio)
- [ ] Shared mode emits HTTP only for allowlisted local prefixes
- [ ] Tracked full inventory remains portable stdio
- [ ] Tests cover both modes

---

## Issue P1C — First shared server MVP

### Title

`[MCP][P1] MVP: share first high-thrash MCP server over Streamable HTTP`

### Summary

Implement one shared server end-to-end (prefer host thrash leader from Phase 0 matrix, or brave if Docker path is ready). Verify multi-client ≤1 process.

### Scope

- Bridge or native HTTP for chosen server
- Wire into start-shared + generator shared mode
- protocol_smoke HTTP path
- Manual dual-client proof

### Acceptance

- [ ] ≥2 clients → ≤1 process/container for that server
- [ ] Orphan cleanup does not kill shared instance
- [ ] Smoke green; stdio path still works

---

## Issue P2 — Expand

### Title

`[MCP][P2] Expand shared plane + profile shared + apply helper + operator docs`

### Summary

Add more servers; profile `shared`; wire `apply-docker-stable-mcp`; update lesson and DOCKER_QUICKSTART.

### Acceptance

- [ ] ≥2 thrash-heavy servers on shared plane
- [ ] Documented daily multi-client workflow
- [ ] Lesson `docker-desktop-wsl-stability-32gib` updated
- [ ] Debt budgets unchanged

---

## Mapping to plan PR sequence

| Pack issue | Plan PR |
| --- | --- |
| P0 | PR1 |
| P1A | PR2 |
| P1B + P1C | PR3 |
| P2 | PR4–PR5 |
| OPS | can land anytime |

## Created GitHub issues (2026-07-24)

| Pack | GitHub | Title |
| --- | --- | --- |
| Umbrella | [#6563](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6563) | Shared HTTP plane for multi-client AI sessions |
| OPS | [#6567](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6567) | Operator playbook |
| P0 | [#6565](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6565) | Transport matrix + MCP_SHARED_RUNTIME.md |
| P1A | [#6566](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6566) | Runtime skeleton + protect bioetl-mcp-* |
| P1B | [#6568](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6568) | setup_mcp --transport-mode shared |
| P1C | [#6564](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6564) | First shared server MVP |
| P2 | [#6569](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6569) | Expand + profile shared + docs |
