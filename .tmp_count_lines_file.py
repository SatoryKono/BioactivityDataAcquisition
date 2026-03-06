from pathlib import Path
import sys
p = Path(sys.argv[1])
text = p.read_text(encoding='utf-8')
print('splitlines', len(text.splitlines()))
print('count_newline', text.count('\n')+1)
