# Gemini CLI Context for BioETL Project

This file contains the core architectural constraints, governance rules, and development standards for the BioETL project. Gemini CLI will automatically load and respect these instructions during every session.

## 0. Canonical Sources For AI Work

- `AGENTS.md`
- `.gemini/agents/GEMINI-RUNTIME.md`
- active `.gemini/agents/**` and `.gemini/skills/**` surfaces for the current task
- `docs/00-project/RULES.md`
- `docs/01-requirements/REQUIREMENTS.md`
- accepted ADRs in `docs/02-architecture/decisions/`
- `docs/00-project/ai/agents/guides/MEMORY_USAGE.md`
- `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`

When AI runtime guidance conflicts, use the list above in that order. For
implementation facts, verify against code, configs, tests, workflows, and
accepted ADRs before trusting memory or mirrors.

## 1. Core Architecture (Hexagonal / Ports & Adapters)

- **Strict Layer Isolation:** You MUST NOT import `infrastructure` modules into `domain` or `application` layers.
- **Domain Purity:** The `domain` layer MUST contain pure business logic (value objects, entities, contracts). NO I/O operations, NO file system access, NO HTTP clients (no `requests`, `httpx`, `aiohttp`).
- **Ports as Contracts:** Infrastructure depends on domain by design. All external dependencies MUST be abstracted via Protocols (`*Port` suffix) defined in `bioetl.domain.ports`.
- **Dependency Injection (DI):** All dependencies MUST be injected via the constructor (`__init__`). NEVER instantiate concrete adapters inside domain or application services. Assembly and factory logic MUST reside ONLY in `src/bioetl/composition/`.

## 2. Data Flow (Medallion Architecture)

- **Bronze:** Raw data extraction (JSONL + zstd), append-only.
- **Silver:** Cleaned, structured data stored in **Delta Lake**. Raw Parquet in Silver is strictly FORBIDDEN. Uses Merge/Upsert by `content_hash`.
- **Gold:** Aggregated data (Delta/Parquet) for analytics.
- **Loading Strategy:** `full_scan_only` is strictly for publication entities; all others MUST use `null` (default incremental) to enable checkpointing.
- **Data Types:** All JSON-like fields in Silver and Gold MUST be stored as canonical JSON strings or NULL if empty.

## 3. Operational & Coding Standards

- **Logging:** You MUST NOT use `print()`. Always use structured logging (`structlog`) via `LoggerPort`.
- **Type Hinting:** All public functions and methods MUST have explicit type hints. The codebase MUST pass `mypy --strict`. Avoid `Any` without a justifying comment.
- **Naming Conventions:**
  - Classes: Use project suffixes (`*Port`, `*Service`, `*Adapter`, `*Factory`).
  - Constants and Enum values MUST be `UPPER_SNAKE_CASE`.
  - Private attributes SHOULD use a single underscore prefix.
- **No Sentinel Values:** Do NOT use sentinel values like `-1`, `"N/A"`, or `9999`. Use `None` and `Optional`.
- **Determinism:** Do not use `datetime.now()` or `random` directly in infrastructure. Use `PipelineContext.started_at` to ensure reproducible pipeline runs.
- **Async I/O:** You MUST NOT use blocking I/O (like standard `open()` or `requests`) inside `async` functions.

## 4. Error Handling

- **Critical Errors:** (e.g., Auth failure, missing schema) MUST fail the pipeline immediately.
- **Recoverable Errors:** (e.g., HTTP 429, 5xx) MUST trigger exponential backoff retries.
- **Data Quality (DQ) Errors:** MUST be sent to a Quarantine sink without stopping the pipeline execution.

## 5. Testing & Validation

- **Coverage Target:** Test coverage MUST be ≥85%.
- **External Calls:** Unit tests MUST use in-memory fakes. Integration tests MUST use `VCR.py` for HTTP calls. Cassettes must be sanitized of secrets and stored in `tests/fixtures/vcr/{provider}/`.
- **Pre-commit Workflow:** Before and after making changes, you MUST run:
  - `make lint` (ruff, mypy)
  - `make test` (pytest)
- Do NOT weaken assertions to make tests pass; fix the underlying behavior instead.

## 6. Documentation & Configuration

- **Active Docs:** Active documentation lives in `docs/00-project` through `docs/05-operations`. Update relevant docs when modifying code contracts or architecture.
- **YAML Configs:** `configs/` YAML files are the canonical source of truth for pipelines. NEVER add secrets or credentials to tracked YAML files.

## 7. AI Workflows

- `.gemini/**` is the active Gemini runtime tree.
- `docs/00-project/ai/**` is a docs mirror/guidance layer and must not override runtime behavior.
- `.claude/**` is not a canonical runtime source for Gemini behavior unless it
  is explicitly verified in the local checkout for a separate change program.
- Before substantial work, read `docs/00-project/ai/memory/agent-memory.md`,
  then the relevant `memory-py-*.md` file, and use the canonical workflow from
  `src/memory/DAILY_WORKFLOW.md`.
- For write-capable work, follow
  `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md`.

- **make ai-review:** Run `py-review-orchestrator` to perform a code review on staged changes.
- **make ai-test:** Run `py-test-swarm` to generate missing test coverage.
- **make ai-docs:** Run `bioetl-documentation-audit` skill to audit docs.

*Remember: Gemini is Jules, a Senior Software Engineer. Adhere to these guidelines strictly.*
