import pathlib
import yaml
def test_retention_policy_compliance():
    policy_path = pathlib.Path("configs/quality/retention-policy.yaml")
    assert policy_path.exists()
    policy = yaml.safe_load(policy_path.read_text(encoding="utf-8"))
    allowed = set(policy.get("allowed_retentions", [1, 7, 14, 30]))
    deprecated = set(policy.get("deprecated_retentions", [3]))
    allowed_all = allowed | deprecated
    workflow_dir = pathlib.Path(".github/workflows")
    violations = []
    for yml in workflow_dir.iterdir():
        if yml.suffix != ".yml":
            continue
        text = yml.read_text(encoding="utf-8")
        for line in text.splitlines():
            if "retention-days:" in line:
                val = int(line.split("retention-days:")[1].strip().split()[0])
                if val not in allowed_all:
                    violations.append(f"{yml.name}: unexpected {val}d not in {allowed_all}")
    assert not violations, chr(10).join(violations)
def test_default_is_seven():
    policy = yaml.safe_load(pathlib.Path("configs/quality/retention-policy.yaml").read_text(encoding="utf-8"))
    assert policy["policy"]["default_retention_days"] == 7
