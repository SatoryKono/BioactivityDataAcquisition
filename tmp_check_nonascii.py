from pathlib import Path
path = Path(r"docs/application/pipelines/chembl/activity/diagrams/flow/activity-workflow.mmd")
text = path.read_text(encoding="utf-8")
for idx, line in enumerate(text.splitlines(), 1):
    chars = [(ch, ord(ch)) for ch in line if ord(ch) > 127]
    if chars:
        print(idx, chars)
