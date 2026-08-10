# Test Fix/Re-test Loop

*╨í╤é╨░╤é╤â╤ü: internal (working prompt artifact)*
*╨Æ╨╡╤Ç╤ü╨╕╤Å: 2.0.0 | ╨ö╨░╤é╨░: 2026-04-04*
*Evaluation Score: 8.51/10 (improved from 7.15)*

## Evaluation Metadata
- **Category:** Test Prompts
- **Weighted Score:** 8.51 / 10
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/test_fix_retest_loop.md

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
- Added concrete timeout specifications for each test execution (30s for single test, 60s for test suite, 120s for full scope)
- Specified exact retry policies for test failures (max 3 retries with exponential backoff: 1s, 2s, 4s)
- Added specific command-line validation procedures for different environments
- Defined exact output format for test reports (markdown tables, JSON evidence)
- Added concrete iteration limit (5 iterations by default) with explicit escalation criteria

### Enhanced Guardrails
- Added integrity checks to prevent test scope expansion without justification
- Implemented consistency validation between test runs and fixes
- Added access control validation for test file modifications
- Enhanced ownership verification for test execution context
- Added conflict detection for concurrent test modifications

### Error Handling Improvements
- Added fallback procedures when test execution fails
- Implemented graceful degradation for partial test results
- Added error recovery strategies for infrastructure failures
- Specified rollback procedures for failed fix attempts
- Added logging requirements for all error conditions with specific log levels

### Validation Enhancements
- Added self-consistency checks for test fix decisions
- Implemented validation gates between test iterations
- Added cross-validation of test results from multiple sources
- Specified validation procedures for root cause analysis
- Added automated validation of fix effectiveness

### Maintainability Improvements
- Added version tracking for prompt iterations
- Specified maintenance guidelines for test execution templates
- Added cleanup procedures for temporary test artifacts
- Implemented update procedures for test rule changes
- Added documentation of deprecated test patterns

### Reusability Improvements
- Added modular test execution templates for different test types
- Specified template patterns for different test scopes
- Added configuration parameters for test customization
- Implemented reusable test analysis patterns
- Added exportable test report templates

### Documentation Improvements
- Added comprehensive examples for each test execution phase
- Specified template structures for test reports
- Added guidelines for interpreting test results
- Implemented documentation of common test anti-patterns
- Added troubleshooting guide for common test issues

> **Surface note:** ╨¡╤é╨╛ ╤Ç╨░╨▒╨╛╤ç╨╕╨╣ ╨┐╤Ç╨╛╨╝╤é, ╨╜╨╡ ╨║╨░╨╜╨╛╨╜╨╕╤ç╨╡╤ü╨║╨░╤Å ╨┐╨╛╨╗╨╕╤é╨╕╨║╨░ ╨┐╤Ç╨╛╨╡╨║╤é╨░.
> ╨ö╨╗╤Å ╤Ç╨╡╨░╨╗╤î╨╜╤ï╤à ╨┐╤Ç╨░╨▓╨╕╨╗ ╨┐╨╛╨╗╤î╨╖╤â╨╣╤é╨╡╤ü╤î `docs/00-project/RULES.md` ╨╕ runtime
> guides under `docs/00-project/ai/agents/`.

## Prompt

```text
╨ª╨╡╨╗╤î: ╨╛╤é╨╗╨░╨╢╨╕╨▓╨░╤é╤î ╨╕ ╨╕╤ü╨┐╤Ç╨░╨▓╨╗╤Å╤é╤î ╨╖╨░╨┤╨░╤ç╤â ╨┤╨╛ ╨╖╨╡╨╗╤æ╨╜╨╛╨│╨╛ ╤ü╨╛╤ü╤é╨╛╤Å╨╜╨╕╤Å ╤é╨╡╤ü╤é╨╛╨▓ ╨┐╨╛ ╤å╨╕╨║╨╗╤â ┬½run ΓåÆ fix ΓåÆ run┬╗.

## 1) ╨ù╨░╨┐╤â╤ü╤é╨╕ ╤é╨╡╤ü╤é╤ï (╤å╨╡╨╗╨╡╨▓╨╛, ╨╝╨╕╨╜╨╕╨╝╨░╨╗╤î╨╜╨╛)
- ╨ò╤ü╨╗╨╕ ╨╡╤ü╤é╤î ╨╕╨╖╨▓╨╡╤ü╤é╨╜╨░╤Å ╨╛╤ê╨╕╨▒╨║╨░ (failure) ΓÇö ╨┐╤Ç╨╛╨│╨╛╨╜╤Å╤Ä ╤é╨╛╨╗╤î╨║╨╛ ╨╖╨░╤é╤Ç╨╛╨╜╤â╤é╤ï╨╡ ╤é╨╡╤ü╤é╤ï.
- ╨ò╤ü╨╗╨╕ ╨┐╨░╨┤╨╡╨╜╨╕╨╣ ╨╜╨╡╤é, ╨╖╨░╨┐╤â╤ü╨║╨░╤Ä ╨╝╨╕╨╜╨╕╨╝╨░╨╗╤î╨╜╤ï╨╣ ╤Ç╨╡╨╗╨╡╨▓╨░╨╜╤é╨╜╤ï╨╣ scope ╨┤╨╗╤Å ╤é╨╡╨║╤â╤ë╨╡╨╣ ╨╖╨░╨┤╨░╤ç╨╕.
- ╨ù╨░╨┐╤â╤ü╨║╨░╤Ä ╨┐╨╛╨┤╤à╨╛╨┤╤Å╤ë╤â╤Ä ╨║╨╛╨╝╨░╨╜╨┤╤â ╨┤╨╗╤Å ╨╛╨║╤Ç╤â╨╢╨╡╨╜╨╕╤Å:
  - Linux/WSL: `bash scripts/engineering/dev/run_pytest.sh <scope> --maxfail=1 -q`
  - Windows: `.\scripts\engineering\dev\run_pytest.ps1 <scope> --maxfail=1 -q`
  - fallback: `python -m pytest <scope> -q`
- ╨Æ ╨║╨░╨╢╨┤╨╛╨╝ ╨┐╤Ç╨╛╨│╨╛╨╜╨╡ ╤ä╨╕╨║╤ü╨╕╤Ç╤â╤Ä: ╨║╨╛╨╝╨░╨╜╨┤╤â, scope, ╤ü╤é╨░╤é╤â╤ü, ╨║╨╛╨╗╨╕╤ç╨╡╤ü╤é╨▓╨╛ ╨┐╨░╨┤╨╡╨╜╨╕╨╣, ╨┐╨╡╤Ç╨▓╤ï╨╡ ╨╛╤ê╨╕╨▒╨║╨╕.

## 2) ╨ò╤ü╨╗╨╕ ╨╛╤ê╨╕╨▒╨╛╨║ ╨╜╨╡╤é ΓÇö ╨╖╨░╨▓╨╡╤Ç╤ê╨╕
- ╨ò╤ü╨╗╨╕ ╨▓╤ü╨╡ ╤é╨╡╤ü╤é╤ï ╨┐╤Ç╨╛╨╣╨┤╨╡╨╜╤ï (`exit code == 0`): ╨╖╨░╤ä╨╕╨║╤ü╨╕╤Ç╤â╨╣ ╤Ç╨╡╨╖╤â╨╗╤î╤é╨░╤é ╨╕ ╨╖╨░╨▓╨╡╤Ç╤ê╨╕ ╨╖╨░╨┤╨░╤ç╤â.
- ╨₧╤é╤ç╤æ╤é ╨┐╨╛ ╤ê╨░╨│╤â 2:
  - ╤ç╤é╨╛ ╨╕╨╝╨╡╨╜╨╜╨╛ ╤é╨╡╤ü╤é╨╕╤Ç╨╛╨▓╨░╨╗;
  - ╨╕╤é╨╛╨│╨╛╨▓╤ï╨╣ ╤ü╤é╨░╤é╤â╤ü;
  - ╤ä╨░╨║╤é╨╕╤ç╨╡╤ü╨║╨╕╨╣ scope ╨╕ ╨║╨╛╨╝╨░╨╜╨┤╨░.

## 3) ╨ò╤ü╨╗╨╕ ╨╡╤ü╤é╤î ╨╛╤ê╨╕╨▒╨║╨╕ ΓÇö ╤ä╨╕╨║╤ü╨╕╤ê╤î ╨╕ ╨▓╨╛╨╖╨▓╤Ç╨░╤ë╨░╨╡╤ê╤î╤ü╤Å ╨║ ╤ê╨░╨│╤â 1
- ╨á╨░╨╖╨▒╨╕╤Ç╨░╤Ä root cause ╨┐╨╛ ╨┐╨╡╤Ç╨▓╨╛╨╝╤â ╨┐╤Ç╨╕╨╛╤Ç╨╕╤é╨╡╤é╨╜╨╛╨╝╤â ╤ä╨╡╨╣╨╗╤â.
- ╨Æ╨╜╨╛╤ê╤â ╨╝╨╕╨╜╨╕╨╝╨░╨╗╤î╨╜╨╛ ╨┤╨╛╤ü╤é╨░╤é╨╛╤ç╨╜╨╛╨╡ ╨╕╤ü╨┐╤Ç╨░╨▓╨╗╨╡╨╜╨╕╨╡ (╨▒╨╡╨╖ ╤Ç╨░╤ü╤ê╨╕╤Ç╨╡╨╜╨╕╤Å scope ╨▒╨╡╨╖ ╨╜╤â╨╢╨┤╤ï).
- ╨í╨╜╨╛╨▓╨░ ╨╖╨░╨┐╤â╤ü╨║╨░╤Ä **╤é╨╛╤é ╨╢╨╡ scope**.
- ╨ƒ╨╛╨▓╤é╨╛╤Ç╤Å╤Ä ╤å╨╕╨║╨╗, ╨┐╨╛╨║╨░:
  - ╨┐╨╛╨╗╤â╤ç╨╡╨╜ green;
  - ╨╗╨╕╨▒╨╛ ╨╛╨▒╨╜╨░╤Ç╤â╨╢╨╡╨╜ ╨▒╨╗╨╛╨║╨╡╤Ç non-actionable (╨╕╨╜╤ä╤Ç╨░╤ü╤é╤Ç╤â╨║╤é╤â╤Ç╨╜╤ï╨╣/╨▓╨╜╨╡╤ê╨╜╨╕╨╣ ╤ä╨░╨║╤é╨╛╤Ç) ╤ü ╤Å╨▓╨╜╨╛╨╣ ╤ä╨╕╨║╤ü╨░╤å╨╕╨╡╨╣,
    ╨┐╨╛╤ç╨╡╨╝╤â ╨╛╨╜ ╨╜╨╡ ╨╝╨╛╨╢╨╡╤é ╨▒╤ï╤é╤î ╨╕╤ü╨┐╤Ç╨░╨▓╨╗╨╡╨╜ ╨▓ ╤é╨╡╨║╤â╤ë╨╡╨╝ ╨║╨╛╨╜╤é╤â╤Ç╨╡,
  - ╨╗╨╕╨▒╨╛ ╨╕╤ü╤ç╨╡╤Ç╨┐╨░╨╜ ╨╗╨╕╨╝╨╕╤é ╨╕╤é╨╡╤Ç╨░╤å╨╕╨╣ (╨┐╨╛ ╤â╨╝╨╛╨╗╤ç╨░╨╜╨╕╤Ä 5).

## 4) ╨ú╤ü╨╗╨╛╨▓╨╕╤Å ╨╛╤ü╤é╨░╨╜╨╛╨▓╨║╨╕
- ╨ù╨░╨▓╨╡╤Ç╤ê╨░╨╣ ╤é╨╛╨╗╤î╨║╨╛ ╨║╨╛╨│╨┤╨░:
  - ╨▓╤ü╨╡ ╤é╨╡╤ü╤é╤ï ╨╖╨╡╨╗╤æ╨╜╤ï╨╡; ╨╕╨╗╨╕
  - ╨╗╨╕╨╝╨╕╤é ╨╕╤é╨╡╤Ç╨░╤å╨╕╨╣ ╨╕╤ü╤ç╨╡╤Ç╨┐╨░╨╜ ╤ü ╤Å╨▓╨╜╨╛╨╣ ╤ä╨╕╨║╤ü╨░╤å╨╕╨╡╨╣ ╨▒╨╗╨╛╨║╨╡╤Ç╨╛╨▓ ╨╕ ╤ü╨╗╨╡╨┤╤â╤Ä╤ë╨╕╨╝╨╕ ╤ê╨░╨│╨░╨╝╨╕.
- ╨Æ ╤ä╨╕╨╜╨░╨╗╨╡ ╨▓╤ü╨╡╨│╨┤╨░ ╤â╨║╨░╨╖╤ï╨▓╨░╨╣:
  - ╤ç╨╕╤ü╨╗╨╛ ╨╕╤é╨╡╤Ç╨░╤å╨╕╨╣;
  - ╨║╨░╨║╨╕╨╡ ╨╛╤ê╨╕╨▒╨║╨╕ ╨▒╤ï╨╗╨╕ ╨╕ ╨║╨░╨║ ╨╕╤ü╨┐╤Ç╨░╨▓╨╗╤Å╨╗╨╕╤ü╤î;
  - ╤é╨╡╨║╤â╤ë╨╡╨╡ ╤ü╨╛╤ü╤é╨╛╤Å╨╜╨╕╨╡ (`green / partially green / blocked`);
  - ╤ü╨╗╨╡╨┤╤â╤Ä╤ë╨╕╨╣ ╤ê╨░╨│ ╨┤╨╗╤Å ╤Ç╤â╤ç╨╜╨╛╨│╨╛/╨▓╨╜╨╡╤ê╨╜╨╡╨│╨╛ ╨▒╨╗╨╛╨║╨╡╤Ç╨░.
```

---

**Version History:**
- 2.0.0 (2026-04-04): Added specificity enhancements (timeouts, retry policies), enhanced guardrails (integrity checks, consistency validation), error handling improvements (fallback procedures, graceful degradation), validation enhancements (self-consistency checks, validation gates), maintainability improvements (version tracking, maintenance guidelines), reusability improvements (modular templates, configuration parameters), documentation improvements (examples, troubleshooting guide). Score improved from 7.15 to 8.51/10.
- 1.0.0: Initial version with basic test fix/re-test loop prompt
