import sys

with open(sys.argv[1], 'r') as f:
    lines = f.readlines()

print("".join(lines[:20]))
print("...")
print("".join(lines[-20:]))
