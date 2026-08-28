import json, pathlib
p=pathlib.Path('configs/quality/scripts_inventory_manifest.json')
data=json.loads(p.read_text())
for e in data['scripts']:
    if e['path']=='scripts/ops/data/vacuum_delta.py':
        e['reference_count']=6
        print('fixed', e['path'], e['reference_count'])
p.write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n')
print('done')
