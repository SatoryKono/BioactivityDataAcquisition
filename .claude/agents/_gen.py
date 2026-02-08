import pathlib

base = pathlib.Path('E:/google_drive/05_AI/github/BioactivityDataAcquisition2')
target = base / '.claude/agents/py-doc-bot.md'

# Read sources
sub = (base / '.claude/agents/subagents/pyDocBot/SUBAGENT.md').read_text(encoding='utf-8')
doc = (base / '.claude/agents/doc-sync.md').read_text(encoding='utf-8')
adr = (base / '.claude/agents/adr-manager.md').read_text(encoding='utf-8')

# Read the content template from a separate file
template = (base / '.claude/agents/_content.md').read_text(encoding='utf-8')
target.write_text(template, encoding='utf-8')
print(f'Written {target.stat().st_size} bytes to {target}')