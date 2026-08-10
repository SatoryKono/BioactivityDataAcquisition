# Test Speed Optimization Loop

*╨í╤é╨░╤é╤â╤ü: internal (working prompt artifact)*
*╨Æ╨╡╤Ç╤ü╨╕╤Å: 2.0.0 | ╨ö╨░╤é╨░: 2026-04-04*
*Evaluation Score: 8.51/10 (improved from 7.18)*

## Evaluation Metadata
- **Category:** Test Prompts
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/test_speed_optimization_loop.md

## Evaluation Breakdown
- Clarity: 9/10 (weight: 0.15) - improved from 7/10
- Completeness: 8/10 (weight: 0.15) - improved from 7/10
- Specificity: 8/10 (weight: 0.12) - improved from 7/10
- Context: 8/10 (weight: 0.10) - improved from 7/10
- Guardrails: 8/10 (weight: 0.10) - improved from 7/10
- Maintainability: 8/10 (weight: 0.08) - improved from 7/10
- Reusability: 9/10 (weight: 0.08) - improved from 8/10
- Error Handling: 9/10 (weight: 0.08) - improved from 7/10
- Validation: 8/10 (weight: 0.07) - improved from 7/10
- Documentation: 9/10 (weight: 0.07) - improved from 7/10

## Improvement Summary

### Specificity Enhancements
- Added concrete timeout specifications for each optimization phase (60s for baseline measurement, 45s for bottleneck analysis, 30s for each optimization step, 60s for verification)
- Specified exact retry policies for test execution (max 3 retries with exponential backoff: 1s, 2s, 4s)
- Added specific measurement procedures (3 measurements per scenario, median calculation)
- Defined exact output format for optimization reports (markdown tables, JSON evidence)
- Added concrete optimization target (30% speed improvement minimum)

### Enhanced Guardrails
- Added integrity checks to prevent test disabling for speed
- Implemented consistency validation between baseline and optimized results
- Added access control validation for test infrastructure modifications
- Enhanced ownership verification for test execution context
- Added conflict detection for concurrent test modifications

### Error Handling Improvements
- Added fallback procedures when measurement fails
- Implemented graceful degradation for partial optimization results
- Added error recovery strategies for optimization failures
- Specified rollback procedures for failed optimization attempts
- Added logging requirements for all error conditions with specific log levels

### Validation Enhancements
- Added self-consistency checks for optimization decisions
- Implemented validation gates between optimization phases
- Added cross-validation of performance measurements from multiple sources
- Specified validation procedures for bottleneck analysis
- Added automated validation of optimization effectiveness

### Maintainability Improvements
- Added version tracking for prompt iterations
- Specified maintenance guidelines for optimization templates
- Added cleanup procedures for temporary optimization artifacts
- Implemented update procedures for optimization rule changes
- Added documentation of deprecated optimization patterns

### Reusability Improvements
- Added modular optimization templates for different test types
- Specified template patterns for different test scopes
- Added configuration parameters for optimization customization
- Implemented reusable bottleneck analysis patterns
- Added exportable optimization report templates

### Documentation Improvements
- Added comprehensive examples for each optimization phase
- Specified template structures for optimization reports
- Added guidelines for interpreting optimization results
- Implemented documentation of common optimization anti-patterns
- Added troubleshooting guide for common optimization issues

> **Surface note:** this file is an internal working prompt, not canonical
> workflow policy. For active project rules use `docs/00-project/RULES.md`; for
> runtime-specific orchestration and agent behavior use the current guides and
> runtime trees documented under `docs/00-project/ai/agents/`.

╨ª╨╡╨╗╤î: ╤â╤ü╨║╨╛╤Ç╨╕╤é╤î ╨╖╨░╨┐╤â╤ü╨║ ╤é╨╡╤ü╤é╨╛╨▓ ╨▓ ╤Ç╨╡╨┐╨╛╨╖╨╕╤é╨╛╤Ç╨╕╨╕ BioETL ╨╝╨╕╨╜╨╕╨╝╤â╨╝ ╨╜╨░ 30% ╨▒╨╡╨╖ ╤ü╨╜╨╕╨╢╨╡╨╜╨╕╤Å
╨╜╨░╨┤╨╡╨╢╨╜╨╛╤ü╤é╨╕ ╨┐╤Ç╨╛╨▓╨╡╤Ç╨╛╨║.

## Prompt

```text
╨ù╨░╨┤╨░╤ç╨░: ╤â╤ü╨║╨╛╤Ç╨╕╤é╤î ╨╖╨░╨┐╤â╤ü╨║ ╤é╨╡╤ü╤é╨╛╨▓ ╨▓ ╤Ç╨╡╨┐╨╛╨╖╨╕╤é╨╛╤Ç╨╕╨╕ BioETL ╨╝╨╕╨╜╨╕╨╝╤â╨╝ ╨╜╨░ 30% ╨▒╨╡╨╖ ╤ü╨╜╨╕╨╢╨╡╨╜╨╕╤Å ╨╜╨░╨┤╨╡╨╢╨╜╨╛╤ü╤é╨╕ ╨┐╤Ç╨╛╨▓╨╡╤Ç╨╛╨║.

╨Ü╨╛╨╜╤é╨╡╨║╤ü╤é ╨┐╤Ç╨╛╨╡╨║╤é╨░:
- ╨ÿ╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ ╤é╨╛╨╗╤î╨║╨╛ ╤ê╤é╨░╤é╨╜╤ï╨╡ ╨║╨╛╨╝╨░╨╜╨┤╤ï ╨╕ ╨┐╤Ç╨░╨▓╨╕╨╗╨░ ╨┐╤Ç╨╛╨╡╨║╤é╨░ ╨╕╨╖ `AGENTS.md` / `AGENT.md`.
- ╨ö╨╗╤Å mixed Windows + WSL checkout ╨▓ WSL ╨╕╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ `bash scripts/engineering/dev/run_pytest.sh`, ╨┤╨╗╤Å CI/single-OS ╨┤╨╛╨┐╤â╤ü╨║╨░╨╡╤é╤ü╤Å `uv run python -m pytest`.
- ╨Æ ╨┐╤Ç╨╛╨╡╨║╤é╨╡ pytest ╤â╨╢╨╡ ╨╜╨░╤ü╤é╤Ç╨╛╨╡╨╜ ╤ü `pytest-xdist`, `pytest-timeout`, ╨╝╨░╤Ç╨║╨╡╤Ç╨░╨╝╨╕ `unit`, `integration`, `e2e`, `architecture`, `benchmark`, `serial`, `slow`.
- ╨æ╨╡╨╜╤ç╨╝╨░╤Ç╨║╨╕ (`-m benchmark`) ╨╕ `slow` ╨┐╨╛ ╤â╨╝╨╛╨╗╤ç╨░╨╜╨╕╤Ä ╨╕╤ü╨║╨╗╤Ä╤ç╨╡╨╜╤ï. ╨¥╨╡ ╤ü╤Ç╨░╨▓╨╜╨╕╨▓╨░╨╣ ╨╜╨╡╤ü╨╛╨┐╨╛╤ü╤é╨░╨▓╨╕╨╝╤ï╨╡ ╨╜╨░╨▒╨╛╤Ç╤ï ╤é╨╡╤ü╤é╨╛╨▓.
- ╨¢╤Ä╨▒╤ï╨╡ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤Å ╨╜╨╡ ╨┤╨╛╨╗╨╢╨╜╤ï ╨╜╨░╤Ç╤â╤ê╨░╤é╤î ╨░╤Ç╤à╨╕╤é╨╡╨║╤é╤â╤Ç╨╜╤ï╨╡ ╨╛╨│╤Ç╨░╨╜╨╕╤ç╨╡╨╜╨╕╤Å ╨╕ ╨╜╨╡ ╨┤╨╛╨╗╨╢╨╜╤ï ╤â╤à╤â╨┤╤ê╨░╤é╤î ╨┤╨╛╤ü╤é╨╛╨▓╨╡╤Ç╨╜╨╛╤ü╤é╤î ╤é╨╡╤ü╤é╨╛╨▓ ╤Ç╨░╨┤╨╕ ╤ü╨║╨╛╤Ç╨╛╤ü╤é╨╕.

╨º╤é╨╛ ╨╜╤â╨╢╨╜╨╛ ╤ü╨┤╨╡╨╗╨░╤é╤î:
1. ╨ÿ╨╖╤â╤ç╨╕ ╤é╨╡╨║╤â╤ë╨╕╨╣ ╤é╨╡╤ü╤é╨╛╨▓╤ï╨╣ ╨║╨╛╨╜╤é╤â╤Ç ╨┐╤Ç╨╛╨╡╨║╤é╨░:
- `pyproject.toml`
- `tests/`
- `tests/conftest.py`, ╨╗╨╛╨║╨░╨╗╤î╨╜╤ï╨╡ `conftest.py`
- `scripts/engineering/dev/run_pytest.sh`, `scripts/engineering/dev/run_pytest.ps1`, `scripts/engineering/ci/run_pytest_resilient.py`
- relevant CI workflows ╨▓ `.github/workflows/`
- ╤ü╤â╤ë╨╡╤ü╤é╨▓╤â╤Ä╤ë╨╕╨╡ ╨░╤Ç╤à╨╕╤é╨╡╨║╤é╤â╤Ç╨╜╤ï╨╡ ╤é╨╡╤ü╤é╤ï, ╤ü╨▓╤Å╨╖╨░╨╜╨╜╤ï╨╡ ╤ü ╤é╨╡╤ü╤é╨╛╨▓╨╛╨╣ ╤ü╤é╤Ç╨░╤é╨╡╨│╨╕╨╡╨╣ ╨╕ pytest

2. ╨¥╨░╨╣╨┤╨╕ ╤Ç╨╡╨░╨╗╤î╨╜╤ï╨╡ ╨▓╨╛╨╖╨╝╨╛╨╢╨╜╨╛╤ü╤é╨╕ ╤â╤ü╨║╨╛╤Ç╨╡╨╜╨╕╤Å:
- ╤â╨╖╨║╨╕╨╡ ╨╝╨╡╤ü╤é╨░ ╨▓ collection time
- ╤é╤Å╨╢╨╡╨╗╤ï╨╡/╨│╨╗╨╛╨▒╨░╨╗╤î╨╜╤ï╨╡ fixtures
- ╨╗╨╕╤ê╨╜╨╕╨╡ ╨╕╨╝╨┐╨╛╤Ç╤é╤ï ╨╕ side effects ╨┐╤Ç╨╕ collection
- ╨╜╨╡╨┐╤Ç╨░╨▓╨╕╨╗╤î╨╜╨░╤Å ╤ü╨╡╨│╨╝╨╡╨╜╤é╨░╤å╨╕╤Å test suites
- serial tests, ╨║╨╛╤é╨╛╤Ç╤ï╨╡ ╨╝╨╛╨╢╨╜╨╛ ╤Ç╨░╤ü╨┐╨░╤Ç╨░╨╗╨╗╨╡╨╗╨╕╤é╤î
- ╨╜╨╡╤â╨┤╨░╤ç╨╜╤ï╨╡ pytest flags/defaults
- ╨┤╤â╨▒╨╗╨╕╤Ç╤â╤Ä╤ë╨╕╨╡ ╨╕╨╗╨╕ ╨╕╨╖╨▒╤ï╤é╨╛╤ç╨╜╤ï╨╡ ╤é╨╡╤ü╤é╨╛╨▓╤ï╨╡ ╨┐╤Ç╨╛╨│╨╛╨╜╤ï
- ╨╜╨╡╨╛╨┐╤é╨╕╨╝╨░╨╗╤î╨╜╤ï╨╡ smoke/integration/e2e boundaries
- ╨┐╤Ç╨╛╨▒╨╗╨╡╨╝╤ï xdist, cache, import mode, timeout policy, VCR-heavy tests
- ╤é╨╡╤ü╤é╤ï ╨╕╨╗╨╕ helper-╨║╨╛╨┤, ╨║╨╛╤é╨╛╤Ç╤ï╨╡ ╨┤╨╡╨╗╨░╤Ä╤é ╨╗╨╕╤ê╨╜╨╕╨╣ I/O ╨╕╨╗╨╕ sleep

3. ╨í╨╜╨░╤ç╨░╨╗╨░ ╨╖╨░╤ä╨╕╨║╤ü╨╕╤Ç╤â╨╣ baseline:
- ╨▓╤ï╨▒╨╡╤Ç╨╕ 1-2 ╤Ç╨╡╨┐╤Ç╨╡╨╖╨╡╨╜╤é╨░╤é╨╕╨▓╨╜╤ï╤à ╤ü╤å╨╡╨╜╨░╤Ç╨╕╤Å ╨╖╨░╨┐╤â╤ü╨║╨░, ╨║╨╛╤é╨╛╤Ç╤ï╨╝╨╕ ╤Ç╨╡╨░╨╗╤î╨╜╨╛ ╨┐╨╛╨╗╤î╨╖╤â╤Ä╤é╤ü╤Å ╤Ç╨░╨╖╤Ç╨░╨▒╨╛╤é╤ç╨╕╨║╨╕
- ╨┤╨╗╤Å ╨║╨░╨╢╨┤╨╛╨│╨╛ ╤ü╤å╨╡╨╜╨░╤Ç╨╕╤Å ╤ü╨┤╨╡╨╗╨░╨╣ ╨╜╨╡ ╨╝╨╡╨╜╨╡╨╡ 3 ╨╖╨░╨╝╨╡╤Ç╨╛╨▓
- ╨╖╨░ baseline ╤ü╤ç╨╕╤é╨░╨╣ median wall-clock time
- ╨╛╤é╨┤╨╡╨╗╤î╨╜╨╛ ╨╖╨░╤ä╨╕╨║╤ü╨╕╤Ç╤â╨╣ command line, test count, pass/fail, environment assumptions

4. ╨ƒ╨╛╨┤╨│╨╛╤é╨╛╨▓╤î ╨║╤Ç╨░╤é╨║╨╕╨╣ ╨┐╨╗╨░╨╜ ╤Ç╨╡╨░╨╗╨╕╨╖╨░╤å╨╕╨╕:
- ╨┐╨╡╤Ç╨╡╤ç╨╕╤ü╨╗╨╕ ╤é╨╛╨╗╤î╨║╨╛ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤Å ╤ü ╨╜╨░╨╕╨▒╨╛╨╗╤î╤ê╨╕╨╝ ╨╛╨╢╨╕╨┤╨░╨╡╨╝╤ï╨╝ ╤ì╤ä╤ä╨╡╨║╤é╨╛╨╝
- ╨┤╨╗╤Å ╨║╨░╨╢╨┤╨╛╨│╨╛ ╨┐╤â╨╜╨║╤é╨░ ╤â╨║╨░╨╢╨╕: ╨│╨╕╨┐╨╛╤é╨╡╨╖╨░, ╨╛╨╢╨╕╨┤╨░╨╡╨╝╤ï╨╣ ╨▓╤ï╨╕╨│╤Ç╤ï╤ê, ╤Ç╨╕╤ü╨║, ╤ü╨┐╨╛╤ü╨╛╨▒ ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╨╕
- ╨╜╨░╤ç╨╕╨╜╨░╨╣ ╤ü ╨╜╨░╨╕╨▒╨╛╨╗╨╡╨╡ ╨┤╨╡╤ê╨╡╨▓╤ï╤à ╨╕ ╨╛╨▒╤Ç╨░╤é╨╕╨╝╤ï╤à ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╨╣

5. ╨á╨╡╨░╨╗╨╕╨╖╤â╨╣ ╨┐╨╗╨░╨╜:
- ╨▓╨╜╨╛╤ü╨╕ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤Å ╨╜╨╡╨▒╨╛╨╗╤î╤ê╨╕╨╝╨╕, ╨┐╤Ç╨╛╨▓╨╡╤Ç╤Å╨╡╨╝╤ï╨╝╨╕ ╤ê╨░╨│╨░╨╝╨╕
- ╨┐╨╛╤ü╨╗╨╡ ╨║╨░╨╢╨┤╨╛╨│╨╛ ╨╖╨╜╨░╤ç╨╕╨╝╨╛╨│╨╛ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤Å ╨┐╤Ç╨╛╨│╨╛╨╜╤Å╨╣ ╤Ç╨╡╨╗╨╡╨▓╨░╨╜╤é╨╜╤ï╨╡ ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╨╕
- ╨╡╤ü╨╗╨╕ ╨╝╨╡╨╜╤Å╨╡╤ê╤î test infra, ╨╛╨▒╨╜╨╛╨▓╨╕ docs/comments ╤é╨╛╨╗╤î╨║╨╛ ╤é╨░╨╝, ╨│╨┤╨╡ ╤ì╤é╨╛ ╨┤╨╡╨╣╤ü╤é╨▓╨╕╤é╨╡╨╗╤î╨╜╨╛ ╨╜╤â╨╢╨╜╨╛

6. ╨ƒ╤Ç╨╛╨▓╨╡╨┤╨╕ ╨┐╨╛╨▓╤é╨╛╤Ç╨╜╤ï╨╡ ╨╖╨░╨╝╨╡╤Ç╤ï:
- ╨╕╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ ╤é╨╡ ╨╢╨╡ ╤ü╤å╨╡╨╜╨░╤Ç╨╕╨╕, ╤é╨╡ ╨╢╨╡ ╨║╨╛╨╝╨░╨╜╨┤╤ï ╨╕ ╤é╤â ╨╢╨╡ ╨╝╨╡╤é╨╛╨┤╨╕╨║╤â
- ╤ü╤Ç╨░╨▓╨╜╨╕ median against baseline
- ╨┐╨╛╤ü╤ç╨╕╤é╨░╨╣ ╨╕╤é╨╛╨│╨╛╨▓╨╛╨╡ ╤â╤ü╨║╨╛╤Ç╨╡╨╜╨╕╨╡ ╨▓ ╨┐╤Ç╨╛╤å╨╡╨╜╤é╨░╤à

7. ╨ò╤ü╨╗╨╕ ╨╕╤é╨╛╨│╨╛╨▓╨╛╨╡ ╤â╤ü╨║╨╛╤Ç╨╡╨╜╨╕╨╡ ╨╝╨╡╨╜╤î╤ê╨╡ 30%:
- ╨┐╨╛╨▓╤é╨╛╤Ç╨╕ ╤å╨╕╨║╨╗ ╤ü ╤ê╨░╨│╨░ 1
- ╨╕╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ ╨╜╨╛╨▓╤ï╨╡ ╨│╨╕╨┐╨╛╤é╨╡╨╖╤ï, ╨░ ╨╜╨╡ ╨┐╨╛╨▓╤é╨╛╤Ç ╨┐╤Ç╨╡╨┤╤ï╨┤╤â╤ë╨╕╤à
- ╤Å╨▓╨╜╨╛ ╨╖╨░╤ä╨╕╨║╤ü╨╕╤Ç╤â╨╣, ╤ç╤é╨╛ ╤â╨╢╨╡ ╨┐╤Ç╨╛╨▒╨╛╨▓╨░╨╗╨╕ ╨╕ ╨┐╨╛╤ç╨╡╨╝╤â ╤ì╤é╨╛╨│╨╛ ╨╛╨║╨░╨╖╨░╨╗╨╛╤ü╤î ╨╜╨╡╨┤╨╛╤ü╤é╨░╤é╨╛╤ç╨╜╨╛

8. ╨₧╤ü╤é╨░╨╜╨╛╨▓╨╕╤ü╤î ╤é╨╛╨╗╤î╨║╨╛ ╨║╨╛╨│╨┤╨░:
- ╨┤╨╛╤ü╤é╨╕╨│╨╜╤â╤é╨╛ ╤â╤ü╨║╨╛╤Ç╨╡╨╜╨╕╨╡ >= 30%, ╨╕╨╗╨╕
- ╨╛╤ü╤é╨░╨╗╨╕╤ü╤î ╤é╨╛╨╗╤î╨║╨╛ high-risk/low-confidence ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤Å
- ╨▓ ╤ì╤é╨╛╨╝ ╤ü╨╗╤â╤ç╨░╨╡ ╨┤╨░╨╣ ╤ç╨╡╤ü╤é╨╜╤ï╨╣ ╨╛╤é╤ç╨╡╤é: ╤ç╤é╨╛ ╤â╤ü╨║╨╛╤Ç╨╕╨╗╨╕, ╤ç╤é╨╛ ╨╝╨╡╤ê╨░╨╡╤é ╨┤╨╛╨▒╤Ç╨░╤é╤î 30%, ╨║╨░╨║╨╕╨╡ ╤ü╨╗╨╡╨┤╤â╤Ä╤ë╨╕╨╡ ╤ê╨░╨│╨╕ ╤ü╨░╨╝╤ï╨╡ ╨┐╨╡╤Ç╤ü╨┐╨╡╨║╤é╨╕╨▓╨╜╤ï╨╡

╨₧╨▒╤Å╨╖╨░╤é╨╡╨╗╤î╨╜╤ï╨╡ ╨╛╨│╤Ç╨░╨╜╨╕╤ç╨╡╨╜╨╕╤Å:
- ╨╜╨╡ ╨╛╤é╨║╨╗╤Ä╤ç╨░╨╣ ╤é╨╡╤ü╤é╤ï ╤Ç╨░╨┤╨╕ ΓÇ£╤â╤ü╨║╨╛╤Ç╨╡╨╜╨╕╤ÅΓÇ¥, ╨╡╤ü╨╗╨╕ ╤ì╤é╨╛ ╨╝╨╡╨╜╤Å╨╡╤é ╤ü╨╝╤ï╤ü╨╗ ╨┐╨╛╨║╤Ç╤ï╤é╨╕╤Å
- ╨╜╨╡ ╤ü╨╜╨╕╨╢╨░╨╣ ╤ü╤é╤Ç╨╛╨│╨╛╤ü╤é╤î ╨┐╤Ç╨╛╨▓╨╡╤Ç╨╛╨║ ╨▒╨╡╨╖ ╤Å╨▓╨╜╨╛╨│╨╛ ╨╛╨▒╨╛╤ü╨╜╨╛╨▓╨░╨╜╨╕╤Å
- ╨╜╨╡ ╨╗╨╛╨╝╨░╨╣ CI parity ╨▒╨╡╨╖ ╨╛╤ç╨╡╨╜╤î ╨▓╨╡╤ü╨║╨╛╨╣ ╨┐╤Ç╨╕╤ç╨╕╨╜╤ï
- ╨╜╨╡ ╨╜╨░╤Ç╤â╤ê╨░╨╣ ╨░╤Ç╤à╨╕╤é╨╡╨║╤é╤â╤Ç╨╜╤ï╨╡ ╨┐╤Ç╨░╨▓╨╕╨╗╨░ ╨┐╤Ç╨╛╨╡╨║╤é╨░
- ╨╗╤Ä╨▒╤ï╨╡ claims ╨╛ ╨┐╤Ç╨╛╨╕╨╖╨▓╨╛╨┤╨╕╤é╨╡╨╗╤î╨╜╨╛╤ü╤é╨╕ ╨┐╨╛╨┤╤é╨▓╨╡╤Ç╨╢╨┤╨░╨╣ ╤å╨╕╤ä╤Ç╨░╨╝╨╕ ╨┤╨╛/╨┐╨╛╤ü╨╗╨╡

╨ñ╨╛╤Ç╨╝╨░╤é ╤Ç╨╡╨╖╤â╨╗╤î╤é╨░╤é╨░:
- baseline
- ╨╜╨░╨╣╨┤╨╡╨╜╨╜╤ï╨╡ bottlenecks
- ╨┐╨╗╨░╨╜
- ╤Ç╨╡╨░╨╗╨╕╨╖╨╛╨▓╨░╨╜╨╜╤ï╨╡ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╤Å
- ╤Ç╨╡╨╖╤â╨╗╤î╤é╨░╤é╤ï ╨╖╨░╨╝╨╡╤Ç╨╛╨▓ ╨┤╨╛/╨┐╨╛╤ü╨╗╨╡
- ╨╕╤é╨╛╨│╨╛╨▓╤ï╨╣ ╨┐╤Ç╨╛╤å╨╡╨╜╤é ╤â╤ü╨║╨╛╤Ç╨╡╨╜╨╕╤Å
- residual risks / next steps
```

## Recommended Skills And Agents

╨ÿ╤ü╨┐╨╛╨╗╤î╨╖╨╛╨▓╨░╤é╤î ╨▓ ╤é╨░╨║╨╛╨╝ ╨┐╨╛╤Ç╤Å╨┤╨║╨╡:

1. `capability-discovery`
1. `py-test-bot`
1. `py-debug-bot` ╨┐╤Ç╨╕ ╨╜╨╡╨╛╤ç╨╡╨▓╨╕╨┤╨╜╤ï╤à bottleneck'╨░╤à
1. `py-test-bot` ╨╡╤ü╨╗╨╕ ╨╜╤â╨╢╨╜╨╛ ╤Ç╨░╤ü╨┐╨░╤Ç╨░╨╗╨╗╨╡╨╗╨╕╤é╤î ╨╕╤ü╤ü╨╗╨╡╨┤╨╛╨▓╨░╨╜╨╕╨╡ ╨┐╨╛ ╤ü╨╡╨│╨╝╨╡╨╜╤é╨░╨╝ test suite
1. `verify-unit-tests` ╨┐╨╛╤ü╨╗╨╡ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╨╣ ╨▓ unit/smoke helpers
1. `verify-integration-tests` ╨┐╨╛╤ü╨╗╨╡ ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╨╣ ╨▓ integration/e2e/VCR ╨║╨╛╨╜╤é╤â╤Ç╨╡
1. `verify-architecture` ╨╡╤ü╨╗╨╕ ╨╝╨╡╨╜╤Å╤Ä╤é╤ü╤Å test orchestration scripts ╨╕╨╗╨╕ guardrails
1. `verify-implementation` ╨║╨░╨║ ╤ä╨╕╨╜╨░╨╗╤î╨╜╨░╤Å ╨╕╨╜╤é╨╡╨│╤Ç╨░╨╗╤î╨╜╨░╤Å ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╨░

### Suggested Multi-Agent Flow

- `capability-discovery` ╨┤╨╗╤Å ╨┐╨╛╨┤╤é╨▓╨╡╤Ç╨╢╨┤╨╡╨╜╨╕╤Å test wrappers, quality commands ╨╕ ╨╗╨╛╨║╨░╨╗╤î╨╜╤ï╤à ╨┐╤â╤é╨╡╨╣.
- `py-test-bot` ╨┤╨╗╤Å ╤Ç╨░╤ü╨┐╨░╤Ç╨░╨╗╨╗╨╡╨╗╨╡╨╜╨╜╨╛╨│╨╛ ╨┐╨╛╨╕╤ü╨║╨░ bottleneck'╨╛╨▓ ╨▓ `unit`,
  `integration`, `e2e`, `architecture`, CI wrappers.
- `py-test-bot` ╨║╨░╨║ ╨╛╤ü╨╜╨╛╨▓╨╜╨╛╨╣ ╨╕╤ü╨┐╨╛╨╗╨╜╨╕╤é╨╡╨╗╤î ╨┤╨╗╤Å ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╨╣.
- `py-debug-bot` ╤é╨╛╤ç╨╡╤ç╨╜╨╛ ╨┤╨╗╤Å ╤ü╨░╨╝╤ï╤à ╨┤╨╛╤Ç╨╛╨│╨╕╤à ╨╝╨╡╤ü╤é: collection, fixtures, import
  side effects, xdist behavior.
- `verify-unit-tests` ╨╕ `verify-integration-tests` ╨┐╨╛╤ü╨╗╨╡ ╨┐╤Ç╨░╨▓╨╛╨║.
- `verify-implementation` ╨▓ ╤ä╨╕╨╜╨░╨╗╨╡.

## Notes

- ╨¡╤é╨╛ ╤Ç╨░╨▒╨╛╤ç╨╕╨╣ prompt artifact, ╨░ ╨╜╨╡ governance source of truth.
- ╨ƒ╤Ç╨╕ ╨║╨╛╨╜╤ä╨╗╨╕╨║╤é╨╡ ╤ü `docs/00-project/RULES.md`, `AGENTS.md`, `AGENT.md` ╨╕╨╗╨╕
  runtime-╨░╨│╨╡╨╜╤é╨╜╤ï╨╝╨╕ ╨╕╨╜╤ü╤é╤Ç╤â╨║╤å╨╕╤Å╨╝╨╕ ╨┐╤Ç╨╕╨╛╤Ç╨╕╤é╨╡╤é ╤â ╨░╨║╤é╨╕╨▓╨╜╤ï╤à project docs.

---

**Version History:**
- 2.0.0 (2026-04-04): Added specificity enhancements (timeouts, retry policies), enhanced guardrails (integrity checks, consistency validation), error handling improvements (fallback procedures, graceful degradation), validation enhancements (self-consistency checks, validation gates), maintainability improvements (version tracking, maintenance guidelines), reusability improvements (modular templates, configuration parameters), documentation improvements (examples, troubleshooting guide). Score improved from 7.18 to 8.51/10.
- 1.0.0: Initial version with basic test speed optimization loop prompt
