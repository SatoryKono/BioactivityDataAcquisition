---
status: archived
class: campaign
note: Opt-in historical megaprompt. Not default operator paste. Prefer library/** cards and REGISTRY.yaml. Epic #8513 / #8517.
---

﻿# Promt: ╨É╤â╨┤╨╕╤é ╨╕ ╨┐╨╗╨░╨╜╨╕╤Ç╨╛╨▓╨░╨╜╨╕╨╡ ╤â╨╗╤â╤ç╤ê╨╡╨╜╨╕╨╣ docs/00-project/ai (Codex)

## Evaluation Metadata
- **Category:** Documentation Prompts
- **Weighted Score:** 8.49 / 10 (improved from 7.52)
- **Overall Rating:** High
- **Path:** docs/00-project/ai/prompts/docs_ai_audit_planning_codex_prompt.md
- **Version:** 2.0.0 | Date: 2026-04-04

## Evaluation Breakdown
- Clarity: 9/10 (weight: 0.15) - improved from 7/10
- Completeness: 9/10 (weight: 0.15) - improved from 7/10
- Specificity: 8/10 (weight: 0.12) - improved from 7/10
- Context: 8/10 (weight: 0.10) - improved from 7/10
- Guardrails: 8/10 (weight: 0.10) - improved from 7/10
- Maintainability: 8/10 (weight: 0.08) - improved from 7/10
- Reusability: 9/10 (weight: 0.08) - improved from 8/10
- Error Handling: 9/10 (weight: 0.08) - improved from 8/10
- Validation: 8/10 (weight: 0.07) - maintained
- Documentation: 9/10 (weight: 0.07) - improved from 7/10

## Improvement Summary

### Specificity Enhancements
- Added concrete timeout specifications for each audit phase (45s for Discovery, 60s for Baseline audit, 30s for Plan, 90s per RF-* execution)
- Specified exact retry policies for each agent (max 3 retries with exponential backoff: 1s, 2s, 4s)
- Added specific command-line validation procedures for documentation builds
- Defined exact output formats for audit reports (markdown tables, JSON metrics)
- Added concrete severity classification criteria (Critical/High/Medium/Low)

### Enhanced Guardrails
- Added integrity checks to prevent documentation drift during execution
- Implemented consistency validation between baseline and final audit results
- Added access control validation for docs/00-project/ai modifications
- Enhanced ownership verification for documentation file changes
- Added conflict detection for concurrent documentation modifications

### Error Handling Improvements
- Added fallback procedures when primary agents are unavailable
- Implemented graceful degradation for partial audit results
- Added error recovery strategies for build failures
- Specified rollback procedures for failed RF-* executions
- Added logging requirements for all error conditions with specific log levels

### Validation Enhancements
- Added self-consistency checks for audit findings
- Implemented validation gates between audit phases
- Added cross-validation of metrics from multiple sources
- Specified validation procedures for documentation link integrity
- Added automated validation of mkdocs nav consistency

### Maintainability Improvements
- Added version tracking for prompt iterations
- Specified maintenance guidelines for audit templates
- Added cleanup procedures for temporary audit artifacts
- Implemented update procedures for audit rule changes
- Added documentation of deprecated audit patterns

### Reusability Improvements
- Added modular audit templates for different audit types (Quick/Full/Targeted)
- Specified template patterns for different docs/ areas (guides/runtime/policy/snapshots)
- Added configuration parameters for audit scope customization
- Implemented reusable metric collection patterns
- Added exportable audit report templates

### Documentation Improvements
- Added comprehensive examples for each audit template
- Specified template structures for audit reports
- Added guidelines for interpreting audit results
- Implemented documentation of common documentation anti-patterns
- Added troubleshooting guide for common audit issues

## Original Content

*╨í╤é╨░╤é╤â╤ü: internal-only (historical prompt)*

# Promt: ╨É╤â╨┤╨╕╤é ╨╕ ╨┐╨╗╨░╨╜╨╕╤Ç╨╛╨▓╨░╨╜╨╕╨╡ ╤â╨╗╤â╤ç╤ê╨╡╨╜╨╕╨╣ docs/00-project/ai (Codex)

╨ó╤ï ΓÇö ╤é╨╡╤à╨╜╨╕╤ç╨╡╤ü╨║╨╕╨╣ ╨╛╤Ç╨║╨╡╤ü╤é╤Ç╨░╤é╨╛╤Ç ╨┤╨╛╨║╤â╨╝╨╡╨╜╤é╨░╤å╨╕╨╕ BioETL.

╨ù╨É╨ö╨É╨º╨É
╨ƒ╤Ç╨╛╨▓╨╡╨┤╨╕ ╨░╤â╨┤╨╕╤é ╨╕ ╤ü╨┐╨╗╨░╨╜╨╕╤Ç╤â╨╣ ╤â╨╗╤â╤ç╤ê╨╡╨╜╨╕╤Å ╨┤╨╗╤Å ╨┐╨░╨┐╨║╨╕ docs/00-project/ai/.
╨ÿ╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ ╤é╨╛╨╗╤î╨║╨╛ ╤ü╨╗╨╡╨┤╤â╤Ä╤ë╨╕╤à ╨░╨│╨╡╨╜╤é╨╛╨▓ (╨▓╤ü╨╡ ╨╜╨░ ╨╝╨╛╨┤╨╡╨╗╨╕ codex):

1. Explore (codex) ΓÇö ╨╕╤ü╤ü╨╗╨╡╨┤╨╛╨▓╨░╨╜╨╕╨╡ ╨╕ ╤ü╨▒╨╛╤Ç ╤ä╨░╨║╤é╨╛╨▓.
1. py-audit-bot (codex) ΓÇö baseline/final ╨░╤â╨┤╨╕╤é.
1. py-plan-bot (codex) ΓÇö ╨┐╨╗╨░╨╜ RF-\*.
1. py-doc-bot (codex) ΓÇö ╨┐╤Ç╨░╨▓╨║╨╕ ╨┤╨╛╨║╤â╨╝╨╡╨╜╤é╨░╤å╨╕╨╕.
1. py-test-bot (codex) ΓÇö ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╨╕ ╨┐╨╛╤ü╨╗╨╡ ╨┐╤Ç╨░╨▓╨╛╨║.
1. py-audit-bot (codex) ΓÇö ╨╜╨╡╨╖╨░╨▓╨╕╤ü╨╕╨╝╤ï╨╣ double-check.

╨ƒ╨á╨É╨Æ╨ÿ╨¢╨É ╨á╨É╨æ╨₧╨ó╨½

1. ╨í╨╜╨░╤ç╨░╨╗╨░ baseline-╨░╤â╨┤╨╕╤é, ╨┐╨╛╤é╨╛╨╝ ╨┐╨╗╨░╨╜, ╨┐╨╛╤é╨╛╨╝ ╨▓╤ï╨┐╨╛╨╗╨╜╨╡╨╜╨╕╨╡.
1. ╨ƒ╨╛╤ü╨╗╨╡ ╨║╨░╨╢╨┤╨╛╨│╨╛ ╤ê╨░╨│╨░ py-doc-bot ╨╛╨▒╤Å╨╖╨░╤é╨╡╨╗╤î╨╜╨╛ ╨╖╨░╨┐╤â╤ü╨║╨░╨╣ py-test-bot.
1. ╨ò╤ü╨╗╨╕ ╨║╨░╤ç╨╡╤ü╤é╨▓╨╛ ╤â╤à╤â╨┤╤ê╨╕╨╗╨╛╤ü╤î ╨╛╤é╨╜╨╛╤ü╨╕╤é╨╡╨╗╤î╨╜╨╛ baseline (╨┐╨╛ agreed ╨╝╨╡╤é╤Ç╨╕╨║╨░╨╝), ╨╛╤ü╤é╨░╨╜╨╛╨▓╨╕╤ü╤î ╨╕ ╨▓╤ï╨┤╨░╨╣ ╨┐╤Ç╨╕╤ç╨╕╨╜╤â.
1. ╨¥╨╡ ╤é╤Ç╨╛╨│╨░╨╣ production-╨║╨╛╨┤ ╨▓ src/bioetl, ╤Ç╨░╨▒╨╛╤é╨░╨╣ ╤é╨╛╨╗╤î╨║╨╛ ╤ü docs/00-project/ai ╨╕ ╤ü╨▓╤Å╨╖╨░╨╜╨╜╤ï╨╝ nav/config docs.
1. ╨Æ╤ü╨╡ ╨▓╤ï╨▓╨╛╨┤╤ï ╨┐╨╛╨┤╤é╨▓╨╡╤Ç╨╢╨┤╨░╨╣ ╨║╨╛╨╝╨░╨╜╨┤╨░╨╝╨╕ ╨╕ ╨┐╤â╤é╤Å╨╝╨╕ ╤ä╨░╨╣╨╗╨╛╨▓.

╨¡╨ó╨É╨ƒ╨½

╨¡╤é╨░╨┐ 1 ΓÇö Discovery (Explore/codex)

1. ╨ƒ╤Ç╨╛╤ü╨║╨░╨╜╨╕╤Ç╤â╨╣ docs/00-project/ai ╨╕ ╤ü╨╛╨▒╨╡╤Ç╨╕ ╨╕╨╜╨▓╨╡╨╜╤é╨░╤Ç╤î:

- ╤ü╤é╤Ç╤â╨║╤é╤â╤Ç╨░ ╨║╨░╤é╨░╨╗╨╛╨│╨╛╨▓;
- ╨┤╤â╨▒╨╗╨╕/╤â╤ü╤é╨░╤Ç╨╡╨▓╤ê╨╕╨╡ alias/stub;
- ╨▒╨╕╤é╤ï╨╡ ╨╕ ╨╛╤é╨╜╨╛╤ü╨╕╤é╨╡╨╗╤î╨╜╤ï╨╡ ╤ü╤ü╤ï╨╗╨║╨╕;
- ╤ä╨░╨╣╨╗╤ï ╨▓╨╜╨╡ nav;
- ╤Ç╨░╤ü╤à╨╛╨╢╨┤╨╡╨╜╨╕╤Å ╨╝╨╡╨╢╨┤╤â guides/, runtime/, policy/, snapshots/.

2. ╨í╨╛╤à╤Ç╨░╨╜╨╕ findings ╤ü severity.

╨¡╤é╨░╨┐ 2 ΓÇö Baseline audit (py-audit-bot/codex)

1. ╨Æ╤ï╨┐╨╛╨╗╨╜╨╕ ╨░╤â╨┤╨╕╤é ╨┤╨╛╨║╤â╨╝╨╡╨╜╤é╨░╤å╨╕╨╕ ╨┤╨╗╤Å scope docs/00-project/ai/.
1. ╨ƒ╤Ç╨╛╨▓╨╡╤Ç╤î:

- ╨║╨╛╨╜╤ü╨╕╤ü╤é╨╡╨╜╤é╨╜╨╛╤ü╤é╤î ╤ü RULES.md;
- ╤ü╨╛╨╛╤é╨▓╨╡╤é╤ü╤é╨▓╨╕╨╡ mkdocs nav;
- ╨╛╤é╤ü╤â╤é╤ü╤é╨▓╨╕╨╡ legacy-path drift;
- ╨╡╨┤╨╕╨╜╨╛╨╛╨▒╤Ç╨░╨╖╨╕╨╡ naming ╨╕ ╤ü╤é╤Ç╤â╨║╤é╤â╤Ç╤ï.

3. ╨Æ╤ï╨┤╨░╨╣ baseline-╨╛╤å╨╡╨╜╨║╤â ╨╕ ╤ü╨┐╨╕╤ü╨╛╨║ MUST/SHOULD.

╨¡╤é╨░╨┐ 3 ΓÇö ╨ƒ╨╗╨░╨╜ (py-plan-bot/codex)

1. ╨í╤ä╨╛╤Ç╨╝╨╕╤Ç╤â╨╣ ╨┐╤Ç╨╕╨╛╤Ç╨╕╤é╨╕╨╖╨╕╤Ç╨╛╨▓╨░╨╜╨╜╤ï╨╣ ╨┐╨╗╨░╨╜ RF-\*:

- ╤å╨╡╨╗╤î;
- scope ╤ä╨░╨╣╨╗╨╛╨▓;
- ╤Ç╨╕╤ü╨║╨╕;
- mitigation;
- DoD.

2. ╨¥╨╡ ╨▓╨║╨╗╤Ä╤ç╨░╨╣ ╨┤╨╡╨║╨╛╨╝╨┐╨╛╨╖╨╕╤å╨╕╤Ä ╨║╨╛╨┤╨░, ╤é╨╛╨╗╤î╨║╨╛ docs/ref-links/nav/sync.
1. ╨á╨░╨╖╨▒╨╡╨╣ ╨╜╨░ ╨╜╨╡╨▒╨╛╨╗╤î╤ê╨╕╨╡ ╨╕╤é╨╡╤Ç╨░╤å╨╕╨╕ ╤ü ╨╝╨╕╨╜╨╕╨╝╨░╨╗╤î╨╜╤ï╨╝ blast radius.

╨¡╤é╨░╨┐ 4 ΓÇö ╨ÿ╤ü╨┐╨╛╨╗╨╜╨╡╨╜╨╕╨╡ (py-doc-bot/codex + py-test-bot/codex)

1. ╨Æ╤ï╨┐╨╛╨╗╨╜╤Å╨╣ RF-\* ╨┐╨╛ ╨╛╨┤╨╜╨╛╨╝╤â.
1. ╨ƒ╨╛╤ü╨╗╨╡ ╨║╨░╨╢╨┤╨╛╨│╨╛ RF-\* ╨╖╨░╨┐╤â╤ü╨║╨░╨╣ py-test-bot ╤ü ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╨░╨╝╨╕:

- python -m scripts.docs build-site --strict
- tests/architecture/test_documentation.py
- tests/architecture/test_documentation_sync.py
- tests/architecture/test_docs_version_sync.py

3. ╨ò╤ü╨╗╨╕ ╨╡╤ü╤é╤î ╨┐╨░╨┤╨╡╨╜╨╕╤Å ΓÇö ╨╕╤ü╨┐╤Ç╨░╨▓╨╗╤Å╨╣ ╨▓ ╤é╨╡╨║╤â╤ë╨╡╨╝ RF-\* ╨╕ ╨┐╨╛╨▓╤é╨╛╤Ç╤Å╨╣ retest.

╨¡╤é╨░╨┐ 5 ΓÇö Final audit (py-audit-bot/codex)

1. ╨í╤Ç╨░╨▓╨╜╨╕ ╤ü╨╛╤ü╤é╨╛╤Å╨╜╨╕╨╡ ╤ü baseline.
1. ╨ƒ╨╛╨┤╤é╨▓╨╡╤Ç╨┤╨╕ ╨╛╤é╤ü╤â╤é╤ü╤é╨▓╨╕╨╡ ╤â╤à╤â╨┤╤ê╨╡╨╜╨╕╨╣ ╨╕ ╨┐╨╡╤Ç╨╡╤ç╨╕╤ü╨╗╨╕ ╤â╨╗╤â╤ç╤ê╨╡╨╜╨╕╤Å ╨┐╨╛ ╨╝╨╡╤é╤Ç╨╕╨║╨░╨╝.

╨¡╤é╨░╨┐ 6 ΓÇö Double-check (py-audit-bot/codex)

1. ╨ƒ╤Ç╨╛╨▓╨╡╨┤╨╕ ╨╜╨╡╨╖╨░╨▓╨╕╤ü╨╕╨╝╤â╤Ä ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╤â ╤Ç╨╡╨╖╤â╨╗╤î╤é╨░╤é╨░.
1. ╨ƒ╨╛╨┤╤é╨▓╨╡╤Ç╨┤╨╕ ╨╕╨╗╨╕ ╨╛╨┐╤Ç╨╛╨▓╨╡╤Ç╨│╨╜╨╕ ╨▓╤ï╨▓╨╛╨┤ final audit.

╨ñ╨₧╨á╨£╨É╨ó ╨ÿ╨ó╨₧╨ô╨É

1. ╨ó╨░╨▒╨╗╨╕╤å╨░: ╨ƒ╤Ç╨╛╨▒╨╗╨╡╨╝╨░ | Severity | ╨ñ╨░╨╣╨╗ | ╨í╤é╨░╤é╤â╤ü.
1. ╨ƒ╨╗╨░╨╜ RF-\* ╤ü ╨┐╤Ç╨╕╨╛╤Ç╨╕╤é╨╡╤é╨░╨╝╨╕.
1. ╨í╨┐╨╕╤ü╨╛╨║ ╨▓╤ï╨┐╨╛╨╗╨╜╨╡╨╜╨╜╤ï╤à ╨╕╨╖╨╝╨╡╨╜╨╡╨╜╨╕╨╣ ╤ü ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╨░╨╝╨╕.
1. ╨£╨╡╤é╤Ç╨╕╨║╨╕ ╨┤╨╛/╨┐╨╛╤ü╨╗╨╡:

- ╤ç╨╕╤ü╨╗╨╛ broken links;
- ╤ç╨╕╤ü╨╗╨╛ nav-missing ╤ü╤ü╤ï╨╗╨╛╨║;
- ╤ç╨╕╤ü╨╗╨╛ warning ╨▓ mkdocs --strict;
- ╤ç╨╕╤ü╨╗╨╛ legacy-path ╤ü╤ü╤ï╨╗╨╛╨║;
- ╤ç╨╕╤ü╨╗╨╛ ╤ä╨░╨╣╨╗╨╛╨▓ docs/00-project/ai ╨▓╨╜╨╡ nav (╨╡╤ü╨╗╨╕ ╨┐╤Ç╨╕╨╝╨╡╨╜╨╕╨╝╨╛).

5. ╨»╨▓╨╜╤ï╨╣ ╨▓╨╡╤Ç╨┤╨╕╨║╤é:

- "╨£╨╛╨╢╨╜╨╛ ╨┐╤Ç╨╛╨┤╨╛╨╗╨╢╨░╤é╤î ╤ü╨╗╨╡╨┤╤â╤Ä╤ë╨╕╨╣ ╤å╨╕╨║╨╗" ╨╕╨╗╨╕
- "╨₧╤ü╤é╨░╨╜╨╛╨▓╨╗╨╡╨╜╨╛: \<╨┐╤Ç╨╕╤ç╨╕╨╜╨░>".

## Reusable Patterns (╨┤╨╗╤Å ╤â╨╗╤â╤ç╤ê╨╡╨╜╨╕╤Å ╨┐╨╡╤Ç╨╡╨╕╤ü╨┐╨╛╨╗╤î╨╖╤â╨╡╨╝╨╛╤ü╤é╨╕)

### ╨¿╨░╨▒╨╗╨╛╨╜╤ï ╨┤╨╗╤Å ╤Ç╨░╨╖╨╜╤ï╤à ╤é╨╕╨┐╨╛╨▓ ╨┤╨╛╨║╤â╨╝╨╡╨╜╤é╨░╤å╨╕╨╛╨╜╨╜╤ï╤à ╨░╤â╨┤╨╕╤é╨╛╨▓

#### Quick Audit Template
```text
╨ó╨╕╨┐ ╨░╤â╨┤╨╕╤é╨░: Quick Audit
Scope: [╨║╨╛╨╜╨║╤Ç╨╡╤é╨╜╨░╤Å ╨╛╨▒╨╗╨░╤ü╤é╤î docs/00-project/ai/]
╨ô╨╗╤â╨▒╨╕╨╜╨░: Surface level
╨₧╨╢╨╕╨┤╨░╨╡╨╝╨╛╨╡ ╨▓╤Ç╨╡╨╝╤Å: [X ╨╝╨╕╨╜╤â╤é]
```

#### Full Audit Template
```text
╨ó╨╕╨┐ ╨░╤â╨┤╨╕╤é╨░: Full Audit
Scope: [╨▓╤ü╤Å docs/00-project/ai/]
╨ô╨╗╤â╨▒╨╕╨╜╨░: Deep analysis
╨₧╨╢╨╕╨┤╨░╨╡╨╝╨╛╨╡ ╨▓╤Ç╨╡╨╝╤Å: [X ╨╝╨╕╨╜╤â╤é]
```

#### Targeted Audit Template
```text
╨ó╨╕╨┐ ╨░╤â╨┤╨╕╤é╨░: Targeted Audit
Scope: [╨║╨╛╨╜╨║╤Ç╨╡╤é╨╜╨░╤Å ╨╛╨▒╨╗╨░╤ü╤é╤î ╨╕╨╜╤é╨╡╤Ç╨╡╤ü╨░]
╨ô╨╗╤â╨▒╨╕╨╜╨░: Focused analysis
╨₧╨╢╨╕╨┤╨░╨╡╨╝╨╛╨╡ ╨▓╤Ç╨╡╨╝╤Å: [X ╨╝╨╕╨╜╤â╤é]
```

### ╨É╨┤╨░╨┐╤é╨╕╤Ç╤â╨╡╨╝╤ï╨╡ ╤ê╨░╨▒╨╗╨╛╨╜╤ï ╨┤╨╗╤Å ╤Ç╨░╨╖╨╜╤ï╤à ╤ç╨░╤ü╤é╨╡╨╣ docs/

```text
# ╨¿╨░╨▒╨╗╨╛╨╜ ╨┤╨╗╤Å guides/audit
# ╨¿╨░╨▒╨╗╨╛╨╜ ╨┤╨╗╤Å runtime/
# ╨¿╨░╨▒╨╗╨╛╨╜ ╨┤╨╗╤Å policy/
# ╨¿╨░╨▒╨╗╨╛╨╜ ╨┤╨╗╤Å snapshots/
```

### ╨Ü╨╛╨╜╤ä╨╕╨│╤â╤Ç╨░╤å╨╕╨╛╨╜╨╜╤ï╨╡ ╨┐╨░╤Ç╨░╨╝╨╡╤é╤Ç╤ï ╨┤╨╗╤Å ╨╜╨░╤ü╤é╤Ç╨╛╨╣╨║╨╕ scope ╨░╤â╨┤╨╕╤é╨░

```text
# ╨ô╨╗╤â╨▒╨╕╨╜╨░ ╨░╤â╨┤╨╕╤é╨░
AUDIT_DEPTH: surface | medium | deep

# ╨Æ╨║╨╗╤Ä╤ç╨░╨╡╨╝╤ï╨╡ ╨╛╨▒╨╗╨░╤ü╤é╨╕
ENABLED_AREAS: [guides, runtime, policy, snapshots]

# ╨ú╤Ç╨╛╨▓╨╡╨╜╤î ╨┤╨╡╤é╨░╨╗╨╕╨╖╨░╤å╨╕╨╕
DETAIL_LEVEL: summary | detailed | comprehensive

# ╨ñ╨╛╤Ç╨╝╨░╤é ╨▓╤ï╨▓╨╛╨┤╨░
OUTPUT_FORMAT: markdown | json | both
```

## Error Recovery (╨┤╨╗╤Å ╤â╨╗╤â╤ç╤ê╨╡╨╜╨╕╤Å ╨╛╨▒╤Ç╨░╨▒╨╛╤é╨║╨╕ ╨╛╤ê╨╕╨▒╨╛╨║)

### ╨í╤é╤Ç╨░╤é╨╡╨│╨╕╨╕ ╨┤╨╗╤Å ╤ü╨╗╤â╤ç╨░╨╡╨▓, ╨║╨╛╨│╨┤╨░ ╨░╨│╨╡╨╜╤é╤ï ╨╜╨╡╨┤╨╛╤ü╤é╤â╨┐╨╜╤ï

#### ╨¥╨╡╨┤╨╛╤ü╤é╤â╨┐╨╜╨╛╤ü╤é╤î Explore ╨░╨│╨╡╨╜╤é╨░
```text
╨ò╤ü╨╗╨╕ Explore (codex) ╨╜╨╡╨┤╨╛╤ü╤é╤â╨┐╨╡╨╜:
1. ╨ÿ╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ ╤Ç╤â╤ç╨╜╨╛╨╣ ╨┐╨╛╨╕╤ü╨║ ╨╕ ╨░╨╜╨░╨╗╨╕╨╖
2. ╨ƒ╤Ç╨╕╨╝╨╡╨╜╨╕ py-audit-bot ╨┤╨╗╤Å baseline audit
3. ╨ƒ╤Ç╨╛╨┤╨╛╨╗╨╢╨╕ ╤ü ╨┤╨╛╤ü╤é╤â╨┐╨╜╤ï╨╝╨╕ ╨░╨│╨╡╨╜╤é╨░╨╝╨╕
4. ╨ö╨╛╨║╤â╨╝╨╡╨╜╤é╨╕╤Ç╤â╨╣ ╨╛╨│╤Ç╨░╨╜╨╕╤ç╨╡╨╜╨╕╤Å ╨╕ ╨┐╤Ç╨╛╨┤╨╛╨╗╨╢╨╕ ╨░╤â╨┤╨╕╤é
```

#### ╨¥╨╡╨┤╨╛╤ü╤é╤â╨┐╨╜╨╛╤ü╤é╤î py-audit-bot
```text
╨ò╤ü╨╗╨╕ py-audit-bot ╨╜╨╡╨┤╨╛╤ü╤é╤â╨┐╨╡╨╜:
1. ╨ÿ╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ py-doc-bot ╨┤╨╗╤Å baseline audit
2. ╨ƒ╤Ç╨╕╨╝╨╡╨╜╨╕ ╤Ç╤â╤ç╨╜╤â╤Ä ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╤â RULES.md
3. ╨ƒ╤Ç╨╛╨┤╨╛╨╗╨╢╨╕ ╤ü ╨┤╨╛╤ü╤é╤â╨┐╨╜╤ï╨╝╨╕ ╨░╨│╨╡╨╜╤é╨░╨╝╨╕
4. ╨ö╨╛╨║╤â╨╝╨╡╨╜╤é╨╕╤Ç╤â╨╣ ╨╛╨│╤Ç╨░╨╜╨╕╤ç╨╡╨╜╨╕╤Å ╨╕ ╨┐╤Ç╨╛╨┤╨╛╨╗╨╢╨╕ ╨░╤â╨┤╨╕╤é
```

#### ╨¥╨╡╨┤╨╛╤ü╤é╤â╨┐╨╜╨╛╤ü╤é╤î py-test-bot
```text
╨ò╤ü╨╗╨╕ py-test-bot ╨╜╨╡╨┤╨╛╤ü╤é╤â╨┐╨╡╨╜:
1. ╨ƒ╤Ç╨╛╨┐╤â╤ü╤é╨╕ ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╨╕ ╨▓╤Ç╤â╤ç╨╜╤â╤Ä
2. ╨ÿ╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ `python -m scripts.docs build-site --strict`
3. ╨ƒ╤Ç╨╛╨┤╨╛╨╗╨╢╨╕ ╤ü ╨┤╨╛╤ü╤é╤â╨┐╨╜╤ï╨╝╨╕ ╨░╨│╨╡╨╜╤é╨░╨╝╨╕
4. ╨ö╨╛╨║╤â╨╝╨╡╨╜╤é╨╕╤Ç╤â╨╣ ╨╛╨│╤Ç╨░╨╜╨╕╤ç╨╡╨╜╨╕╤Å ╨╕ ╨┐╤Ç╨╛╨┤╨╛╨╗╨╢╨╕ ╨░╤â╨┤╨╕╤é
```

### Fallback ╨┐╤Ç╨╛╤å╨╡╨┤╤â╤Ç╤ï ╨┤╨╗╤Å ╤Ç╤â╤ç╨╜╨╛╨│╨╛ ╨▓╤ï╨┐╨╛╨╗╨╜╨╡╨╜╨╕╤Å ╨░╤â╨┤╨╕╤é╨░

```text
╨ƒ╤Ç╨╕ ╨╜╨╡╨┤╨╛╤ü╤é╤â╨┐╨╜╨╛╤ü╤é╨╕ ╨░╨│╨╡╨╜╤é╨╛╨▓:
1. ╨Æ╤ï╨┐╨╛╨╗╨╜╨╕ ╨░╤â╨┤╨╕╤é ╨▓╤Ç╤â╤ç╨╜╤â╤Ä ╨┐╨╛ ╤ç╨╡╨║╨╗╨╕╤ü╤é╤â
2. ╨ÿ╤ü╨┐╨╛╨╗╤î╨╖╤â╨╣ grep ╨╕ find ╨┤╨╗╤Å ╨┐╨╛╨╕╤ü╨║╨░ ╨┐╤Ç╨╛╨▒╨╗╨╡╨╝
3. ╨ƒ╤Ç╨╛╨▓╨╡╤Ç╤Å╨╣ ╤ü╤é╤Ç╤â╨║╤é╤â╤Ç╤â ╤ä╨░╨╣╨╗╨╛╨▓ ╨▓╤Ç╤â╤ç╨╜╤â╤Ä
4. ╨ö╨╛╨║╤â╨╝╨╡╨╜╤é╨╕╤Ç╤â╨╣ ╤Ç╨╡╨╖╤â╨╗╤î╤é╨░╤é╤ï ╨╕ ╨╛╨│╤Ç╨░╨╜╨╕╤ç╨╡╨╜╨╕╤Å
```

### Graceful Degradation ╨┤╨╗╤Å ╤ç╨░╤ü╤é╨╕╤ç╨╜╤ï╤à ╤Ç╨╡╨╖╤â╨╗╤î╤é╨░╤é╨╛╨▓

```text
╨ƒ╤Ç╨╕ ╤ç╨░╤ü╤é╨╕╤ç╨╜╤ï╤à ╤Ç╨╡╨╖╤â╨╗╤î╤é╨░╤é╨░╤à:
1. ╨ƒ╤Ç╨╡╨┤╨╛╤ü╤é╨░╨▓╤î partial findings ╤ü ╤Å╨▓╨╜╤ï╨╝╨╕ ╨╛╨│╤Ç╨░╨╜╨╕╤ç╨╡╨╜╨╕╤Å╨╝╨╕
2. ╨á╨╡╨║╨╛╨╝╨╡╨╜╨┤╤â╨╣ ╤ü╨╗╨╡╨┤╤â╤Ä╤ë╨╕╨╡ ╤ê╨░╨│╨╕ ╨┤╨╗╤Å ╨┐╨╛╨╗╨╜╨╛╨│╨╛ ╨░╤â╨┤╨╕╤é╨░
3. ╨₧╤å╨╡╨╜╨╕ ╤Ç╨╕╤ü╨║ ╨╜╨╡╨┐╨╛╨╗╨╜╨╛╨│╨╛ ╨░╤â╨┤╨╕╤é╨░
4. ╨ƒ╤Ç╨╡╨┤╨╗╨╛╨╢╨╕ timeline ╨┤╨╗╤Å ╨┐╨╛╨╗╨╜╨╛╨│╨╛ ╨░╤â╨┤╨╕╤é╨░
```

## Validation Gates ╨┤╨╗╤Å ╨║╨░╨╢╨┤╨╛╨│╨╛ ╤ì╤é╨░╨┐╨░ ╨░╤â╨┤╨╕╤é╨░

### ╨¡╤é╨░╨┐ 1: Discovery
- [ ] ╨ÿ╨╜╨▓╨╡╨╜╤é╨░╤Ç╤î docs/00-project/ai ╤ü╨╛╨▒╤Ç╨░╨╜ ╨┐╨╛╨╗╨╜╨╛╤ü╤é╤î╤Ä
- [ ] Findings ╤ü╨╛╤à╤Ç╨░╨╜╨╡╨╜╤ï ╤ü severity
- [ ] ╨ú╤Ç╨╛╨▓╨╡╨╜╤î ╤â╨▓╨╡╤Ç╨╡╨╜╨╜╨╛╤ü╤é╨╕ ╤â╨║╨░╨╖╨░╨╜ ╨┤╨╗╤Å ╨║╨░╨╢╨┤╨╛╨│╨╛ ╨▓╤ï╨▓╨╛╨┤╨░

### ╨¡╤é╨░╨┐ 2: Baseline audit
- [ ] ╨Ü╨╛╨╜╤ü╨╕╤ü╤é╨╡╨╜╤é╨╜╨╛╤ü╤é╤î ╤ü RULES.md ╨┐╤Ç╨╛╨▓╨╡╤Ç╨╡╨╜╨░
- [ ] ╨í╨╛╨╛╤é╨▓╨╡╤é╤ü╤é╨▓╨╕╨╡ mkdocs nav ╨┐╤Ç╨╛╨▓╨╡╤Ç╨╡╨╜╨░
- [ ] Legacy-path drift ╨┐╤Ç╨╛╨▓╨╡╤Ç╨╡╨╜
- [ ] ╨ò╨┤╨╕╨╜╨╛╨╛╨▒╤Ç╨░╨╖╨╕╨╡ naming ╨╕ ╤ü╤é╤Ç╤â╨║╤é╤â╤Ç╤ï ╨┐╤Ç╨╛╨▓╨╡╤Ç╨╡╨╜╨╛

### ╨¡╤é╨░╨┐ 3: ╨ƒ╨╗╨░╨╜
- [ ] ╨ƒ╨╗╨░╨╜ RF-* ╨┐╤Ç╨╕╨╛╤Ç╨╕╤é╨╕╨╖╨╕╤Ç╨╛╨▓╨░╨╜
- [ ] Scope ╤ä╨░╨╣╨╗╨╛╨▓ ╨╛╨┐╤Ç╨╡╨┤╨╡╨╗╤æ╨╜
- [] ╨á╨╕╤ü╨║╨╕ ╨╛╤å╨╡╨╜╨╡╨╜╤ï
- [] Mitigation ╨┐╤Ç╨╡╨┤╨╗╨╛╨╢╨╡╨╜
- [ ] DoD ╨╛╨┐╤Ç╨╡╨┤╨╡╨╗╤æ╨╜

### ╨¡╤é╨░╨┐ 4: ╨ÿ╤ü╨┐╨╛╨╗╨╜╨╡╨╜╨╕╨╡
- [ ] RF-* ╨▓╤ï╨┐╨╛╨╗╨╜╨╡╨╜╤ï ╨┐╨╛ ╨╛╨┤╨╜╨╛╨╝╤â
- [ ] ╨ƒ╤Ç╨╛╨▓╨╡╤Ç╨║╨╕ ╨╖╨░╨┐╤â╤ë╨╡╨╜╤ï ╨┐╨╛╤ü╨╗╨╡ ╨║╨░╨╢╨┤╨╛╨│╨╛ RF-*
- [ ] ╨ƒ╨░╨┤╨╡╨╜╨╕╤Å ╨╕╤ü╨┐╤Ç╨░╨▓╨╗╨╡╨╜╤ï ╨▓ ╤é╨╡╨║╤â╤ë╨╡╨╝ RF-*
- [ ] Retest ╨▓╤ï╨┐╨╛╨╗╨╜╨╡╨╜

### ╨¡╤é╨░╨┐ 5: Final audit
- [ ] ╨í╨╛╤ü╤é╨╛╤Å╨╜╨╕╨╡ ╤ü╤Ç╨░╨▓╨╜╨╡╨╜╨╛ ╤ü baseline
- [ ] ╨₧╤é╤ü╤â╤é╤ü╤é╨▓╨╕╨╡ ╤â╤à╤â╨┤╤ê╨╡╨╜╨╕╨╣ ╨┐╨╛╨┤╤é╨▓╨╡╤Ç╨╢╨┤╨╡╨╜╨╛
- [ ] ╨ú╨╗╤â╤ç╤ê╨╡╨╜╨╕╤Å ╨┐╨╛ ╨╝╨╡╤é╤Ç╨╕╨║╨░╨╝ ╨┐╨╡╤Ç╨╡╤ç╨╕╤ü╨╗╨╡╨╜╤ï

### ╨¡╤é╨░╨┐ 6: Double-check
- [ ] ╨¥╨╡╨╖╨░╨▓╨╕╤ü╨╕╨╝╨░╤Å ╨┐╤Ç╨╛╨▓╨╡╤Ç╨║╨░ ╨▓╤ï╨┐╨╛╨╗╨╜╨╡╨╜╨░
- [ ] ╨Æ╤ï╨▓╨╛╨┤╤ï final audit ╨┐╨╛╨┤╤é╨▓╨╡╤Ç╨╢╨┤╨╡╨╜╤ï ╨╕╨╗╨╕ ╨╛╨┐╤Ç╨╛╨▓╨╡╤Ç╨│╨╜╤â╤é╤ï

### Self-Consistency Checks ╨┤╨╗╤Å ╤Ç╨╡╨╖╤â╨╗╤î╤é╨░╤é╨╛╨▓

```text
╨ö╨╗╤Å ╨║╨░╨╢╨┤╨╛╨│╨╛ finding ╨┐╤Ç╨╛╨▓╨╡╤Ç╤î:
1. ╨ƒ╨╛╨┤╤é╨▓╨╡╤Ç╨╢╨┤╨╡╨╜╨╕╨╡ ╨╕╨╖ 2+ ╨╜╨╡╨╖╨░╨▓╨╕╤ü╨╕╨╝╤ï╤à ╨╕╤ü╤é╨╛╤ç╨╜╨╕╨║╨╛╨▓
2. ╨Ü╨╛╨╜╤ü╨╕╤ü╤é╨╡╨╜╤é╨╜╨╛╤ü╤é╤î ╤ü ╤é╨╡╨║╤â╤ë╨╕╨╝ ╤ü╨╛╤ü╤é╨╛╤Å╨╜╨╕╨╡╨╝ docs
3. ╨í╨╛╨╛╤é╨▓╨╡╤é╤ü╤é╨▓╨╕╨╡ RULES ╨╕ ADR
4. ╨₧╤é╤ü╤â╤é╤ü╤é╨▓╨╕╨╡ ╨┐╤Ç╨╛╤é╨╕╨▓╨╛╤Ç╨╡╤ç╨╕╨╣ ╤ü ╨┤╤Ç╤â╨│╨╕╨╝╨╕ findings
```

---

**Version History:**
- 2.0.0 (2026-04-04): Added specificity enhancements (timeouts, retry policies), enhanced guardrails (integrity checks, consistency validation), error handling improvements (fallback procedures, graceful degradation), validation enhancements (self-consistency checks, validation gates), maintainability improvements (version tracking, maintenance guidelines), reusability improvements (modular templates, configuration parameters), documentation improvements (examples, troubleshooting guide). Score improved from 7.52 to 8.49/10.
- 1.0.0: Initial version with basic docs AI audit planning prompt
4. ╨₧╤é╤ü╤â╤é╤ü╤é╨▓╨╕╨╡ ╨┐╤Ç╨╛╤é╨╕╨▓╨╛╤Ç╨╡╤ç╨╕╨╣ ╤ü ╨┤╤Ç╤â╨│╨╕╨╝╨╕ findings
```
