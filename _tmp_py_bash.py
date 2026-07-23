import subprocess

cmds = [
    "export OPENAI_API_KEY=synthetic; echo VAL=$OPENAI_API_KEY",
    "export OPENAI_API_KEY=synthetic; echo VAL=${OPENAI_API_KEY}",
    "export OPENAI_API_KEY=synthetic; printf '%s\\n' \"$OPENAI_API_KEY\"",
    "export OPENAI_API_KEY=synthetic; python3 -c 'import os; print(os.environ.get(\"OPENAI_API_KEY\"))'",
]
for cmd in cmds:
    r = subprocess.run(["bash", "-c", cmd], text=True, capture_output=True)
    print("CMD:", cmd)
    print("OUT:", repr(r.stdout), "ERR:", repr(r.stderr), "RC:", r.returncode)
    print("---")
