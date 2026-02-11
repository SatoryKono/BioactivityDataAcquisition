import pathlib

target = pathlib.Path(
    "E:/g-drive/05_AI/github/BioactivityDataAcquisition2/.claude/agents/py-doc-bot.md"
)

# Read source files for reference
base = pathlib.Path("E:/g-drive/05_AI/github/BioactivityDataAcquisition2")
sub_path = base / ".claude/agents/subagents/pyDocBot/SUBAGENT.md"
doc_path = base / ".claude/agents/doc-sync.md"
adr_path = base / ".claude/agents/adr-manager.md"

sub = sub_path.read_text(encoding="utf-8")
doc = doc_path.read_text(encoding="utf-8")
adr = adr_path.read_text(encoding="utf-8")

# The merged content will be constructed inline
# We write the merged py-doc-bot.md
target.write_text("PLACEHOLDER_FOR_CONTENT", encoding="utf-8")
print(f"Written {target.stat().st_size} bytes")
