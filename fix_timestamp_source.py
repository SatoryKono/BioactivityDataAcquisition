#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

# Обновить все три дашборда - использовать правильный timestamp запрос
dashboards = [
    './grafana/dashboards/bioetl-dq-v2.json',
    './grafana/dashboards/bioetl-overview-v2.json',
    './grafana/dashboards/bioetl-provider-health-v2.json'
]

for dashboard_path in dashboards:
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Найти Execution Timestamp панель и обновить запрос
    for panel in data.get('panels', []):
        if panel.get('id') == 101:  # Execution Timestamp panel
            for target in panel.get('targets', []):
                # Использовать min() от bioetl_records_processed_created для получения времени запуска
                target['expr'] = 'min(bioetl_records_processed_created{pipeline=~"$pipeline", run_id=~"$run_id"})'
                target['legendFormat'] = 'Start Time'
    
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    name = dashboard_path.split('/')[-1]
    print(f"Updated {name}")

print("\nAll dashboards updated with correct timestamp source!")
