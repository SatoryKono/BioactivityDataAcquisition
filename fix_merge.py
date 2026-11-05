import subprocess
import re

def run(cmd):
    return subprocess.check_output(cmd, shell=True).decode('utf-8')

print("Aborting any existing merge...")
run("git merge --abort || true")

print("Starting merge...")
try:
    run("git merge origin/main --no-edit")
except subprocess.CalledProcessError:
    print("Merge conflict occurred.")

# Read the file with conflicts
with open('docs/04-reference/environment-variables.md', 'r') as f:
    content = f.read()

if '<<<<<<<' in content:
    print("Fixing conflict...")
    # A simple resolution: just keep both blocks, removing the markers.
    # Actually, let's be more precise.
    # The conflict is likely because both added lines to the end or same place.
    # Let's replace the conflict block with the concatenated content of both sides.

    def repl(m):
        top = m.group(1)
        bottom = m.group(2)
        return top + "\n" + bottom

    new_content = re.sub(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> [a-f0-9]+', repl, content, flags=re.DOTALL)
    new_content = re.sub(r'<<<<<<< HEAD\n(.*?)\n=======\n(.*?)\n>>>>>>> origin/main', repl, new_content, flags=re.DOTALL)

    with open('docs/04-reference/environment-variables.md', 'w') as f:
        f.write(new_content)

    run("git add docs/04-reference/environment-variables.md")
    run("git commit --no-edit")
    print("Merge resolved and committed.")
else:
    print("No conflict markers found?")
