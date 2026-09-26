# План работ: Shared MCP plane (actualized)

*Status: working execution plan (non-normative)*
*Date: 2026-07-24*
*Program: GitHub #6563*
*Related:*
  - [mcp-shared-http-multi-client-plan-2026-07-24.md](./mcp-shared-http-multi-client-plan-2026-07-24.md)
  - [mcp-shared-http-multi-client-issue-pack-2026-07-24.md](./mcp-shared-http-multi-client-issue-pack-2026-07-24.md)
  - Policy: `docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md`
  - Policy: `docs/00-project/ai/agents/policy/MCP_LOCAL_RUNTIME_CONFIG.md`

---

## 1. Цель и критерий успеха

### 1.1 Цель

Один long-lived **Streamable HTTP** endpoint на логический MCP-сервер;
Grok + Cursor + Codex + Gemini + VS Code → **один** процесс/контейнер на сервер
(без N× stdio / Docker Toolkit thrash).

### 1.2 Success metrics (из program plan)

| # | Метрика | Target |
|---|---------|--------|
| M1 | ≥2 AI-клиента на shared server | ≤1 host process / container на server |
| M2 | Migrated servers | 0 random-name Docker orphans (`docker-mcp-name=…`) |
| M3 | Portable SSOT | Tracked `.mcp.json` остаётся full **stdio** |
| M4 | Smoke / checks | `protocol_smoke` HTTP + stdio regression green |
| M5 | Tech-debt budgets | не увеличиваются |
| M6 | #6293 | нет long-lived **stdio** Compose keepalive |

### 1.3 Non-goals (этот план)

- Multi-replica / load-balancer MCP.
- Compose + `container_name` как default (только optional Mode B позже).
- Перенос всех 21 серверов в одном PR.
- Multi-machine / multi-tenant gateway.
- Возврат long-lived stdio Compose (#6293).
- Shared plane для T3 Toolkit (`jetbrains`, `node-code-sandbox`) — только disable.

---

## 2. Baseline (факт на 2026-07-24, post apply)

### 2.1 Уже сделано (live + code)

| Область | Состояние |
|---------|-----------|
| Host shared plane | 5 серверов: 8811 brave, 8813 adr, 8814 deja, 8815 context7, 8816 ast-grep |
| Lifecycle | `start-shared` / `stop-shared` / `health-shared` / `shared-servers.json` |
| Generator | `setup_mcp.py --profile shared --transport-mode shared` |
| Apply | `apply-docker-stable-mcp.ps1 -Profile shared -TransportMode shared` |
| Grok | `apply-shared-to-grok.ps1` + HTTP URL; thrash gateways disabled |
| Clients home | `MCP_DOCKER` full catalog убран (Cursor/Codex/Gemini/VS Code) |
| Toolkit | `jetbrains` + `node-code-sandbox` сняты с profile `default` |
| Orphans | jetbrains/sandbox count = 0 после cleanup |
| Policy SSOT | `MCP_SHARED_RUNTIME.md` |
| Protect cleanup | `bioetl-*` / `bioetl.mcp.shared` (не трогать shared) |

### 2.2 Известные пробелы baseline

| ID | Пробел |
|----|--------|
| G1 | Клиенты могут ещё не быть restarted → configs не загружены |
| G2 | Нет formal dual-client proof (M1) |
| G3 | `apply-shared-to-grok`: после `-DisableDockerGateways` часть shared могла остаться `enabled=false` (ручной fix) |
| G4 | `start-shared`: гонка `npx` cache (context7 ENOENT при параллельном cold start) |
| G5 | `health-shared` иногда долго/«висит» без per-server timeout |
| G6 | Нет unit/smoke на HTTP path generator + protocol |
| G7 | ~16 T2 серверов ещё **stdio-only** (thrash при multi-client) |
| G8 | GitHub issues #6563–#6569 не closed / acceptance не отмечены |
| G9 | Lesson / DOCKER_QUICKSTART могут отставать от live workflow |
| G10 | Mode B Compose не нужен сейчас; зафиксировать отказ от «container_name = optimum» |

---

## 3. Архитектурные опоры (не пересматривать без ADR)

```text
  Grok / Cursor / Codex / Gemini / VS Code
           |  type: http  url=http://127.0.0.1:88xx/mcp
           v
  mcp-proxy@6.5.4 (host)  ──► 1× wrapper.ps1 ──► 1× server
           ^
  start-shared.ps1 / stop-shared.ps1 / health-shared.ps1
  catalog: scripts/ops/runtime/mcp/shared-servers.json
```

| Правило | Деталь |
|---------|--------|
| Transport v1 | Streamable HTTP only на plane |
| Bind | `127.0.0.1` only |
| Portable tracked | always `transport-mode stdio` |
| Local projections | `shared` / `hybrid` |
| Docker native images | optional Mode B later: `bioetl-mcp-<name>`, label `bioetl.mcp.shared=true` |
| Toolkit T3 | disable, не wrap |

---

## 4. Волны работ (W0 → W5)

Каждая волна: **deliverables → acceptance → deps → estimate → risks**.

```text
W0  Operator verify (no code)          ─── block smoke
W1  Hardening fixes (B1–B3)            ─── block reliability
W2  Close P0/P1 acceptance (tests)     ─── block program close
W3  Expand thrash-heavy (P2 partial)   ─── cut remaining stdio thrash
W4  Docs / GitHub closeout             ─── ops + governance
W5  Optional Mode B / auth / watchdog  ─── only if needed
```

---

### W0 — Operator verification (P0 ops)

**Цель:** подтвердить, что live multi-client path работает после apply.

| Task | Owner | Steps | Acceptance |
|------|-------|-------|------------|
| **W0.1** Restart all AI clients | Operator | Полный exit Grok/Cursor/Codex/Gemini/VS Code → start | Процессы новые; MCP reload |
| **W0.2** Health | Operator | `.\scripts\ops\runtime\mcp\health-shared.ps1` | 5/5 OK; `/ping` 200 |
| **W0.3** Dual-client smoke | Operator | 2 клиента вызывают tool `context7` (или `brave-search`) | ≤1 listener на 8815/8811; нет второго npx child «пакета» |
| **W0.4** Toolkit regression | Operator | `docker ps` filter `docker-mcp-name=jetbrains\|node-code-sandbox` | count = 0 |
| **W0.5** No MCP_DOCKER | Operator | home configs Cursor/Codex/Gemini/VS Code | нет `gateway run --profile default` |

**Deps:** plane already up.
**Estimate:** 30–60 min.
**Exit:** checklist W0 signed → можно W1/W2.

**Failure playbook:**

1. Plane down → `start-shared.ps1`
2. Client still stdio → re-run `setup_mcp --profile shared --transport-mode shared` + `apply-shared-to-grok.ps1` + restart
3. Orphans back → `cleanup-mcp-orphans.ps1 -KillHostGateways` + проверить Toolkit profile

---

### W1 — Reliability fixes (code, P1)

**Цель:** plane start/apply идемпотентны и не ломают enabled/cache.

#### W1.1 Fix `apply-shared-to-grok.ps1` enabled semantics

| Item | Detail |
|------|--------|
| Problem | Shared blocks иногда `enabled=false`; `-DisableDockerGateways` regex может пересекаться с соседними блоками / partial match |
| Work | 1) После rewrite shared: assert `enabled = true` для catalog names. 2) Disable gateways только по точному section-replace (не bare `enabled=true` multiline). 3) Unit/fixture test на sample `config.toml` |
| Files | `scripts/ops/runtime/mcp/apply-shared-to-grok.ps1`, optional `tests/...` or `scripts/ops/runtime/mcp/tests/` |
| Acceptance | Re-apply on backup fixture → all 5 shared `enabled=true` + url; docker/mermaid/… `enabled=false` only |
| Estimate | 0.5–1 d |

#### W1.2 Harden `start-shared.ps1` against npx thrash

| Item | Detail |
|------|--------|
| Problem | Parallel `npx -y` cold start → ENOENT under `npm-cache\_npx\…` (context7) |
| Work | 1) Sequential start (or lockfile). 2) Pre-warm `mcp-proxy@6.5.4` once. 3) Per-server `NPM_CONFIG_CACHE` under `logs/mcp-shared/npm-cache/<name>` or shared warm cache. 4) Increase settle for first boot; retry 1× on early exit |
| Files | `scripts/ops/runtime/mcp/start-shared.ps1` |
| Acceptance | Cold `stop-shared` + `start-shared` → 5/5 started without manual cache delete |
| Estimate | 0.5–1 d |

#### W1.3 `health-shared.ps1` timeouts

| Item | Detail |
|------|--------|
| Problem | Полный health может «висеть» |
| Work | Per-server TCP + HTTP timeout (e.g. 3s); non-zero exit + JSON summary always written |
| Files | `scripts/ops/runtime\mcp\health-shared.ps1` (+ `.sh` parity) |
| Acceptance | Worst-case wall clock ≤ N×timeout + overhead; exit code reflects down count |
| Estimate | 0.25–0.5 d |

**W1 exit:** cold start green + grok apply fixture green + health bounded.

---

### W2 — Program P0/P1 acceptance (tests + proof)

**Цель:** закрыть acceptance #6565 / #6566 / #6568 / #6564 без расширения inventory.

#### W2.1 Generator tests (`#6568`)

| Work | Acceptance |
|------|------------|
| Unit: `transport-mode stdio` → no localhost 88xx rewrite on portable | Default unchanged |
| Unit: `shared` → only catalog servers → `http://127.0.0.1:…` | Allowlist enforced |
| Unit: tracked `.mcp.json` path always stdio | Portable SSOT |
| Hybrid: catalog HTTP, others stdio | Documented |

**Files:** `scripts/ai/codex/setup_mcp.py`, existing test suite under `tests/` or `scripts/ai/codex/`.

#### W2.2 Cleanup protect proof (`#6566`)

| Work | Acceptance |
|------|------------|
| Documented manual or automated: fake container `bioetl-mcp-dummy` + label `bioetl.mcp.shared=true` survives `cleanup-mcp-orphans` | Not removed |
| Foreign `docker-mcp=true` random still removed | Removed |

#### W2.3 Protocol smoke HTTP (`#6564`)

| Work | Acceptance |
|------|------------|
| Extend smoke to hit `http://127.0.0.1:8813/mcp` (or catalog) initialize/list-tools when plane up | Green when plane up; skip/xfail documented when down |
| Stdio path still green | No regression |

#### W2.4 Dual-client formal evidence (`#6564` / M1)

| Work | Acceptance |
|------|------------|
| Capture evidence (process list / port owners) for 2 clients × 1 server | Attached to issue #6564 / #6563 |

**W2 estimate:** 1–2 d.
**W2 exit:** issues P0/P1B/P1A/P1C can be closed or marked ready-to-close.

---

### W3 — Expand plane (P2 thrash cut)

**Цель:** снять оставшийся multi-client stdio thrash по ROI.

### 3.1 Priority tiers

| Tier | Servers | Why | Suggested ports |
|------|---------|-----|-----------------|
| **T3a (next)** | `docker`, `mermaid` (optional `dockerhub`) | Host gateway thrash; Grok already had wrappers | 8817, 8818, (8819) |
| **T3b** | `github`, `fetch` | Frequent wrappers | 8820, 8821 |
| **T3c** | `prometheus`, `grafana` | Ops profile | 8822, 8823 |
| **T3d** | `neo4j-cypher`, `neo4j-memory` | After neo4j auth healthy | 8824, 8825 |
| **T3e** | `memory`, `filesystem` | Stateful — design roots first | Deferred (design-first approach) |
| **Defer** | `mutmut`, `code-analyzer`, `github-actions`, `mcp-code-interpreter` | Lower thrash / cost | later |
| **Never on plane** | `jetbrains`, `node-code-sandbox` | T3 Toolkit; disable only | — |

### 3.2 Per-server work item template

For each server:

1. Confirm wrapper stdio works standalone.
2. Add entry to `shared-servers.json` (port, wrapper, class, priority).
3. Keep port map in sync in `setup_mcp.py` SHARED endpoints table.
4. `start-shared` starts it; `health-shared` pings.
5. Generator emits HTTP in `shared` mode.
6. Grok apply catalog-driven (no hardcode list drift).
7. Smoke tool call once.
8. Update `MCP_SHARED_RUNTIME.md` matrix row → Phase N.

### 3.3 Special: docker / mermaid

| Option | Pros | Cons |
|--------|------|------|
| A. Each behind own mcp-proxy | Simple, matches Phase 1 | 2 proxies + 2 gateways still |
| B. One shared gateway process exposing both (if toolkit allows) | Fewer processes | Coupling; not in current catalog model |
| **Recommend A** for consistency with Phase 1 |

**Constraint:** gateway must speak MCP over stdio to proxy; clients only see HTTP.
**Do not** re-enable full `MCP_DOCKER --profile default`.

### 3.4 W3 batches

| Batch | Scope | Estimate | Exit |
|-------|-------|----------|------|
| **W3.1** | docker + mermaid (+ dockerhub if needed) | 1–2 d | 2 clients, ≤1 gateway container/process each |
| **W3.2** | github + fetch | 1 d | same |
| **W3.3** | prometheus + grafana (ops) | 1 d | optional profile `ops` shared |
| **W3.4** | neo4j-* after auth fix | 1 d | depends neo4j healthy |
| **W3.5** | memory/filesystem design note only | 0.5 d | ADR/note before implement |

**W3 exit:** ≥7 shared servers or all daily multi-client set; lesson updated.

---

### W4 — Docs, ops playbook, GitHub closeout

| Task | Deliverable | Acceptance |
|------|-------------|------------|
| **W4.1** DOCKER_QUICKSTART shared section | Actualized commands (start → apply → restart → health) | Matches scripts |
| **W4.2** Lesson `docker-desktop-wsl-stability-32gib` | Shared plane + Toolkit disable | Linked from policy |
| **W4.3** OPS playbook (#6567) | One page: thrash recovery, what not to kill | Operator can recover without agent |
| **W4.4** Decision log: Compose `container_name` | «Not default; Mode B optional» in plan/policy | No re-open thrash |
| **W4.5** Close/update GitHub #6563–#6569 | Evidence links, checkboxes | States reflect reality |
| **W4.6** Inventory scripts registry | If new scripts — lifecycle registry | CI inventory clean |

**Estimate:** 0.5–1.5 d.
**Deps:** W0–W2 ideally; W4.1–W4.3 can start after W0.

---

### W5 — Optional hardening (only if triggered)

| Trigger | Work |
|---------|------|
| Unauthorized loopback concern | mcp-proxy API key + client headers |
| Residual Toolkit enablement | Detect script: profile still has bad servers → warn |
| Memory pressure | Idle shutdown / watchdog for plane PIDs |
| Docker-native server only | Mode B: `docker-compose.mcp-shared.yml`, `container_name: bioetl-mcp-<name>`, `127.0.0.1:88xx`, health `/ping`, **HTTP only** |
| Multiplex desire | Single reverse-proxy in front of plane — separate design |

**Do not start W5 without explicit need.**

---

## 5. Dependency graph

```text
W0 (verify)
 ├─► W1 (fixes) ──► W2 (tests/proof) ──► close P0/P1 issues
 │                      │
 │                      └─► W4 (docs/closeout)
 └─► W3.1 thrash gateways (can parallel W2 after W1.2)
         └─► W3.2+ expand
                └─► W4.5 umbrella close
W5 optional after W3/W4
```

Critical path: **W0 → W1 → W2 → W4.5**.
Value path for thrash: **W0 → W1.2 → W3.1**.

---

## 6. Work breakdown (checklist)

### Wave 0 — Operator

- [ ] W0.1 Restart all five clients *(operator — required for clients to load HTTP)*
- [x] W0.2 `health-shared` daily 12/12 *(plane green 2026-07-24; neo4j excluded)*
- [x] W0.3 Single-instance proof *(1 listener/port; evidence `logs/mcp-shared/single-instance-evidence.md`)*
- [x] W0.4 No jetbrains/sandbox containers *(0/0)*
- [x] W0.5 No `MCP_DOCKER` full gateway in home configs *(clean)*

### Runtime R1

- [x] R1 daily catalog start (no neo4j) health green *(12/12, 2026-07-24)*

### Wave 1 — Code fixes

- [x] W1.1 Grok apply enabled=true + safe disable gateways + fixture
- [x] W1.2 start-shared sequential/pre-warm/retry
- [x] W1.3 health-shared per-server timeout
  *(implemented 2026-07-24: section-scoped regex, npm-cache prewarm, health timeouts)*

### Wave 2 — Acceptance

- [x] W2.1 setup_mcp transport-mode unit tests *(stdio/shared/hybrid + localhost reject; 2026-07-24)*
- [x] W2.2 cleanup protect proof *(bioetl-mcp-protect-probe + label survives cleanup; 2026-07-24)*
- [x] W2.3 protocol_smoke HTTP *(smoke_http_server + unit tests; live optional)*
- [ ] W2.4 Dual-client evidence on issues *(operator: restart clients + proof)*

### Wave 3 — Expand

- [x] W3.1 docker + mermaid (+ dockerhub) *(catalog 8817–8819; 2026-07-24)*
- [x] W3.2 github + fetch *(8820–8821)*
- [x] W3.3 prometheus + grafana *(8822–8823)*
- [x] W3.4 neo4j-* *(catalog 8824–8825; optional daily — auth dependent)*
- [x] W3.5 memory/filesystem design gate *(documented deferred in MCP_SHARED_RUNTIME)*

### Wave 4 — Docs / GH

- [x] W4.1 DOCKER_QUICKSTART
- [x] W4.2 Lesson 32 GiB
- [x] W4.3 OPS playbook (`scripts/ops/runtime/mcp/OPERATOR.md`)
- [x] W4.4 Compose decision note (MCP_SHARED_RUNTIME Mode B)
- [ ] W4.5 GitHub issue closeout *(needs `gh` + operator evidence W0/W2.4)*
- [ ] W4.6 scripts inventory if required by CI registry

### Wave 5 — Optional hardening

- [x] Auth token *(optional `BIOETL_MCP_SHARED_API_KEY` → mcp-proxy --apiKey; 2026-07-24)*
- [ ] Toolkit detector *(still open)*
- [x] Plane watchdog *(`watchdog-shared.ps1 -Daily`)*
- [x] Mode B compose skeleton *(`docker-compose.mcp-shared.yml`, empty services)*
- [x] Loopback bind *(`--host 127.0.0.1` in start-shared)*
- [x] Daily profile *(`start-shared.ps1 -Daily` excludes neo4j-*)*

---

## 7. Mapping to GitHub issues

| Wave | Issues | Close when |
|------|--------|------------|
| W0 + W4.3 | #6567 OPS | Playbook + operator can recover |
| W2.x + docs matrix | #6565 P0 | Matrix + policy accepted |
| W1 + W2.2 | #6566 P1A | Skeleton stable + protect proof |
| W2.1 | #6568 P1B | Tests green |
| W0.3 + W2.3–W2.4 | #6564 P1C | MVP multi-client proven |
| W3 + W4.1–W4.2 | #6569 P2 | Expand + daily workflow docs |
| All P1 + OPS | #6563 Umbrella | Child issues closed / linked evidence |

---

## 8. PR sequence (recommended)

| PR | Title | Wave | Risk |
|----|-------|------|------|
| **PR-A** | fix(mcp-shared): grok apply enabled + start-shared npx harden + health timeouts | W1 | Low |
| **PR-B** | test(mcp): transport-mode shared/stdio + HTTP smoke | W2 | Low |
| **PR-C** | feat(mcp-shared): docker+mermaid on shared plane | W3.1 | Med (gateway) |
| **PR-D** | docs(mcp): shared plane ops + lesson + compose decision | W4 | Low |
| **PR-E+** | expand remaining T2 servers (batched) | W3.2–W3.4 | Med |

Rules:

- One concern per PR where possible.
- No debt budget increases.
- No `.env` edits without explicit approval.
- Tracked `.mcp.json` stays portable stdio.
- Post-change: `health-shared` + relevant tests; report skipped checks.

---

## 9. Daily operator runbook (target end-state)

```powershell
# Boot / after reboot
cd E:\g-drive\05_AI\github\BioactivityDataAcquisition
.\scripts\ops\runtime\mcp\start-shared.ps1
.\scripts\ops\runtime\mcp\health-shared.ps1

# After pulling generator/catalog changes
$env:PYTHONPATH = (Resolve-Path .).Path
python scripts/ai/codex/setup_mcp.py --profile shared --transport-mode shared --skip-codex-validation
.\scripts\ops\runtime\mcp\apply-shared-to-grok.ps1 -DisableDockerGateways
# restart AI clients once

# Thrash recovery (AI idle preferred)
.\scripts\ops\runtime\docker\cleanup-mcp-orphans.ps1 -KillHostGateways

# Stop plane
.\scripts\ops\runtime\mcp\stop-shared.ps1
```

Fallback single-client stdio:

```powershell
python scripts/ai/codex/setup_mcp.py --profile stable --transport-mode stdio --skip-codex-validation
```

---

## 10. Risks and mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Clients not restarted | Shared configs ignored; thrash returns | W0 mandatory; docs emphasize full restart |
| Toolkit re-enabled in Desktop UI | jetbrains/sandbox orphans | W0.4; optional W5 detector; cleanup |
| npx cache corruption | Plane partial start | W1.2 sequential + pre-warm |
| Grok enabled=false | Silent missing tools | W1.1 assert |
| Gateway servers hard to HTTP-wrap | W3.1 slips | Spike 0.5 d before PR-C |
| neo4j auth unhealthy | Blocks neo4j MCP share | Fix neo4j health first |
| Scope creep (all 21) | Never ship | Tiers; stop after daily set |
| Compose Mode B misused as stdio | #6293 regression | W4.4 decision; HTTP-only gate |
| Parallel multi-PR inventory drift | Port collisions | Single catalog `shared-servers.json` SSOT |

---

## 11. Effort summary (rough)

| Wave | Effort | Calendar (1 engineer) |
|------|--------|------------------------|
| W0 | 0.5 d | Day 0 |
| W1 | 1–2 d | Day 1–2 |
| W2 | 1–2 d | Day 2–4 |
| W3.1 | 1–2 d | Day 4–6 |
| W3.2–W3.4 | 2–4 d | Week 2 |
| W4 | 0.5–1.5 d | Parallel after W2 |
| W5 | optional | later |
| **MVP close (W0–W2+W4 partial)** | **~3–5 d** | |
| **Daily multi-client hardened (to W3.1)** | **~5–8 d** | |

---

## 12. Definition of Done (program slice)

Program slice «multi-client daily» считается done, когда:

1. W0 checklist green on operator host.
2. W1 fixes merged.
3. W2 tests + dual-client evidence attached to #6564.
4. Plane ≥ Phase 1 five servers stable cold-start.
5. W3.1 (docker/mermaid) done **or** explicitly deferred with residual thrash accepted.
6. Docs (W4.1–W4.3) match commands.
7. #6563 children closed or re-scoped with dates.
8. No tech-debt budget increase; no #6293 stdio Compose.

---

## 13. Immediate next actions (ordered)

1. **Operator:** W0.1–W0.5 (restart + dual-client proof).
2. **Dev:** PR-A = W1.1 + W1.2 + W1.3.
3. **Dev:** PR-B = W2.1 + W2.3.
4. **Dev:** PR-C = W3.1 after spike gateway HTTP wrap.
5. **Docs/GH:** W4 in parallel after W0.

---

## 14. Related paths (quick index)

| Path | Role |
|------|------|
| `scripts/ops/runtime/mcp/*` | Plane lifecycle |
| `scripts/ops/runtime/mcp/shared-servers.json` | Port/catalog SSOT |
| `scripts/ai/codex/setup_mcp.py` | Local projections |
| `scripts/ops/runtime/docker/apply-docker-stable-mcp.ps1` | One-shot apply |
| `scripts/ops/runtime/docker/cleanup-mcp-orphans.ps1` | Orphan cleanup |
| `scripts/ops/runtime/mcp/apply-shared-to-grok.ps1` | Grok HTTP projection |
| `docs/00-project/ai/agents/policy/MCP_SHARED_RUNTIME.md` | Design SSOT |
| `docs/DOCKER_QUICKSTART.md` | Operator entry |

---

*End of execution plan.*
