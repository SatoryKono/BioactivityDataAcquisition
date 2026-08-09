# Agent Memory — Navigation Entry Point

## Evaluation Metadata
- **Category:** Memory Sheets
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/memory/agent-memory.md

## Evaluation Breakdown
- Clarity: 9/10 (weight: 0.15)
- Completeness: 8/10 (weight: 0.15)
- Specificity: 9/10 (weight: 0.12)
- Context: 9/10 (weight: 0.10)
- Guardrails: 9/10 (weight: 0.10)
- Maintainability: 9/10 (weight: 0.08)
- Reusability: 9/10 (weight: 0.08)
- Error Handling: 9/10 (weight: 0.08)
- Validation: 9/10 (weight: 0.07)
- Documentation: 9/10 (weight: 0.07)

## Original Content

______________________________________________________________________

Version: 2.0.0
Status: active
Class: internal-published
Owner: BioETL Team
Last verified: '2026-08-07'

______________________________________________________________________

# Agent memory — navigation entry point

This file is a compact navigation aid, not a behavioral or governance source.
When memory conflicts with the current checkout, follow the precedence in
`AGENTS.md` and `docs/00-project/NORMATIVE_SOURCES.md`.

## Minimum task bootstrap

Before planning, auditing, or editing:

1. Read `AGENTS.md`.
1. Read `docs/00-project/NORMATIVE_SOURCES.md` and select only the rules,
   requirements, ADRs, and policies relevant to the task.
1. Read `docs/00-project/ai/agents/guides/MEMORY_USAGE.md` and this file.
1. If using a named role, read its profile, wrapper skill, and matching
   `memory-py-*.md` sheet.
1. Run the `pre-task` command from `src/memory/DAILY_WORKFLOW.md`.

V1/V2 tasks use a direct single-agent route unless the user or an active
contract requires more. V3/V4 tasks use explicit planning and the orchestration
and post-change gates in `.codex/agents/ORCHESTRATION.md`.

Role memory sheets: `memory-py-audit-bot.md`, `memory-py-config-bot.md`,
`memory-py-debug-bot.md`, `memory-py-doc-bot.md`, `memory-py-plan-bot.md`, and
`memory-py-test-bot.md`.

## Canonical owner map

| Question | Read |
| --- | --- |
| Runtime precedence and safety | `AGENTS.md` |
| Normative stack | `docs/00-project/NORMATIVE_SOURCES.md` |
| Engineering rules | `docs/00-project/RULES.md` |
| Testable requirements | `docs/01-requirements/REQUIREMENTS.md` |
| Architecture decisions | `docs/02-architecture/decisions/` |
| Codex routing | `.codex/agents/CODEX-RUNTIME.md`, `.codex/agents/ORCHESTRATION.md` |
| Role behavior | `.codex/agents/py-*.md` |
| Skill entry contracts | `.codex/skills/**` |
| Post-change obligations | `docs/00-project/ai/agents/policy/POST_CHANGE_VALIDATION.md` |
| Memory lifecycle | `src/memory/DAILY_WORKFLOW.md` |

Docs under `docs/00-project/ai/**` are mirrors/navigation unless an ownership
policy explicitly makes a file canonical. Runtime behavior is changed in its
active runtime source first and mirrors are synchronized afterward.

## Repository navigation

- Product code: `src/bioetl/`
- Tests: `tests/`
- Configuration: `configs/`
- Architecture evidence: `docs/reports/evidence/`
- Quality/debt governance: `configs/quality/`, `reports/quality/`
- Runtime tooling: `scripts/ai/`, `scripts/ops/`
- Documentation map: `docs/00-project/00-map.md`
- Glossary: `docs/00-project/glossary.md`

Use repository search and current generators/checkers. Do not rely on memory for
file counts, provider counts, ADR ranges, coverage thresholds, command aliases,
or current dependency versions.

## Platform-specific Python environments

- On native Windows and in PowerShell, agents MUST use the repository-local
  `.venv-win` environment. Activate it with
  `.\.venv-win\Scripts\Activate.ps1` or invoke
  `.\.venv-win\Scripts\python.exe` directly.
- Do not reuse a Linux/WSL `.venv` from Windows. Create or refresh the Windows
  environment with `.\scripts\engineering\dev\setup_env_windows.ps1`.
- WSL/Linux agents must continue to follow the platform-specific environment
  guidance in `docs/03-guides/getting-started.md`; `.venv-win` is reserved for
  native Windows processes.

## Durable invariants to verify at source

- Respect layer boundaries and constructor injection.
- Direct `interfaces -> infrastructure` imports are forbidden; interfaces route
  through Application services or public Composition entrypoints.
- Preserve deterministic writes and current config/schema contracts.
- Keep the default BioETL runtime local-only; optional infrastructure remains
  opt-in.
- Do not expose secrets or sensitive data in code, config, recordings, logs, or
  reports.
- Do not create or modify `.env` files without explicit per-task approval.
- Technical-debt budgets, exemptions, thresholds, and hotspot caps may not be
  increased.
- Preserve unrelated worktree changes and use canonical generators for derived
  artifacts.

These bullets are reminders only; cite and apply the current normative source.

## Evidence anchors

For repo-wide structural claims, start at:

- `docs/reports/evidence/project-file-structure/SUMMARY.md`
- `docs/reports/evidence/project-package-topology/SUMMARY.md`
- `docs/reports/evidence/governance-signals/SUMMARY.md`

Package/file count alone is descriptive, not proof of debt. Prefer current
family-level topology plus governance signals and executable checks.

## Memory loop and closeout

Use the canonical commands and identity variables documented in
`src/memory/DAILY_WORKFLOW.md`. Episodic records belong under
`src/memory/episodic/`; durable lessons require curated promotion. Never write
secrets, credentials, raw sensitive payloads, or machine-specific tokens into
memory.

After write-capable work:

1. Re-scan touched and related surfaces.
1. Run proportionate validation and required mirror/generator checks.
1. Run the canonical `post-task` workflow.
1. Report commands/results, exact skips, mirror status, and debt outcome as
   `improved`, `unchanged`, or `worsened`.

`worsened` is not made acceptable by raising a budget. If a hard guardrail
would be violated, stop and escalate.

## Improved Sections

### Specificity Enhancements

#### Concrete Bootstrap Commands
```bash
# Step 1: Read AGENTS.md
cat AGENTS.md

# Step 2: Read NORMATIVE_SOURCES.md
cat docs/00-project/NORMATIVE_SOURCES.md

# Step 3: Read MEMORY_USAGE.md
cat docs/00-project/ai/agents/guides/MEMORY_USAGE.md

# Step 4: Read role-specific memory (if using named role)
cat docs/00-project/ai/memory/memory-py-audit-bot.md

# Step 5: Run pre-task command
python -m memory.tooling.workflow pre-task --task-id=<TASK_ID>
```

#### Timeout Policies
```yaml
bootstrap_timeouts:
  read_agents_md: 5
  read_normative_sources: 10
  read_memory_usage: 5
  read_role_memory: 5
  run_pre_task: 30
  total_bootstrap_timeout: 55
```

#### Retry Policies
```yaml
bootstrap_retry_policies:
  read_agents_md:
    max_retries: 3
    backoff: "fixed"
    backoff_delay: 1
  
  read_normative_sources:
    max_retries: 3
    backoff: "fixed"
    backoff_delay: 2
  
  run_pre_task:
    max_retries: 2
    backoff: "exponential"
    backoff_delay: [1, 2]
```

### Enhanced Guardrails

#### Integrity Guardrails
- **Memory Consistency**: Verify memory consistency with current checkout
- **Precedence Enforcement**: Enforce precedence hierarchy from AGENTS.md
- **Role Validation**: Validate role-specific memory before use
- **Bootstrap Validation**: Validate bootstrap completion before task execution

#### Consistency Guardrails
- **Navigation Consistency**: Ensure navigation is consistent across memory sheets
- **Invariant Consistency**: Ensure invariants are consistent with normative sources
- **Evidence Consistency**: Ensure evidence anchors are consistent with current evidence
- **Closeout Consistency**: Ensure closeout procedures are consistent across tasks

#### Access Control Guardrails
- **Memory Access Control**: Verify access to memory files before reading
- **Normative Access Control**: Verify access to normative sources before reading
- **Role Access Control**: Verify access to role-specific memory before reading
- **Evidence Access Control**: Verify access to evidence anchors before reading

### Error Handling Improvements

#### Error Recovery Strategies
```yaml
error_recovery:
  bootstrap:
    strategy: "retry_with_fallback"
    fallback: "manual_bootstrap"
    max_retries: 3
  
  memory_read:
    strategy: "retry_with_skip"
    fallback: "skip_non_essential_memory"
    max_retries: 2
  
  pre_task:
    strategy: "retry_with_partial"
    fallback: "partial_pre_task"
    max_retries: 2
```

#### Fallback Procedures
- **Bootstrap Fallback**: Manual bootstrap using direct file reading and manual validation
- **Memory Read Fallback**: Skip non-essential memory if essential memory is available
- **Pre-Task Fallback**: Partial pre-task execution if full pre-task fails

#### Graceful Degradation
- **Partial Bootstrap**: Allow partial bootstrap if full bootstrap fails
- **Partial Memory**: Allow partial memory if full memory is unavailable
- **Partial Pre-Task**: Allow partial pre-task if full pre-task fails
- **Warning Mode**: Operate in warning mode for non-critical failures

### Validation Enhancements

#### Validation Gates
```yaml
validation_gates:
  pre_bootstrap:
    - validate_file_access
    - validate_environment
    - validate_dependencies
  
  during_bootstrap:
    - validate_file_read
    - validate_memory_consistency
    - validate_precedence
  
  post_bootstrap:
    - validate_bootstrap_completion
    - validate_role_memory
    - validate_pre_task_execution
```

#### Self-Consistency Checks
- **Memory Consistency**: Verify memory is consistent with current checkout
- **Precedence Consistency**: Verify precedence is consistent with AGENTS.md
- **Role Consistency**: Verify role memory is consistent with role profile
- **Bootstrap Consistency**: Verify bootstrap is consistent with task requirements

#### Validation Procedures
1. **Pre-Bootstrap Validation**: Validate file access, environment, and dependencies
2. **During-Bootstrap Validation**: Validate file read, memory consistency, and precedence
3. **Post-Bootstrap Validation**: Validate bootstrap completion, role memory, and pre-task execution
4. **Cross-Step Validation**: Validate consistency across bootstrap steps

### Maintainability Improvements

#### Maintenance Guidelines
- **Weekly Review**: Review memory consistency weekly
- **Monthly Audit**: Conduct monthly audit of memory sheets
- **Quarterly Update**: Update memory documentation quarterly
- **Continuous Monitoring**: Monitor memory usage metrics continuously

#### Versioning Strategy
```yaml
versioning:
  format: "v{major}.{minor}.{patch}"
  major: "breaking changes"
  minor: "new features or significant improvements"
  patch: "bug fixes or minor improvements"
  
  current_version: "v2.0.0"
  release_schedule: "as_needed"
  backward_compatibility: "maintained_for_minor_and_patch"
```

#### Cleanup Procedures
- **Memory Cleanup**: Clean up episodic memory older than 90 days
- **Evidence Cleanup**: Archive evidence anchors older than 1 year
- **Log Cleanup**: Clean up memory logs older than 30 days
- **Cache Cleanup**: Clean up memory cache artifacts older than 7 days

### Reusability Improvements

#### Reusable Patterns
```yaml
reusable_patterns:
  bootstrap:
    - file_reading
    - memory_validation
    - precedence_enforcement
    - pre_task_execution
  
  navigation:
    - canonical_owner_map
    - repository_navigation
    - evidence_anchors
  
  closeout:
    - re_scan
    - validation
    - post_task_workflow
    - reporting
```

#### Modular Components
- **Bootstrap Module**: Execute bootstrap procedures
- **Navigation Module**: Provide navigation assistance
- **Validation Module**: Validate memory consistency
- **Closeout Module**: Execute closeout procedures

#### Templates
```yaml
templates:
  memory_sheet:
    - metadata
    - bootstrap_procedures
    - navigation_map
    - invariants
    - closeout_procedures
  
  bootstrap_procedure:
    - step_description
    - execution_command
    - timeout_policy
    - retry_policy
    - validation_procedure
```

#### Configuration Parameters
```yaml
configuration_parameters:
  bootstrap_timeouts:
    read_agents_md: 5
    read_normative_sources: 10
    read_memory_usage: 5
    read_role_memory: 5
    run_pre_task: 30
  
  bootstrap_retries:
    read_agents_md: 3
    read_normative_sources: 3
    run_pre_task: 2
```

### Documentation Improvements

#### Enhanced Documentation with Examples
```yaml
documentation_examples:
  bootstrap:
    - v1_task_bootstrap_example
    - v2_task_bootstrap_example
    - v3_task_bootstrap_example
    - v4_task_bootstrap_example
  
  navigation:
    - runtime_precedence_example
    - normative_stack_example
    - role_behavior_example
  
  closeout:
    - write_capable_closeout_example
    - read_only_closeout_example
```

#### Templates and Guidelines
- **Memory Sheet Template**: Standard template for defining memory sheets
- **Bootstrap Guidelines**: Guidelines for implementing bootstrap procedures
- **Navigation Guidelines**: Guidelines for implementing navigation assistance
- **Closeout Guidelines**: Guidelines for implementing closeout procedures

#### Usage Examples
```bash
# Example: Bootstrap for V1 task
python -m memory.tooling.workflow pre-task --task-id=v1-task-123 --task-type=v1

# Example: Bootstrap for V2 task
python -m memory.tooling.workflow pre-task --task-id=v2-task-456 --task-type=v2

# Example: Bootstrap for V3 task
python -m memory.tooling.workflow pre-task --task-id=v3-task-789 --task-type=v3

# Example: Bootstrap for V4 task
python -m memory.tooling.workflow pre-task --task-id=v4-task-012 --task-type=v4

# Example: Closeout for write-capable task
python -m memory.tooling.workflow post-task --task-id=task-123 --task-type=write-capable

# Example: Closeout for read-only task
python -m memory.tooling.workflow post-task --task-id=task-456 --task-type=read-only
```
