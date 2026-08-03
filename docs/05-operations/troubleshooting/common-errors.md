______________________________________________________________________

Version: 1.0.0
Status: active
Class: published
Owner: BioETL Team
Last verified: '2026-07-28'

______________________________________________________________________

# Troubleshooting — Common Error Patterns

Operator/developer playbook for frequent BioETL failures.

**Issue:** #6547 · **Companion:** [guides/troubleshooting.md](../../03-guides/troubleshooting.md) · **Local-only:** [ADR-010](../../02-architecture/decisions/ADR-010-local-only-deployment.md)

## Template (each pattern)

| Field | Meaning |
| --- | --- |
| **Symptoms** | What you observe |
| **Root causes** | Common why |
| **Diagnosis** | Commands / checks |
| **Resolution** | Fix |
| **Prevention** | Avoid recurrence |

---

## Import / module errors

### `ModuleNotFoundError` / `ImportError`

| | |
| --- | --- |
| **Symptoms** | `No module named bioetl...` or missing third-party package |
| **Root causes** | Wrong venv; incomplete `make install` / `uv sync`; running from wrong cwd |
| **Diagnosis** | `python -c "import bioetl; print(bioetl.__file__)"`; confirm `.venv` / `.venv-win` active |
| **Resolution** | `make install` or `uv sync`; use `uv run python -m bioetl ...` |
| **Prevention** | Document env activation in [quick-start](../../03-guides/quick-start.md) |

### Layer boundary / circular import

| | |
| --- | --- |
| **Symptoms** | Architecture test fail; circular import at runtime |
| **Root causes** | Application importing infrastructure adapters; domain importing application |
| **Diagnosis** | `make test-architecture`; `python -m scripts.engineering.qa.check_architecture` |
| **Resolution** | Move wiring to `composition/`; depend on ports in domain/application ([ADR-005](../../02-architecture/decisions/ADR-005-composition-layer-separation.md)) |
| **Prevention** | Architecture suite in CI; no new layer exceptions |

---

## Type / protocol errors

### `TypeError` / `AttributeError` in transforms

| | |
| --- | --- |
| **Symptoms** | Crash mid-transform on unexpected type/null |
| **Root causes** | Provider schema drift; missing null guards; wrong field mapping |
| **Diagnosis** | Stack frame + sample bronze record; compare Pandera schema |
| **Resolution** | Fix mapping/normalizer; add DQ/required field; re-run with `--limit` |
| **Prevention** | Contract tests; VCR cassettes for provider responses |

### mypy / Protocol mismatches

| | |
| --- | --- |
| **Symptoms** | `make lint` / mypy fails on ports |
| **Root causes** | Incomplete Protocol implementation; wrong constructor bag |
| **Diagnosis** | `uv run mypy src/bioetl/...` |
| **Resolution** | Align adapter with port; use identity bags at composition root |
| **Prevention** | Constructor bags over long kwargs ([ARCH-CR-06](https://github.com/SatoryKono/BioactivityDataAcquisition/issues/6868)) |

---

## Data / validation errors

### Pandera `SchemaError` / Gold strict fail

| | |
| --- | --- |
| **Symptoms** | Fail on Gold write; schema error not swallowed |
| **Root causes** | Column drift; null in non-null; type mismatch ([ADR-018](../../02-architecture/decisions/ADR-018-gold-strict-validation.md)) |
| **Diagnosis** | Error payload fields; `bioetl config show`; contract registry |
| **Resolution** | Fix transform; regenerate schema if SSOT changed; never catch-and-ignore Gold schema errors |
| **Prevention** | Contract CI; schema generation pipeline (ADR-037) |

### DQ threshold breach

| | |
| --- | --- |
| **Symptoms** | Exit DQ codes; soft/hard threshold messages |
| **Root causes** | Bad source batch; thresholds; new rule too strict |
| **Diagnosis** | [DQ cheatsheet](../../03-guides/cheatsheets/data-quality-rules.md); `bioetl dq validate --entity ... --show-rules`; quarantine inspect |
| **Resolution** | Fix data/transform **or** justified YAML threshold change **or** quarantine path |
| **Prevention** | No silent skip of invalid Silver rows (RULES §2.1) |

### Enum validation failures

| | |
| --- | --- |
| **Symptoms** | Unknown enum member |
| **Root causes** | Provider added value; YAML enum lag (ADR-038) |
| **Diagnosis** | Compare error value to `configs` enum YAML |
| **Resolution** | Extend enum YAML + tests; avoid hardcoding enums in code |

---

## State / test errors

### `AssertionError` in tests / flaky order

| | |
| --- | --- |
| **Symptoms** | Unit/integration assertion fails intermittently |
| **Root causes** | Non-deterministic sort; time/random; shared FS state |
| **Diagnosis** | Re-run with seed; check ADR-014 sort_by; isolate temp dirs |
| **Resolution** | Stabilize ordering; freeze clocks; clean fixtures |
| **Prevention** | [ADR-042](../../02-architecture/decisions/ADR-042-testing-strategy-matrix.md) test matrix |

### Operation order / side effects

| | |
| --- | --- |
| **Symptoms** | Lifecycle assertions fail (checkpoint/ledger) |
| **Root causes** | Resume path confusion (checkpoint vs ledger — ADR-046) |
| **Diagnosis** | `bioetl run-manifest show`; `bioetl checkpoint inspect` |
| **Resolution** | Use correct resume flags; clear stale local state carefully |

---

## Infrastructure / HTTP errors

### `ConnectionError` / `TimeoutError`

| | |
| --- | --- |
| **Symptoms** | Provider fetch fails |
| **Root causes** | Network; rate limit; circuit open (ADR-007/032) |
| **Diagnosis** | `bioetl health check --provider ...`; metrics/circuit state |
| **Resolution** | Retry/backoff; check API keys; wait circuit half-open |
| **Prevention** | Unified HTTP client; VCR for tests |

### VCR cassette mismatches

| | |
| --- | --- |
| **Symptoms** | Cassette not found / body mismatch |
| **Root causes** | API changed; filter headers; wrong mode |
| **Diagnosis** | Compare request path; cassette path under tests |
| **Resolution** | Re-record per project VCR skill policy; never commit secrets |
| **Prevention** | Deterministic filters in cassette config |

---

## Pipeline / write errors

### `PipelineNotFoundError`

| | |
| --- | --- |
| **Symptoms** | Unknown pipeline name |
| **Diagnosis** | `bioetl config list-pipelines` |
| **Resolution** | Fix name; ensure `configs/entities/{provider}/{entity}.yaml` exists |

### `LockNotAcquiredError`

| | |
| --- | --- |
| **Symptoms** | Cannot start run |
| **Root causes** | Concurrent same pipeline; crashed process left local lock |
| **Diagnosis** | Process list; `bioetl lock check` (local diagnostic only) |
| **Resolution** | Stop competing process; ADR-003 MemoryLock is process-local |
| **Prevention** | One runner per pipeline; graceful shutdown ADR-008 |

### Silver/Gold write failures

| | |
| --- | --- |
| **Symptoms** | Delta write/OSError; path missing |
| **Diagnosis** | [local-storage-layout](../../03-guides/local-storage-layout.md); disk space |
| **Resolution** | Create `data/` layout; fix permissions; vacuum if needed |
| **Prevention** | Local-only storage checks in getting-started |

### Quarantine routing surprises

| | |
| --- | --- |
| **Symptoms** | Rows in quarantine unexpected |
| **Diagnosis** | `bioetl quarantine ...`; [quarantine runbook](../runbooks/quarantine-management.md) |
| **Resolution** | Fix DQ/transform; replay; do not purge without policy |

---

## Performance

| Pattern | Diagnosis | Resolution |
| --- | --- | --- |
| Slow full extract | `--limit` smoke; provider rate limits | Batch size; cache bronze; composite enrich-only |
| Memory growth | Large frames; map_elements | Smaller batches; vectorized ops; stream writes |
| I/O contention | Many concurrent Delta writers | Serialize writers; local disk health |

See [performance-baselines](../performance-baselines.md).

---

## Related runbooks

| Topic | Link |
| --- | --- |
| Pipeline failure recovery | [runbooks/pipeline-failure-recovery.md](../runbooks/pipeline-failure-recovery.md) |
| DQ failure | [runbooks/pipeline-failure-dq.md](../runbooks/pipeline-failure-dq.md) |
| Incident response | [runbooks/incident-response.md](../runbooks/incident-response.md) |
| Stale lock | [runbooks/stale-lock.md](../runbooks/stale-lock.md) |
| CLI exit codes | [CLI cheatsheet](../../03-guides/cheatsheets/cli-commands.md) |

## See also

- [Guides troubleshooting](../../03-guides/troubleshooting.md)
- [DQ rules cheatsheet](../../03-guides/cheatsheets/data-quality-rules.md)
- [ADR matrix](../../03-guides/cheatsheets/adr-matrix.md)
