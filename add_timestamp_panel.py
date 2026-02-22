#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

# Панель Execution Timestamp
timestamp_panel = {
    "datasource": "Prometheus",
    "fieldConfig": {
        "defaults": {
            "color": {"mode": "palette-classic"},
            "custom": {"hideFrom": {"legend": False, "tooltip": False, "viz": False}},
            "mappings": [],
            "unit": "short",
            "thresholds": {
                "mode": "absolute",
                "steps": [
                    {"color": "green", "value": None}
                ]
            }
        },
        "overrides": []
    },
    "gridPos": {"h": 3, "w": 12, "x": 12, "y": 0},
    "id": 101,
    "options": {
        "colorMode": "background",
        "graphMode": "none",
        "justifyMode": "center",
        "orientation": "auto",
        "reduceOptions": {"calcs": ["lastNotNull"], "fields": "", "values": False},
        "textMode": "auto"
    },
    "targets": [
        {
            "expr": "max(bioetl_run_start_timestamp{pipeline=~\"$pipeline\", run_id=~\"$run_id\"})",
            "legendFormat": "Timestamp",
            "refId": "A"
        }
    ],
    "title": "Execution Timestamp",
    "type": "stat"
}

# Обновить все три дашборда
dashboards = [
    './grafana/dashboards/bioetl-dq-v2.json',
    './grafana/dashboards/bioetl-overview-v2.json',
    './grafana/dashboards/bioetl-provider-health-v2.json'
]

for dashboard_path in dashboards:
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Удалить существующую Execution Timestamp панель если есть
    data['panels'] = [p for p in data.get('panels', []) if p.get('id') != 101]
    
    # Вставить Execution Timestamp панель в конец (будет видна после фильтров)
    data['panels'].append(timestamp_panel)
    
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    name = dashboard_path.split('/')[-1]
    print(f"Updated {name}")

print("\nAll dashboards updated with Execution Timestamp panel!")
