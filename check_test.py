import json, yaml, ast, pathlib

ROOT = pathlib.Path(".")
inv = json.load(open("reports/quality/module-coverage-inventory.json"))
summary = inv["summary"]
status = summary["status_counts"]
doc = open("docs/02-architecture/current-state-inventory.md", encoding="utf-8").read()
print("summary", summary["source_module_count"], status)
print("check fully", "" + str(status["fully_covered"]) + " fully covered" in doc)
print("check source", "" + str(summary["source_module_count"]) + "" in doc)
print(
    "doc snippet",
    doc[doc.find("fully covered") - 100 : doc.find("fully covered") + 100],
)
