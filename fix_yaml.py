with open("tests/unit/scripts/ci/test_quality_integral_gate.py", "r") as f:
    text = f.read()

text = text.replace("from scripts.ci", "from bioetl.ci")

with open("tests/unit/scripts/ci/test_quality_integral_gate.py", "w") as f:
    f.write(text)
