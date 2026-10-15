import subprocess
out = subprocess.run(["git", "log", "-n", "3", "--oneline"], capture_output=True, text=True)
print(out.stdout)
