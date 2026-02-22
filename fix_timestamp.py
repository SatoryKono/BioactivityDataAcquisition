#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json

# Обновить все три дашборда
dashboards = [
    './grafana/dashboards/bioetl-dq-v2.json',
    './grafana/dashboards/bioetl-overview-v2.json',
    './grafana/dashboards/bioetl-provider-health-v2.json'
]

for dashboard_path in dashboards:
    with open(dashboard_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Найти панель с Execution Timestamp и обновить запрос
    for panel in data.get('panels', []):
        if panel.get('title') == 'Execution Timestamp':
            # Обновить targets
            for target in panel.get('targets', []):
                # Заменить expr на правильный запрос
                target['expr'] = 'max(bioetl_run_start_timestamp{pipeline=~"$pipeline", run_id=~"$run_id"})'
                target['legendFormat'] = 'Execution Timestamp'
            print(f"Updated Execution Timestamp in {dashboard_path.split('/')[-1]}")
    
    # Обновить PromQL в других панелях для использования переменных
    for panel in data.get('panels', []):
        for target in panel.get('targets', []):
            expr = target.get('expr', '')
            
            # Заменить $latest_run_id на $run_id с использованием обеих переменных
            if '$latest_run_id' in expr:
                expr = expr.replace('$latest_run_id', '$run_id')
                # Добавить фильтр по pipeline если его нет
                if 'pipeline=~' not in expr:
                    # Для простых запросов добавить фильтр pipeline
                    if 'run_id=~' in expr:
                        expr = expr.replace('run_id=~"$run_id"', 'pipeline=~"$pipeline", run_id=~"$run_id"')
                target['expr'] = expr
    
    with open(dashboard_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=4)
    
    print(f"Updated {dashboard_path.split('/')[-1]}")

print("\nAll dashboards updated with correct timestamp queries!")
