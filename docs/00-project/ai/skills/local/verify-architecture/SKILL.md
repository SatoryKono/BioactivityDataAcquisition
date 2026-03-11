---
name: verify-architecture
description: Run architecture compliance checks for BioETL (quick/full/category modes) before commit or PR.
---

# Verify Architecture

*Статус: internal-published (Internal / Extended)*

## Objective
Execute architecture validation checks and report blocking/non-blocking issues.

## Source Of Truth
- Codex SSOT: `.codex/skills/verify-architecture/SKILL.md`
- Claude runtime: `.claude/commands/verify-architecture.md`

## Workflow
1. Open and follow the SSOT skill file for your active runtime.
2. Select mode (`quick`, `full`, `category`) based on request scope.
3. Adapt command examples to the active shell and installed toolchain.
4. Report findings with failing tests/checks and actionable next fixes.

## Notes
- The `.codex/skills/` directory is canonical for test groupings and command sets.
