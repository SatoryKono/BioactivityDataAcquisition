---
id: chembl-activity-assay-alias-fix-20260518
title: "\u041F\u043E\u0447\u0438\u043D\u043A\u0430 alias/seam \u0440\u0435\u0433\u0440\
  \u0435\u0441\u0441\u0438\u0439 chembl_activity \u0438 chembl_assay"
task_id: chembl-activity-assay-alias-fix-20260518
created_at: '2026-05-18T19:34:51Z'
ttl_days: 14
confidence: episodic
source_refs:
- <add-source-ref>
summary: "\u041F\u043E\u0447\u0438\u043D\u0435\u043D alias seam \u0434\u043B\u044F\
  \ chembl_activity \u0438 chembl_assay: Silver \u0442\u0435\u043F\u0435\u0440\u044C\
  \ \u043F\u0443\u0431\u043B\u0438\u043A\u0443\u0435\u0442 canonical \u043F\u043E\u043B\
  \u044F activity_* \u0438 assay_description, \u0430 Gold \u043E\u0431\u0440\u0430\
  \u0442\u043D\u043E \u043F\u0440\u043E\u0435\u0446\u0438\u0440\u0443\u0435\u0442\
  \ legacy type/relation/value \u0438 description; entity/config/tests \u0441\u043E\
  \u0433\u043B\u0430\u0441\u043E\u0432\u0430\u043D\u044B."
---

# Episodic summary

## Task

- Title: Починка alias/seam регрессий chembl_activity и chembl_assay

## Outcome

- Починен alias seam для chembl_activity и chembl_assay: Silver теперь публикует canonical поля activity_* и assay_description, а Gold обратно проецирует legacy type/relation/value и description; entity/config/tests согласованы.

## Lessons learned

- Replace with durable follow-up if needed
