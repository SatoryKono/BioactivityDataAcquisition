import subprocess, json
out=subprocess.check_output(['git','show','6627ed1d9a:configs/quality/scripts_inventory_manifest.json'])
data=json.loads(out)
print([e['reference_count'] for e in data['scripts'] if e['path']=='scripts/ops/data/vacuum_delta.py'][0])
