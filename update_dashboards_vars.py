#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json
import sys

# Шаблон для переменных
template_vars = [
    {
        "allValue": None,
        "current": {},
        "datasource": "Prometheus",
        "definition": "label_values(bioetl_records_processed_total, pipeline)",
        "hide": 0,
        "includeAll": True,
        "label": "Pipeline",
        "multi": True,
        "name": "pipeline",
        "options": [],
        "query": {
            "query": "label_values(bioetl_records_processed_total, pipeline)",
            "refId": "StandardVariableQuery"
        },
        "refresh": 1,
        "regex": "",
        "skipUrlSync": False,
        "sort": 1,
        "tagValuesQuery": "",
        "tags": [],
        "tagsQuery": "",
        "type": "query",
        "useTags": False
    },
    {
        "allValue": None,
        "current": {},
        "datasource": "Prometheus",
        "definition": "label_values(bioetl_records_processed_total{pipeline=~\"$pipeline\"}, run_id)",
        "hide": 0,
        "includeAll": True,
        "label": "Run ID",
        "multi": True,
        "name": "run_id",
        "options": [],
        "query": {
            "query": "label_values(bioetl_records_processed_total{pipeline=~\"$pipeline\"}, run_id)",
            "refId": "StandardVariableQuery"
        },
        "refresh": 1,
        "regex": "",
        "skipUrlSync": False,
        "sort": 1,
        "tagValuesQuery": "",
        "tags": [],
        "tagsQuery": "",
        "type": "query",
        "useTags": False
    }
]

# Обновить все три дашборда
dashboards = [
    './grafana/dashboards/bioetl-dq-v2.json',
    './grafana/dashboards/bioetl-overview-v2.json',
    './grafana/dashboards/bioetl-provider-health-v2.json'
]

for dashboard in dashboards:
    with open(dashboard, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    data['templating']['list'] = template_vars
    
    with open(dashboard, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    print(f"Updated {dashboard.split('/')[-1]}")

print("\nAll dashboards updated successfully!")
