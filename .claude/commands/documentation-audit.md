---
description: "Полный аудит документации BioETL: синхронизация с кодом, соответствие ADR, обновление RULES.md и REQUIREMENTS.md."
---

# /documentation-audit

## Objective
Full documentation audit of BioETL, bring docs in sync with code and ADRs.

## Workflow

### 1. Intake
- Confirm repo root and target version
- Identify entry points: README.md, mkdocs.yml
- `rg --files docs`

### 2. Audit Checklist
- **RULES.md**: verify rules exist in code/configs, ADR-010/014/017 reflected
- **REQUIREMENTS.md**: each requirement maps to rule/implementation
- **Architecture docs**: diagrams match current modules
- **Provider docs**: each provider active, pipeline steps correct
- **Contract docs**: schemas match code models
- **Orphan docs**: check if referenced in mkdocs.yml
- **Cross-doc consistency**: no conflicting definitions

### 3. Plan
Turn findings into prioritized change list (Critical > High > Medium > Low).

### 4. Update (if requested)
Edit docs to match code. Keep versions/dates explicit. Propose delete/archive for obsolete docs.

### 5. Verify
- Check links and nav (mkdocs.yml)
- RULES.md ↔ REQUIREMENTS.md sync
- ADR references correct

## Commands
```bash
rg -n "ADR-010|ADR-014|ADR-017" docs README.md mkdocs.yml
rg -n "v5\.14|5\.14" docs README.md
rg --files docs
```

## Report Template
```
# Documentation Audit Report
## Summary: Date, Scope, Status
## Findings: Critical / High / Medium / Low
## Proposed changes (prioritized)
## Required decisions
## Dead/orphan docs
## Verification: RULES↔REQUIREMENTS sync, ADR alignment, link check
```

## Constraints
- **MUST** verify findings against actual code
- **MUST NOT** change code unless explicitly asked
- **MUST NOT** remove docs without approval
- **SHOULD** flag code↔doc divergence and propose options
