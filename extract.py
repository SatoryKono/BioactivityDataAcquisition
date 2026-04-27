lines1 = [194, 261, 267, 270, 272, 278, 284, 288, 292, 295, 296, 300, 301, 302, 305, 319, 401, 704, 853, 1268, 1555, 1587, 2226, 2248, 2250, 2368, 2373, 2466, 2504, 2814, 2333, 2361, 2408, 2617, 2729, 2733]
try:
    with open('testing_support/neo4j_memory_sync.py', encoding='utf-8') as f:
        text = f.readlines()
    for l in lines1:
        if l <= len(text):
            print(f'1:{l}: {text[l-1].strip()}')
except Exception as e:
    print(f"Error reading testing_support: {e}")

lines2 = [217, 223, 229, 283, 672]
try:
    with open('scripts/engineering/qa/naming_audit.py', encoding='utf-8') as f:
        text = f.readlines()
    for l in lines2:
        if l <= len(text):
            print(f'2:{l}: {text[l-1].strip()}')
except Exception as e:
    print(f"Error reading naming_audit: {e}")

lines3 = [100]
try:
    with open('scripts/ai/codex/helper/ensure-codex-cli.sh', encoding='utf-8') as f:
        text = f.readlines()
    for l in lines3:
        if l <= len(text):
            print(f'3:{l}: {text[l-1].strip()}')
except Exception as e:
    print(f"Error reading ensure-codex-cli: {e}")
