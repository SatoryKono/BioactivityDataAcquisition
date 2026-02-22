#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

# Информационные панели для верхней части
info_panels = [
    {
        "datasource": "Prometheus",
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"hideFrom": {"legend": False, "tooltip": False, "viz": False}},
                "mappings": [],
                "unit": "short"
            },
            "overrides": []
        },
        "gridPos": {"h": 3, "w": 6, "x": 0, "y": 0},
        "id": 99,
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
                "expr": "max(label_values(bioetl_records_processed_total{pipeline=~\"$pipeline\"}, pipeline)) or vector(0)",
                "legendFormat": "Pipeline",
                "refId": "A"
            }
        ],
        "title": "Pipeline",
        "type": "stat"
    },
    {
        "datasource": "Prometheus",
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"hideFrom": {"legend": False, "tooltip": False, "viz": False}},
                "mappings": [],
                "unit": "short"
            },
            "overrides": []
        },
        "gridPos": {"h": 3, "w": 6, "x": 6, "y": 0},
        "id": 100,
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
                "expr": "max(label_values(bioetl_records_processed_total{pipeline=~\"$pipeline\", run_id=~\"$run_id\"}, run_id)) or vector(0)",
                "legendFormat": "Run ID",
                "refId": "A"
            }
        ],
        "title": "Run ID",
        "type": "stat"
    },
    {
        "datasource": "Prometheus",
        "fieldConfig": {
            "defaults": {
                "color": {"mode": "palette-classic"},
                "custom": {"hideFrom": {"legend": False, "tooltip": False, "viz": False}},
                "mappings": [],
                "unit": "short"
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
                "expr": "max(bioetl_run_start_timestamp{pipeline=~\"$pipeline\", run_id=~\"$run_id\"}) or vector(0)",
                "legendFormat": "Execution Timestamp",
                "refId": "A"
            }
        ],
        "title": "Execution Timestamp",
        "type": "stat"
    }
]

# Обновить все три дашборда
dashboards = [
    './grafana/dashboards/bioetl-dq-v2.json',
    './grafana/dashboards/bioetl-overview-v2.json',
    './grafana/dashboards/bioetl-provider-health-v2.json'
]

for dashboard_path in dashboards:
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Удалить старые info панели если они есть
    data['panels'] = [p for p in data.get('panels', []) if p.get('id') not in [99, 100, 101]]
    
    # Добавить новые info панели в начало
    data['panels'] = info_panels + data['panels']
    
    # Пересчитать gridPos для остальных панелей (сместить вниз на 3)
    for i, panel in enumerate(data['panels']):
        if i >= 3:  # Пропустить первые три info панели
            if 'gridPos' in panel:
                panel['gridPos']['y'] += 3
    
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    print(f"Updated {dashboard_path.split('/')[-1]} with info panels")

print("\nAll dashboards updated with info panels!")
