---
id: fix-coalesce-policy-loc
title: "\u0421\u043D\u0438\u0436\u0435\u043D\u0438\u0435 LOC coalesce_policy"
task_id: fix-coalesce-policy-loc
created_at: '2026-06-19T10:51:12Z'
ttl_days: 14
confidence: episodic
source_refs:
- src/bioetl/application/composite/coalesce_policy.py
summary: "\u0412\u044B\u043D\u0435\u0441 internal helpers \u0438\u0437 application/composite/coalesce_policy.py\
  \ \u0432 \u043F\u0440\u0438\u0432\u0430\u0442\u043D\u044B\u0439 \u043C\u043E\u0434\
  \u0443\u043B\u044C _coalesce_policy_support.py, \u0441\u043E\u043A\u0440\u0430\u0442\
  \u0438\u0432 coalesce_policy.py \u0441 593 \u0434\u043E 232 LOC \u0431\u0435\u0437\
  \ \u0438\u0437\u043C\u0435\u043D\u0435\u043D\u0438\u044F \u043F\u0443\u0431\u043B\
  \u0438\u0447\u043D\u043E\u0433\u043E API CoalescePolicyService. \u041F\u043E\u0434\
  \u0442\u0432\u0435\u0440\u0436\u0434\u0435\u043D\u044B unit \u0438 \u0430\u0440\u0445\
  \u0438\u0442\u0435\u043A\u0442\u0443\u0440\u043D\u044B\u0439 LOC checks; refresh\
  \ module-coverage inventory source_tree_sha256 \u043F\u0440\u043E\u043F\u0443\u0449\
  \u0435\u043D, \u043F\u043E\u0442\u043E\u043C\u0443 \u0447\u0442\u043E committed\
  \ artifact \u0443\u0436\u0435 dirty \u0438 \u0433\u0435\u043D\u0435\u0440\u0430\u0442\
  \u043E\u0440 \u0432 \u044D\u0442\u043E\u043C worktree \u043F\u043E\u0434\u0445\u0432\
  \u0430\u0442\u044B\u0432\u0430\u0435\u0442 \u043D\u0435\u0441\u0432\u044F\u0437\u0430\
  \u043D\u043D\u044B\u0435 \u043F\u043E\u043B\u044C\u0437\u043E\u0432\u0430\u0442\u0435\
  \u043B\u044C\u0441\u043A\u0438\u0435 src-\u0438\u0437\u043C\u0435\u043D\u0435\u043D\
  \u0438\u044F."
---

# Episodic summary

## Task

- Title: Снижение LOC coalesce_policy

## Outcome

- Вынес internal helpers из application/composite/coalesce_policy.py в приватный модуль _coalesce_policy_support.py, сократив coalesce_policy.py с 593 до 232 LOC без изменения публичного API CoalescePolicyService. Подтверждены unit и архитектурный LOC checks; refresh module-coverage inventory source_tree_sha256 пропущен, потому что committed artifact уже dirty и генератор в этом worktree подхватывает несвязанные пользовательские src-изменения.

## Lessons learned

- Replace with durable follow-up if needed
