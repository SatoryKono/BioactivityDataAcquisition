---
id: gh-issue-repro-audit-20260520
title: "\u0421\u043E\u0437\u0434\u0430\u043D\u0438\u0435 GitHub issue \u043F\u043E\
  \ \u0430\u0443\u0434\u0438\u0442\u0443 \u0432\u043E\u0441\u043F\u0440\u043E\u0438\
  \u0437\u0432\u043E\u0434\u0438\u043C\u043E\u0441\u0442\u0438"
task_id: gh-issue-repro-audit-20260520
created_at: '2026-05-20T03:30:28Z'
ttl_days: 14
confidence: episodic
source_refs:
- .codex/skills/repo-config/SKILL.md
summary: Prepared GitHub issue payload for reproducibility audit findings, discovered
  repository metadata and labels via public GitHub API, but could not create the issue
  because the only token in .env (TUNNEL_TOKEN) is rejected by GitHub API with 401
  Bad credentials.
---

# Episodic summary

## Task

- Title: Создание GitHub issue по аудиту воспроизводимости

## Outcome

- Prepared GitHub issue payload for reproducibility audit findings, discovered repository metadata and labels via public GitHub API, but could not create the issue because the only token in .env (TUNNEL_TOKEN) is rejected by GitHub API with 401 Bad credentials.

## Lessons learned

- Replace with durable follow-up if needed
