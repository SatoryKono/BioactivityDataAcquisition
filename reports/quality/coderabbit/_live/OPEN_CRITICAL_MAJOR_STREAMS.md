# Open CodeRabbit residual — CRITICAL + MAJOR

Live `gh` snapshot, repo `SatoryKono/BioactivityDataAcquisition`.

| Class | Open |
|-------|-----:|
| **critical path-cluster** | **0** |
| **major path-cluster** | **0** |
| **TOTAL C+M path-clusters** | **0** |

## CRITICAL path-clusters

_Нет открытых critical residual path-cluster issues._

## MAJOR path-clusters

_Нет открытых major residual path-cluster issues._

Все path-cluster issues вида `[CR-FULL][Wave *][critical|major] residual in \`path\`` закрыты
(application/core, domain, storage, observability, batch, transformer, publication, …).

## Campaign / follow-up open (не C/M path-cluster)

| # | Title | Stream |
|--:|-------|--------|
| **#7688** | `[CR-FULL][meta]` Exhaustive CodeRabbit residual audit campaign | C0 epic (parent) |
| **#7694** | Wave E: contracts, normative docs, Grafana surfaces | C1 Wave E |
| **#8031** | Wave E CLI residual blocked: docs/grafana/scripts ignored | C1 Wave E |
| **#7695** | Wave F: test honesty residual | C2 Wave F |
| **#8032** | Wave F CLI residual blocked: tests ignored | C2 Wave F |
| **#7946** | Retry rate-limited domain residual leaves | C3 domain retry |
| **#7698** | CodeRabbit CLI secret and trusted workflow health | C4 secret/workflow |
| **#7697** | Campaign closeout: re-audit + FINAL.md + tag | C5 closeout |
| **#6988** | DSA-06 Dependency Health residual (Grafana) | C-extra (не CR path-cluster) |

## 5 независимых потоков (campaign backlog)

Path-cluster **critical/major исчерпаны**. Ниже — потоки на оставшийся CR-FULL campaign follow-up:

```
C1 Wave E (docs/contracts/grafana) ──┐
C2 Wave F (tests)                  ──┼── parallel
C3 Domain rate-limit retry         ──┤
C4 CR CLI secret / workflow        ──┤
C5 Closeout FINAL                  ──┘  (после C1–C4)
```

| Stream | Issues | Notes |
|--------|--------|-------|
| **C1 Wave E** | #7694, #8031 | contracts / normative docs / Grafana; #8031 = CLI “All files ignored” |
| **C2 Wave F** | #7695, #8032 | test honesty; #8032 = CLI tests scope blocked |
| **C3 domain retry** | #7946 | rate-limited domain residual leaves |
| **C4 secret/workflow** | #7698 | CR CLI secret + trusted workflow health |
| **C5 closeout** | #7697 | re-audit fixed scopes + FINAL.md + tag — **last** |

**C0 epic #7688** — parent; закрывать после дочерних.  
**#6988 DSA-06** — смежный residual, не CR-FULL path-cluster severity queue.

## Правила

1. **Critical/major path-clusters = 0** — implement-streams по findings закрыты.
2. C1 ∥ C2 ∥ C3 ∥ C4 можно параллелить; **C5 — после** них.
3. #7688 — epic, не параллельный implement-stream.
4. Не увеличивать бюджеты техдолга.
