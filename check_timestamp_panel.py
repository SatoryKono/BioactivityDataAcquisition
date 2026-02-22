#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

# Проверить наличие Execution Timestamp панели
dashboards = [
    './grafana/dashboards/bioetl-dq-v2.json',
    './grafana/dashboards/bioetl-overview-v2.json',
    './grafana/dashboards/bioetl-provider-health-v2.json'
]

for dashboard_path in dashboards:
    print(f"\n{'='*60}")
    print(f"Checking: {dashboard_path.split('/')[-1]}")
    print('='*60)
    
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Найти Execution Timestamp панель
    timestamp_panels = [p for p in data['panels'] if 'Timestamp' in p.get('title', '')]
    
    if timestamp_panels:
        panel = timestamp_panels[0]
        print(f"Found: {panel.get('title')}")
        print(f"ID: {panel.get('id')}")
        print(f"GridPos: {panel.get('gridPos')}")
        print(f"Type: {panel.get('type')}")
        
        # Проверить, находится ли на y=0 (верхняя часть)
        if panel.get('gridPos', {}).get('y') == 0:
            print("Status: VISIBLE in top row")
        else:
            print(f"Status: NOT in top row (y={panel.get('gridPos', {}).get('y')})")
    else:
        print("ERROR: Execution Timestamp panel NOT FOUND!")
