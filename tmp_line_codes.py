from pathlib import Path
path = Path(r'docs/application/pipelines/chembl/activity/diagrams/flow/activity-workflow.mmd')
for idx, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1):
    if idx in (1,3,6):
        print(idx, repr(line))
        print([ord(ch) for ch in line])
